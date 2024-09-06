from rest_framework import serializers

class HelloWorldSerializer(serializers.Serializer):
    nome = serializers.CharField(max_length=100, required=True)
    
class ConsultarIpv6Serializer(serializers.Serializer):
    date = serializers.CharField(required=True)
    time = serializers.CharField(required=True)
    ipv6 = serializers.CharField(required=True)