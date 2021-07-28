
from rest_framework import routers

from .views import HookViewSet

router = routers.SimpleRouter()
router.register(r'webhooks', HookViewSet, 'webhook')

urlpatterns = router.urls