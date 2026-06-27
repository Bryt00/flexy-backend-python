import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "flexy_backend.settings")
django.setup()

from marketing.models import Campaign
print("Total Campaigns:", Campaign.objects.count())
print("Active Campaigns:", Campaign.objects.filter(status='ACTIVE').count())
