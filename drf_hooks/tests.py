import requests
import json
import time
import copy
from datetime import datetime

from mock import patch, MagicMock, ANY

from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.test import TestCase
from django.test.utils import override_settings
from django_comments.models import Comment
from django.test.signals import setting_changed
from django.dispatch import receiver

from rest_framework import serializers

from drf_hooks import models
from drf_hooks.client import get_client

from drf_hooks.admin import HookForm

Hook = models.Hook

urlpatterns = []

HOOK_EVENTS_OVERRIDE = {
    'comment.added':        'django_comments.Comment.created',
    'comment.changed':      'django_comments.Comment.updated',
    'comment.removed':      'django_comments.Comment.deleted',
    'comment.moderated':    'django_comments.Comment.moderated',
    'special.thing':        None,
}

HOOK_SERIALIZERS_OVERRIDE = {
    'django_comments.Comment': 'drf_hooks.tests.CommentSerializer',
}

ALT_HOOK_EVENTS = dict(HOOK_EVENTS_OVERRIDE)
ALT_HOOK_EVENTS['comment.moderated'] += '+'
ALT_HOOK_SERIALIZERS = {}
CLIENT = get_client()

class CommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = '__all__'



@receiver(setting_changed)
def handle_hook_events_change(sender, setting, *args, **kwargs):
    if setting == 'HOOK_EVENTS':
        models.clear_event_lookup()


@override_settings(HOOK_EVENTS=HOOK_EVENTS_OVERRIDE, HOOK_SERIALIZERS=HOOK_SERIALIZERS_OVERRIDE, HOOK_DELIVERER=None)
class DRFHooksTest(TestCase):
    """
    This test Class uses real HTTP calls to a requestbin service, making it easy
    to check responses and endpoint history.
    """

    #############
    ### TOOLS ###
    #############

    def setUp(self):
        self.client = requests # force non-async for test cases

        self.user = User.objects.create_user('bob', 'bob@example.com', 'password')
        self.site, created = Site.objects.get_or_create(domain='example.com', name='example.com')

    def make_hook(self, event, target):
        return Hook.objects.create(
            user=self.user,
            event=event,
            target=target
        )

    #############
    ### TESTS ###
    #############

    @override_settings(HOOK_EVENTS=ALT_HOOK_EVENTS)
    def test_get_event_actions_config(self):
        self.assertEquals(
            models.get_event_lookup(),
            {
                'django_comments.Comment': {
                    'created': ('comment.added', False),
                    'updated': ('comment.changed', False),
                    'deleted': ('comment.removed', False),
                    'moderated': ('comment.moderated', True),
                },
            }
        )

    def test_no_hook(self):
        comment = Comment.objects.create(
            site=self.site,
            content_object=self.user,
            user=self.user,
            comment='Hello world!'
        )

    @patch('drf_hooks.tests.CLIENT.post', autospec=True)
    def perform_create_request_cycle(self, method_mock):
        method_mock.return_value = None
        target = 'http://example.com/perform_create_request_cycle'
        hook = self.make_hook('comment.added', target)
        comment = Comment.objects.create(
            site=self.site,
            content_object=self.user,
            user=self.user,
            comment='Hello world!'
        )
        return hook, comment, json.loads(method_mock.call_args_list[0][1]['data'])

    @override_settings(HOOK_SERIALIZERS=ALT_HOOK_SERIALIZERS)
    def test_simple_comment_hook(self):
        """
        Uses the default serializer.
        """
        hook, comment, payload = self.perform_create_request_cycle()
        self.assertEquals(hook.id, payload['hook']['id'])
        self.assertEquals('comment.added', payload['hook']['event'])
        self.assertEquals(hook.target, payload['hook']['target'])

        self.assertEquals(comment.id, payload['data']['fields']['object_pk'])
        self.assertEquals('Hello world!', payload['data']['fields']['comment'])
        self.assertEquals(1, payload['data']['fields']['user'])

    def test_drf_comment_hook(self):
        """
        Uses the drf serializer.
        """
        hook, comment, payload = self.perform_create_request_cycle()
        self.assertEquals(hook.id, payload['hook']['id'])
        self.assertEquals('comment.added', payload['hook']['event'])
        self.assertEquals(hook.target, payload['hook']['target'])

        self.assertEquals(str(comment.id), payload['data']['object_pk'])
        self.assertEquals('Hello world!', payload['data']['comment'])
        self.assertEquals(1, payload['data']['user'])

    @patch('drf_hooks.tests.CLIENT.post')
    def test_full_cycle_comment_hook(self, method_mock):
        method_mock.return_value = None
        target = 'http://example.com/test_full_cycle_comment_hook'

        [self.make_hook(event, target) for event in ['comment.added', 'comment.changed', 'comment.removed']]

        # created
        comment = Comment.objects.create(
            site=self.site,
            content_object=self.user,
            user=self.user,
            comment='Hello world!'
        )
        # updated
        comment.comment = 'Goodbye world...'
        comment.save()
        # deleted
        comment.delete()

        payloads = [json.loads(call[2]['data']) for call in method_mock.mock_calls]

        self.assertEquals('comment.added', payloads[0]['hook']['event'])
        self.assertEquals('comment.changed', payloads[1]['hook']['event'])
        self.assertEquals('comment.removed', payloads[2]['hook']['event'])

        self.assertEquals('Hello world!', payloads[0]['data']['comment'])
        self.assertEquals('Goodbye world...', payloads[1]['data']['comment'])
        self.assertEquals('Goodbye world...', payloads[2]['data']['comment'])

    @patch('drf_hooks.tests.CLIENT.post')
    def test_custom_instance_hook(self, method_mock):
        from drf_hooks.signals import hook_event

        method_mock.return_value = None
        target = 'http://example.com/test_custom_instance_hook'

        self.make_hook('comment.moderated', target)

        comment = Comment.objects.create(
            site=self.site,
            content_object=self.user,
            user=self.user,
            comment='Hello world!'
        )

        hook_event.send(
            sender=comment.__class__,
            action='moderated',
            instance=comment
        )
        # time.sleep(1) # should change a setting to turn off async
        payloads = [json.loads(call[2]['data']) for call in method_mock.mock_calls]
        self.assertEquals('comment.moderated', payloads[0]['hook']['event'])
        self.assertEquals('Hello world!', payloads[0]['data']['comment'])

    @patch('drf_hooks.tests.CLIENT.post')
    def test_raw_custom_event(self, method_mock):
        from drf_hooks.signals import raw_hook_event

        method_mock.return_value = None
        target = 'http://example.com/test_raw_custom_event'

        self.make_hook('special.thing', target)

        raw_hook_event.send(
            sender=None,
            event_name='special.thing',
            payload={
                'hello': 'world!'
            },
            user=self.user
        )
        # time.sleep(1) # should change a setting to turn off async

        payload = json.loads(method_mock.mock_calls[0][2]['data'])

        self.assertEquals('special.thing', payload['hook']['event'])
        self.assertEquals('world!', payload['data']['hello'])

    def test_valid_form(self):
        form_data = {
            'user': self.user.id,
            'target': "http://example.com",
            'event': HookForm.get_admin_events()[0][0]
        }
        form = HookForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_form_save(self):
        form_data = {
            'user': self.user.id,
            'target': "http://example.com",
            'event': HookForm.get_admin_events()[0][0]
        }
        form = HookForm(data=form_data)

        self.assertTrue(form.is_valid())
        instance = form.save()
        self.assertIsInstance(instance, Hook)

    def test_invalid_form(self):
        form = HookForm(data={})
        self.assertFalse(form.is_valid())

    @override_settings(HOOK_CUSTOM_MODEL='drf_hooks.Hook')
    def test_get_custom_hook_model(self):
        # Using the default Hook model just to exercise get_hook_model's
        # lookup machinery.
        from drf_hooks.models import AbstractHook, get_hook_model
        HookModel = get_hook_model()
        self.assertIs(HookModel, Hook)
        self.assertTrue(issubclass(HookModel, AbstractHook))
