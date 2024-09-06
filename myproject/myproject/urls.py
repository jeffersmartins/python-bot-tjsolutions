from django.contrib import admin
from django.urls import path, include
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from rest_framework import permissions
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()


schema_view = get_schema_view(
   openapi.Info(
      title="Hello World API",
      default_version='v1',
      description="API para dizer Olá Mundo",
   ),
   public=True,
   permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
]
