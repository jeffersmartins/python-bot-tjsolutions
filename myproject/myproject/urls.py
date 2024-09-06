from django.contrib import admin
from django.urls import path, include
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from rest_framework import permissions
from dotenv import load_dotenv
from django.views.generic import TemplateView

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
   # # Use o URL local para testes, e ajuste conforme necessário
#    url='http://localhost:8000/api/'
   url='https://playwrightlogs.online.dev.br/api/'
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('swagger-custom/', TemplateView.as_view(
        template_name='swagger-ui.html',
        extra_context={'schema_url': 'schema-swagger-ui'}
    ), name='swagger-ui-custom'),
]