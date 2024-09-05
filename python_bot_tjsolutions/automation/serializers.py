from rest_framework import serializers

class QueryParamsSerializer(serializers.Serializer):
    date = serializers.CharField(required=True)
    time = serializers.CharField(required=True)
    ipv6 = serializers.CharField(required=True)