from django.urls import path
from .views import hello_world, consultar_ipv6, relatorio_ipv6

urlpatterns = [
    path('hello-world/', hello_world, name='hello_world'),
    path('consultar-ipv6/', consultar_ipv6, name='consultar_ipv6'),
    path('relatorio-ipv6/', relatorio_ipv6, name='relatorio_ipv6'),
]
