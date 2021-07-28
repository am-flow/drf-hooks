from django.apps import apps as django_apps
from django.core.exceptions import ImproperlyConfigured
from django.conf import settings
from importlib import import_module



def get_module(path):
    """
    A modified duplicate from Django's built in backend
    retriever.

        slugify = get_module('django.template.defaultfilters.slugify')
    """
    try:
        mod_name, func_name = path.rsplit('.', 1)
        mod = import_module(mod_name)
    except ImportError as e:
        raise ImportError(
            'Error importing alert function {0}: "{1}"'.format(mod_name, e))
    try:
        func = getattr(mod, func_name)
    except AttributeError:
        raise ImportError(
            ('Module "{0}" does not define a "{1}" function'
                            ).format(mod_name, func_name))
    return func


def get_hook_model():
    """
    Returns the Custom Hook model if defined in settings,
    otherwise the default Hook model.
    """
    model_label = getattr(settings, 'HOOK_CUSTOM_MODEL', 'drf_hooks.Hook')
    try:
        return django_apps.get_model(model_label, require_ready=False)
    except ValueError:
        raise ImproperlyConfigured("HOOK_CUSTOM_MODEL must be of the form 'app_label.model_name'")
    except LookupError:
        raise ImproperlyConfigured("HOOK_CUSTOM_MODEL refers to unknown model '%s'" % model_label)