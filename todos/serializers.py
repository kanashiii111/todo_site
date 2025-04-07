from rest_framework import serializers
from .models import todo

class todoSerializer(serializers.ModelSerializer):
    class Meta:
        model = todo
        fields = ['id', 'name', 'description', 'isCompleted', 'priority', 'tag']