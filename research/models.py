from django.db import models


class ResearchTask(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        IN_PROGRESS = 'IN_PROGRESS', 'In Progress'
        COMPLETED = 'COMPLETED', 'Completed'
        FAILED = 'FAILED', 'Failed'

    industry = models.CharField(max_length=200)
    location = models.CharField(max_length=200)
    top_companies = models.PositiveIntegerField(default=5)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    total_companies = models.PositiveIntegerField(default=0)
    emails_found = models.PositiveIntegerField(default=0)
    phones_found = models.PositiveIntegerField(default=0)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.industry} | {self.location} | {self.status}'


class CompanyContact(models.Model):
    class Confidence(models.TextChoices):
        HIGH = 'HIGH', 'High'
        MEDIUM = 'MEDIUM', 'Medium'
        LOW = 'LOW', 'Low'

    task = models.ForeignKey(
        ResearchTask, on_delete=models.CASCADE, related_name='contacts'
    )
    company_name = models.CharField(max_length=255)
    website = models.URLField(max_length=500, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    address = models.TextField(blank=True)
    source_url = models.URLField(max_length=500, blank=True)
    confidence = models.CharField(
        max_length=10, choices=Confidence.choices, default=Confidence.LOW
    )
    is_verified = models.BooleanField(default=False)
    is_selected = models.BooleanField(default=False)
    normalized_name = models.CharField(max_length=255, db_index=True)
    # Email campaign tracking
    is_mail_sent = models.BooleanField(default=False)
    email_draft_subject = models.TextField(blank=True)
    email_draft_body = models.TextField(blank=True)
    mail_draft_date = models.DateField(null=True, blank=True)
    mail_sent_at = models.DateTimeField(null=True, blank=True)
    mail_sent_to = models.EmailField(blank=True)
    campaign = models.ForeignKey(
        'EmailCampaign', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='contacts'
    )

    class Meta:
        unique_together = ('task', 'normalized_name')

    def __str__(self):
        return f'{self.company_name} ({self.task_id})'  
    
class KeyPerson(models.Model):
    company = models.ForeignKey(
        CompanyContact, on_delete=models.CASCADE, related_name='key_persons'
    )
    name = models.CharField(max_length=255)
    designation = models.CharField(max_length=255, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    linkedin_url = models.URLField(max_length=500, blank=True)

    class Meta:
        unique_together = ('company', 'name')

    def __str__(self):
        return f'{self.name} ({self.company_id})'
    
    
    
class EmailCampaign(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        DRAFTING = 'DRAFTING', 'Drafting'
        SCHEDULED = 'SCHEDULED', 'Scheduled'
        SENDING = 'SENDING', 'Sending'
        COMPLETED = 'COMPLETED', 'Completed'
        FAILED = 'FAILED', 'Failed'
        PAUSED = 'PAUSED', 'Paused'

    industry = models.CharField(max_length=200)
    location = models.CharField(max_length=200)
    requested_count = models.PositiveIntegerField()
    scheduled_send_date = models.DateField(null=True, blank=True)
    sent_count = models.PositiveIntegerField(default=0)
    failed_count = models.PositiveIntegerField(default=0)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Campaign {self.id} | {self.industry} | {self.status}'