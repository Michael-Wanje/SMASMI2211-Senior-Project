from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import Resident, ResidentContact
from .serializers import ResidentSerializer, ResidentCreateUpdateSerializer, ResidentContactSerializer

class ResidentListCreateView(generics.ListCreateAPIView):
    queryset = Resident.objects.all().select_related('user').prefetch_related('contacts')
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return ResidentCreateUpdateSerializer
        return ResidentSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class ResidentDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Resident.objects.all().select_related('user').prefetch_related('contacts')
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return ResidentCreateUpdateSerializer
        return ResidentSerializer

class MyResidentProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = ResidentCreateUpdateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        resident, created = Resident.objects.get_or_create(user=self.request.user)
        return resident

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def search_residents(request):
    query = request.GET.get('q', '')
    apartment = request.GET.get('apartment', '')
    
    residents = Resident.objects.all().select_related('user')
    
    if query:
        residents = residents.filter(
            models.Q(user__first_name__icontains=query) |
            models.Q(user__last_name__icontains=query) |
            models.Q(user__email__icontains=query) |
            models.Q(apartment_number__icontains=query)
        )
    
    if apartment:
        residents = residents.filter(apartment_number__icontains=apartment)
    
    serializer = ResidentSerializer(residents, many=True)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def resident_stats(request):
    total_residents = Resident.objects.count()
    active_residents = Resident.objects.filter(user__is_active=True).count()
    
    return Response({
        'total_residents': total_residents,
        'active_residents': active_residents,
        'inactive_residents': total_residents - active_residents,
    })