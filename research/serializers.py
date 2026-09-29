from rest_framework import serializers

from .models import CompanyContact, KeyPerson, ResearchTask


class KeyPersonSerializer(serializers.ModelSerializer):
    class Meta:
        model = KeyPerson
        exclude = ('id', 'company')


class CompanyContactSerializer(serializers.ModelSerializer):
    key_persons = KeyPersonSerializer(many=True, read_only=True)
    task_industry = serializers.CharField(source='task.industry', read_only=True)
    task_location = serializers.CharField(source='task.location', read_only=True)

    class Meta:
        model = CompanyContact
        exclude = ('confidence', 'normalized_name', 'is_selected')

class CreateResearchSerializer(serializers.Serializer):
    industry = serializers.CharField(max_length=200)
    location = serializers.CharField(max_length=200)
    top_companies = serializers.IntegerField(min_value=1, max_value=50, default=5)
    
    
class ResearchTaskSerializer(serializers.ModelSerializer):
    contacts = serializers.SerializerMethodField()
    duration = serializers.SerializerMethodField()
    created_at = serializers.SerializerMethodField()
    completed_at = serializers.SerializerMethodField()

    class Meta:
        model = ResearchTask
        fields = (
            'id', 'industry', 'location', 'top_companies', 'status',
            'total_companies', 'emails_found', 'phones_found',
            'error_message', 'created_at', 'completed_at',
            'duration', 'contacts',
        )

    def get_contacts(self, obj):
        contacts = obj.contacts.filter(is_selected=True).order_by('-is_verified', 'id')
        return CompanyContactSerializer(contacts, many=True).data
    @staticmethod
    def _format_duration(seconds):
        """280 -> '0:04:40' | 5430 -> '1:30:30' (always H:MM:SS)."""
        if seconds is None:
            return None
        minutes, sec = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        return f'{hours}:{minutes:02d}:{sec:02d}'

    def get_duration(self, obj):
        return self._format_duration(obj.duration_seconds)

    def get_created_at(self, obj):
        return self._to_ist(obj.created_at)

    def get_completed_at(self, obj):
        return self._to_ist(obj.completed_at)

    @staticmethod
    def _to_ist(dt):
        if dt is None:
            return None
        import zoneinfo
        return dt.astimezone(zoneinfo.ZoneInfo('Asia/Kolkata')).strftime('%d %b %Y, %I:%M:%S %p IST')