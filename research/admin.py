from django.contrib import admin

from .models import CompanyContact, ResearchTask


class CompanyContactInline(admin.TabularInline):
    model = CompanyContact
    extra = 0


@admin.register(ResearchTask)
class ResearchTaskAdmin(admin.ModelAdmin):
    list_display = ('id', 'industry', 'location', 'status', 'emails_found', 'created_at')
    list_filter = ('status',)
    inlines = [CompanyContactInline]