from django.conf import settings
from rest_framework import serializers

from drf_hooks.models import get_hook_model


class HookSerializer(serializers.ModelSerializer):
    event = serializers.ChoiceField(choices=list(settings.HOOK_EVENTS))
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())
    headers = serializers.JSONField(write_only=True, required=False)

    def create(self, validated_data):
        """Recreating identical hooks fails silently"""
        obj, created = get_hook_model().objects.get_or_create(**validated_data)
        return obj

    class Meta:
        model = get_hook_model()
        fields = '__all__'
        read_only_fields = ('user',)
