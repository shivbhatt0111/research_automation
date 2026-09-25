from rest_framework import serializers

from .models import ResearchTask, CompanyContact, KeyPerson


class KeyPersonSerializer(serializers.ModelSerializer):
    class Meta:
        model = KeyPerson
        exclude = ('id', 'company')


class CompanyContactSerializer(serializers.ModelSerializer):
    key_persons = KeyPersonSerializer(many=True, read_only=True)

    class Meta:
        model = CompanyContact
        exclude = ('confidence', 'normalized_name', 'is_selected', 'is_verified')


class ResearchTaskSerializer(serializers.ModelSerializer):
    contacts = serializers.SerializerMethodField()

    class Meta:
        model = ResearchTask
        fields = '__all__'

    def get_contacts(self, obj):
        contacts = obj.contacts.filter(is_selected=True).order_by('-is_verified', 'id')
        return CompanyContactSerializer(contacts, many=True).data


class CreateResearchSerializer(serializers.Serializer):
    industry = serializers.CharField(max_length=200)
    location = serializers.CharField(max_length=200)
    top_companies = serializers.IntegerField(min_value=1, max_value=50, default=5)