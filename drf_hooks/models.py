import json
from collections import OrderedDict, defaultdict

from django.apps import apps
from django.conf import settings
from django.core import serializers
from django.core.exceptions import ValidationError, ImproperlyConfigured
from django.core.serializers.json import DjangoJSONEncoder
from django.contrib.auth import get_user_model
from django.db import models
from django.db.models.signals import post_save, post_delete
from django.utils.module_loading import import_string
from django.dispatch import receiver

from .signals import hook_event, raw_hook_event
from .client import get_client

__EVENT_LOOKUP = None
__HOOK_MODEL = None

if not hasattr(settings, 'HOOK_EVENTS'):
    raise Exception('You need to define settings.HOOK_EVENTS!')

def get_event_lookup():
    global __EVENT_LOOKUP
    if not __EVENT_LOOKUP:
        __EVENT_LOOKUP = defaultdict(dict)
        for event_name, auto in settings.HOOK_EVENTS.items():
            if not auto:
                continue
            model, action = auto.rstrip('+').rsplit('.', 1)
            all_users = auto.endswith('+')
            if action in __EVENT_LOOKUP[model]:
                raise ImproperlyConfigured(
                    "settings.HOOK_EVENTS has a duplicate {action} for model "
                    "{model_path}".format(action=action, model=model)
                )
            __EVENT_LOOKUP[model][action] = (event_name, all_users)
    return __EVENT_LOOKUP

def clear_event_lookup():
    global __EVENT_LOOKUP
    __EVENT_LOOKUP = None

def get_hook_model():
    """
    Returns the Custom Hook model if defined in settings,
    otherwise the default Hook model.
    """
    global __HOOK_MODEL
    if __HOOK_MODEL is None:
        model_label = getattr(settings, 'HOOK_CUSTOM_MODEL', 'drf_hooks.Hook')
        try:
            __HOOK_MODEL = apps.get_model(model_label, require_ready=False)
        except ValueError:
            raise ImproperlyConfigured("HOOK_CUSTOM_MODEL must be of the form 'app_label.model_name'")
        except LookupError:
            raise ImproperlyConfigured("HOOK_CUSTOM_MODEL refers to unknown model '%s'" % model_label)
    return __HOOK_MODEL


def get_default_headers():
    return {'Content-Type': 'application/json'}


class AbstractHook(models.Model):
    """
    Stores a representation of a Hook.
    """
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    user = models.ForeignKey(get_user_model(), related_name='%(class)ss', on_delete=models.CASCADE)
    event = models.CharField('Event', max_length=64, db_index=True)
    target = models.URLField('Target URL', max_length=255)
    headers = models.JSONField(default=get_default_headers)

    class Meta:
        abstract = True

    def clean(self):
        """ Validation for events. """
        if self.event not in settings.HOOK_EVENTS.keys():
            raise ValidationError(
                "Invalid hook event {evt}.".format(evt=self.event)
            )

    @staticmethod
    def serialize_model(instance):
        hook_srls = getattr(settings, 'HOOK_SERIALIZERS', {})
        if instance._meta.label in hook_srls:
            serializer = import_string(hook_srls[instance._meta.label])
            context = {'request': None}
            data = serializer(instance, context=context).data
        else:
            # if no user defined serializers, fallback to the django builtin!
            data = serializers.serialize('python', [instance])[0]
            for k, v in data.items():
                if isinstance(v, OrderedDict):
                    data[k] = dict(v)
            if isinstance(data, OrderedDict):
                data = dict(data)
        return data
    
    def serialize_hook(self, payload):
        serialized_hook = {
            'hook': {'id': self.id, 'event': self.event, 'target': self.target},
            'data': payload,
        }
        return json.dumps(serialized_hook, cls=DjangoJSONEncoder)

    def deliver_hook(self, serialized_hook):
        """Deliver the payload to the target URL."""
        get_client().post(
            url=self.target,
            data=serialized_hook,
            headers=self.headers
        )

    @classmethod
    def find_hooks(cls, event_name, user=None):
        hooks = cls.objects.filter(event=event_name)
        if not user:
            return hooks
        return hooks.filter(user=user)

    @classmethod
    def find_and_fire_hooks(cls, event_name, payload, user=None):
        for hook in cls.find_hooks(event_name, user=user):
            serialized_hook = hook.serialize_hook(payload)
            hook.deliver_hook(serialized_hook)

    @staticmethod
    def get_user(instance, all_users=False):
        if all_users:
            return
        if hasattr(instance, 'user'):
            return instance.user
        elif isinstance(instance, get_user_model()):
            return instance
        else:
            raise ValueError('{} has no `user` property.'.format(repr(instance)))

    @classmethod
    def handle_model_event(cls, instance, action):
        events = get_event_lookup()
        model = instance._meta.label
        if model not in events or action not in events[model]:
            return
        event_name, all_users = events[model][action]
        payload = cls.serialize_model(instance)
        user = cls.get_user(instance, all_users)
        cls.find_and_fire_hooks(event_name, payload, user)

    def __unicode__(self):
        return u'{} => {}'.format(self.event, self.target)


class Hook(AbstractHook):
    class Meta(AbstractHook.Meta):
        swappable = 'HOOK_CUSTOM_MODEL'


##############
### EVENTS ###
##############

@receiver(hook_event, dispatch_uid='instance-custom-hook')
def custom_event(sender, instance, action, *args, **kwargs):
    """Manually trigger a custom action (or even a standard action)."""
    get_hook_model().handle_model_event(instance, action)


@receiver(post_save, dispatch_uid='instance-saved-hook')
def model_saved(sender, instance, created, *args, **kwargs):
    """Automatically triggers "created" and "updated" actions."""
    action = 'created' if created else 'updated'
    get_hook_model().handle_model_event(instance, action)


@receiver(post_delete, dispatch_uid='instance-deleted-hook')
def model_deleted(sender, instance, *args, **kwargs):
    """Automatically triggers "deleted" actions."""
    get_hook_model().handle_model_event(instance, 'deleted')


@receiver(raw_hook_event, dispatch_uid='raw-custom-hook')
def raw_custom_event(sender, event_name, payload, user, **kwargs):
    """Give a full payload"""
    get_hook_model().find_and_fire_hooks(event_name, payload, user)