from rest_framework import generics
from .models import todo
from .serializers import todoSerializer

class todoListCreateView(generics.ListCreateAPIView):
    queryset = todo.objects.all()
    serializer_class = todoSerializer

class todoRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = todo.objects.all()
    serializer_class = todoSerializer
