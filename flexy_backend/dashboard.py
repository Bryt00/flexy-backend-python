from django.conf import settings
from django.utils.translation import gettext_lazy as _
from rides.models import Ride, Incident
from profiles.models import Profile

def dashboard_callback(request, context):
    """
    Callback for Unfold dashboard components.
    """
    total_rides = Ride.objects.count()
    active_rides = Ride.objects.filter(status='in_progress').count()
    active_sos = Incident.objects.filter(status='ACTIVE', type='SOS').count()
    online_drivers = Profile.objects.filter(user__role='driver', user__is_active=True).count() # Simplified logic

    context.update({
        "cards": [
            {
                "title": _("Active Rides"),
                "metric": active_rides,
                "footer": _("Total Rides: {}").format(total_rides),
                "icon": "commute",
            },
            {
                "title": _("Active SOS"),
                "metric": active_sos,
                "footer": _("Pending alerts"),
                "icon": "report_problem",
                "color": "red",
            },
            {
                "title": _("Drivers Online"),
                "metric": online_drivers,
                "icon": "directions_car",
            },
        "google_maps_api_key": settings.GOOGLE_MAPS_API_KEY,
    })

    return [
        {
            "title": _("Operational Snapshot"),
            "style": "grid-column: span 12 / span 12;",
            "items": [
                {
                    "title": _("Active Rides"),
                    "metric": active_rides,
                    "footer": _("Total Rides: {}").format(total_rides),
                    "icon": "commute",
                    "color": "sky",
                    "link": "/admin/rides/ride/?status=in_progress",
                },
                {
                    "title": _("SOS Alerts"),
                    "metric": active_sos,
                    "footer": _("Critical incidents"),
                    "icon": "report_problem",
                    "color": "red",
                    "link": "/admin/rides/incident/?type=SOS&status=ACTIVE",
                },
                {
                    "title": _("Fleet Online"),
                    "metric": online_drivers,
                    "footer": _("Drivers ready"),
                    "icon": "directions_car",
                    "color": "lime",
                    "link": "/admin/profiles/profile/",
                },
            ],
        },
        {
            "template": "admin/components/map_dashboard.html",
            "title": _("Command & Control - Live Fleet Monitoring"),
            "style": "grid-column: span 12 / span 12;",
            "context": {
                "google_maps_api_key": settings.GOOGLE_MAPS_API_KEY,
                "active_rides": active_rides,
                "online_drivers": online_drivers,
            },
        },
    ]
