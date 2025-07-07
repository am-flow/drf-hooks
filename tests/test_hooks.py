import json
import typing as tp
from unittest.mock import MagicMock

import pytest
from pytest_mock import MockFixture

from drf_hooks.client import get_client
from tests.settings import ALT_HOOK_EVENTS

CLIENT = get_client()


from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.dispatch import receiver
from django.test.signals import setting_changed
from django_comments.models import Comment
from rest_framework import serializers

from drf_hooks import models
from drf_hooks.admin import HookForm

Hook = models.Hook

urlpatterns = []


class CommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = "__all__"


@receiver(setting_changed)
def handle_hook_events_change(sender, setting, *args, **kwargs):
    if setting == "HOOK_EVENTS":
        models.clear_event_lookup()


@pytest.fixture
def setup(db) -> tp.Generator[tuple[User, Site], None, None]:
    user = User.objects.create_user("bob", "bob@example.com", "password")
    site, created = Site.objects.get_or_create(domain="example.com", name="example.com")
    yield user, site


@pytest.fixture
def mocked_post(mocker: MockFixture) -> MagicMock:
    return mocker.patch.object(CLIENT, attribute="post", autospec=True)


# @pytest.mark.usefixtures("setup", "mocked_post")
class TestDRFHooks:
    """This test Class uses real HTTP calls to a requestbin service,
    making it easy to check responses and endpoint history."""

    def make_hook(self, user, event, target):
        return Hook.objects.create(user=user, event=event, target=target)

    #############
    ### TESTS ###
    #############

    def test_get_event_actions_config(self, settings) -> None:
        settings.HOOK_EVENTS = ALT_HOOK_EVENTS
        assert dict(models.get_event_lookup()) == {
            "django_comments.Comment": {
                "created": ("comment.added", False),
                "updated": ("comment.changed", False),
                "deleted": ("comment.removed", False),
                "moderated": ("comment.moderated", True),
            },
        }
        # self.assertEquals(
        #     models.get_event_lookup(),
        #     {
        #         "django_comments.Comment": {
        #             "created": ("comment.added", False),
        #             "updated": ("comment.changed", False),
        #             "deleted": ("comment.removed", False),
        #             "moderated": ("comment.moderated", True),
        #         },
        #     },
        # )

    def test_no_hook(self, setup: tuple[User, Site]):
        user, site = setup
        comment = Comment.objects.create(
            site=site, content_object=user, user=user, comment="Hello world!"
        )

    def perform_create_request_cycle(self, site, user, mocked_post):
        mocked_post.return_value = None
        target = "http://example.com/perform_create_request_cycle"
        hook = self.make_hook(user, "comment.added", target)
        comment = Comment.objects.create(
            site=site, content_object=user, user=user, comment="Hello world!"
        )
        return hook, comment, json.loads(mocked_post.call_args_list[0][1]["data"])

    # @override_settings(HOOK_SERIALIZERS=ALT_HOOK_SERIALIZERS)
    def test_simple_comment_hook(self, setup: tuple[User, Site], mocked_post):
        """Uses the default serializer."""
        user, site = setup
        hook, comment, payload = self.perform_create_request_cycle(site, user, mocked_post)
        assert hook.id == payload["hook"]["id"]
        assert "comment.added" == payload["hook"]["event"]
        assert hook.target == payload["hook"]["target"]
        assert str(comment.id) == payload["data"]["object_pk"]
        assert "Hello world!" == payload["data"]["comment"]
        assert 1 == payload["data"]["user"]

    def test_drf_comment_hook(self, setup: tuple[User, Site], mocked_post):
        """Uses the drf serializer."""
        user, site = setup
        hook, comment, payload = self.perform_create_request_cycle(site, user, mocked_post)
        assert hook.id == payload["hook"]["id"]
        assert "comment.added" == payload["hook"]["event"]
        assert hook.target == payload["hook"]["target"]

        assert str(comment.id) == payload["data"]["object_pk"]
        assert "Hello world!" == payload["data"]["comment"]
        assert 1 == payload["data"]["user"]

    def test_full_cycle_comment_hook(self, mocked_post, setup: tuple[User, Site]):
        mocked_post.return_value = None
        user, site = setup
        target = "http://example.com/test_full_cycle_comment_hook"
        for event in ("comment.added", "comment.changed", "comment.removed"):
            self.make_hook(user, event, target)

        # created
        comment = Comment.objects.create(
            site=site, content_object=user, user=user, comment="Hello world!"
        )
        # updated
        comment.comment = "Goodbye world..."
        comment.save()
        # deleted
        comment.delete()

        payloads = [json.loads(call[2]["data"]) for call in mocked_post.mock_calls]

        assert "comment.added" == payloads[0]["hook"]["event"]
        assert "comment.changed" == payloads[1]["hook"]["event"]
        assert "comment.removed" == payloads[2]["hook"]["event"]

        assert "Hello world!" == payloads[0]["data"]["comment"]
        assert "Goodbye world..." == payloads[1]["data"]["comment"]
        assert "Goodbye world..." == payloads[2]["data"]["comment"]

    def test_custom_instance_hook(self, mocked_post, setup: tuple[User, Site]):
        from drf_hooks.signals import hook_event

        user, site = setup
        mocked_post.return_value = None
        target = "http://example.com/test_custom_instance_hook"

        self.make_hook(user, "comment.moderated", target)

        comment = Comment.objects.create(
            site=site, content_object=user, user=user, comment="Hello world!"
        )

        hook_event.send(sender=comment.__class__, action="moderated", instance=comment)
        # time.sleep(1) # should change a setting to turn off async
        payloads = [json.loads(call[2]["data"]) for call in mocked_post.mock_calls]
        assert "comment.moderated" == payloads[0]["hook"]["event"]
        assert "Hello world!" == payloads[0]["data"]["comment"]

    def test_raw_custom_event(self, mocked_post, setup: tuple[User, Site]):
        from drf_hooks.signals import raw_hook_event

        user, site = setup
        mocked_post.return_value = None
        target = "http://example.com/test_raw_custom_event"

        self.make_hook(user, "special.thing", target)

        raw_hook_event.send(
            sender=None, event_name="special.thing", payload={"hello": "world!"}, user=user
        )

        payload = json.loads(mocked_post.mock_calls[0][2]["data"])

        assert "special.thing" == payload["hook"]["event"]
        assert "world!" == payload["data"]["hello"]

    def test_valid_form(self, setup: tuple[User, Site]) -> None:
        user, site = setup
        form_data = {
            "user": user.id,
            "target": "http://example.com",
            "event": HookForm.get_admin_events()[0][0],
            "headers": json.dumps({"Content-Type": "application/json"}),
        }
        form = HookForm(data=form_data)
        assert form.is_valid()

    def test_form_save(self, setup: tuple[User, Site]):
        user, site = setup
        form_data = {
            "user": user.id,
            "target": "http://example.com",
            "event": HookForm.get_admin_events()[0][0],
            "headers": json.dumps({"Content-Type": "application/json"}),
        }
        form = HookForm(data=form_data)

        assert form.is_valid()
        instance = form.save()
        assert isinstance(instance, Hook)

    def test_invalid_form(self):
        form = HookForm(data={})
        assert not form.is_valid()

    # @override_settings(HOOK_CUSTOM_MODEL="drf_hooks.Hook")
    def test_get_custom_hook_model(self):
        # Using the default Hook model just to exercise get_hook_model's
        # lookup machinery.
        from drf_hooks.models import AbstractHook, get_hook_model

        HookModel = get_hook_model()
        assert HookModel is Hook
        assert issubclass(HookModel, AbstractHook)
