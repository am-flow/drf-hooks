from django.contrib import admin
from django.conf import settings
from django import forms
from .models import get_hook_model


class HookForm(forms.ModelForm):
    """
    Model form to handle registered events, asuring
    only events declared on HOOK_EVENTS settings
    can be registered.
    """

    class Meta:
        model = get_hook_model()
        fields = ['user', 'target', 'event']

    def __init__(self, *args, **kwargs):
        super(HookForm, self).__init__(*args, **kwargs)
        self.fields['event'] = forms.ChoiceField(choices=self.get_admin_events())

    @classmethod
    def get_admin_events(cls):
        return [(x, x) for x in settings.HOOK_EVENTS]

class HookAdmin(admin.ModelAdmin):
    list_display = [f.name for f in get_hook_model()._meta.fields]
    raw_id_fields = ['user', ]
    form = HookForm


admin.site.register(get_hook_model(), HookAdmin)
