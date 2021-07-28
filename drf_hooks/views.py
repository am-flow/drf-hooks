from rest_framework import viewsets
from .models import get_hook_model
from .serializers import HookSerializer

class HookViewSet(viewsets.ModelViewSet):
    """Retrieve, create, update or destroy webhooks."""
    queryset = get_hook_model().objects.all()
    model = get_hook_model()
    serializer_class = HookSerializer
    # permission_classes = (CustomDjangoModelPermissions,)
