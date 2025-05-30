from rest_framework import serializers
from authentication.serializers import UserSerializer
from .models import Resident, ResidentContact

class ResidentContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResidentContact
        fields = '__all__'
        read_only_fields = ('id', 'created_at')

class ResidentSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    contacts = ResidentContactSerializer(many=True, read_only=True)
    full_name = serializers.CharField(source='user.get_full_name', read_only=True)
    email = serializers.CharField(source='user.email', read_only=True)
    phone_number = serializers.CharField(source='user.phone_number', read_only=True)

    class Meta:
        model = Resident
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at', 'user')

class ResidentCreateUpdateSerializer(serializers.ModelSerializer):
    contacts = ResidentContactSerializer(many=True, required=False)

    class Meta:
        model = Resident
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at', 'user')

    def create(self, validated_data):
        contacts_data = validated_data.pop('contacts', [])
        resident = Resident.objects.create(**validated_data)
        
        for contact_data in contacts_data:
            ResidentContact.objects.create(resident=resident, **contact_data)
            
        return resident

    def update(self, instance, validated_data):
        contacts_data = validated_data.pop('contacts', [])
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Update contacts
        if contacts_data:
            instance.contacts.all().delete()
            for contact_data in contacts_data:
                ResidentContact.objects.create(resident=instance, **contact_data)
        
        return instance