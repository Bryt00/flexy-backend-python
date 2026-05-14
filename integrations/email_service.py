from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class EmailService:
    @staticmethod
    def send_welcome_email(user):
        """
        Sends a welcome email to a newly registered user.
        """
        subject = 'Welcome to FlexyRide!'
        context = {
            'user': user,
            'app_name': 'FlexyRide'
        }
        
        try:
            html_message = render_to_string('emails/welcome.html', context)
            send_mail(
                subject,
                '', # Plain text version empty
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                html_message=html_message,
                fail_silently=False,
            )
            logger.info(f"Welcome email sent to {user.email}")
        except Exception as e:
            logger.error(f"Failed to send welcome email to {user.email}: {str(e)}")

    @staticmethod
    def send_otp_email(email, otp_code):
        """
        Sends an OTP code for authentication/verification.
        """
        subject = f'{otp_code} is your FlexyRide verification code'
        context = {
            'otp_code': otp_code,
            'expires_in': '10 minutes'
        }
        
        try:
            html_message = render_to_string('emails/otp.html', context)
            send_mail(
                subject,
                f"Your verification code is {otp_code}",
                settings.DEFAULT_FROM_EMAIL,
                [email],
                html_message=html_message,
                fail_silently=False,
            )
            logger.info(f"OTP email sent to {email}")
        except Exception as e:
            logger.error(f"Failed to send OTP email to {email}: {str(e)}")

    @staticmethod
    def send_ride_receipt_email(ride, receipt):
        """
        Sends an itemized receipt after trip completion.
        """
        subject = f'Your FlexyRide Trip Receipt - {receipt.receipt_no}'
        context = {
            'ride': ride,
            'receipt': receipt,
            'user': ride.rider
        }
        
        try:
            html_message = render_to_string('emails/receipt.html', context)
            send_mail(
                subject,
                f"Your trip receipt {receipt.receipt_no} for {receipt.total_fare} GHS",
                settings.DEFAULT_FROM_EMAIL,
                [ride.rider.email],
                html_message=html_message,
                fail_silently=False,
            )
            logger.info(f"Receipt email sent for ride {ride.id}")
        except Exception as e:
            logger.error(f"Failed to send receipt email for ride {ride.id}: {str(e)}")
    @staticmethod
    def send_verification_status_email(user, is_approved, reason=None):
        """
        Sends an email to the driver informing them of the admin's verification decision.
        """
        subject = 'Update on your FlexyRide Driver Verification' if is_approved else 'Action Required: Your FlexyRide Driver Verification'
        context = {
            'user': user,
            'is_approved': is_approved,
            'reason': reason,
            'app_name': 'FlexyRide'
        }
        
        try:
            html_message = render_to_string('emails/verification_result.html', context)
            send_mail(
                subject,
                f"Your driver verification has been {'approved' if is_approved else 'rejected'}.",
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                html_message=html_message,
                fail_silently=False,
            )
            logger.info(f"Verification email sent to {user.email} (Approved: {is_approved})")
        except Exception as e:
            logger.error(f"Failed to send verification email to {user.email}: {str(e)}")

    @staticmethod
    def send_admin_verification_notification_email(driver_name, driver_email):
        """
        Notifies the admin that a new driver profile is pending verification.
        """
        subject = f'NEW VERIFICATION: {driver_name} is pending review'
        message = f"A new driver profile has been submitted for verification.\n\nDriver: {driver_name}\nEmail: {driver_email}\n\nPlease log in to the admin dashboard to review the documents."
        
        try:
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [settings.ADMIN_EMAIL],
                fail_silently=False,
            )
            logger.info(f"Admin verification notification sent for {driver_email}")
        except Exception as e:
            logger.error(f"Failed to send admin verification notification: {str(e)}")

    @staticmethod
    def send_admin_ad_notification_email(business_name, contact_email):
        """
        Notifies the admin that a new ad booking has been submitted.
        """
        subject = f'NEW AD SUBMISSION: {business_name}'
        message = f"A new ad booking has been submitted for review.\n\nBusiness: {business_name}\nContact: {contact_email}\n\nPlease log in to the admin dashboard to review the ad creative."
        
        try:
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [settings.ADMIN_EMAIL],
                fail_silently=False,
            )
            logger.info(f"Admin ad notification sent for {business_name}")
        except Exception as e:
            logger.error(f"Failed to send admin ad notification: {str(e)}")

    @staticmethod
    def send_ad_status_email(contact_email, business_name, is_approved, reason=None):
        """
        Sends an email to the business informing them of the ad approval/rejection.
        """
        subject = f'Your Ad Booking for {business_name} was Approved!' if is_approved else f'Action Required: Your Ad Booking for {business_name}'
        
        if is_approved:
            message = f"Congratulations! Your ad for {business_name} has been approved.\n\nYou can now proceed to payment in your ad dashboard to go live.\n\nThank you for choosing FlexyRide."
        else:
            message = f"Your ad for {business_name} was not approved.\n\nReason: {reason if reason else 'Creative does not meet our guidelines.'}\n\nPlease update your creative in the dashboard and resubmit."

        try:
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [contact_email],
                fail_silently=False,
            )
            logger.info(f"Ad status email sent to {contact_email} (Approved: {is_approved})")
        except Exception as e:
            logger.error(f"Failed to send ad status email to {contact_email}: {str(e)}")

    @staticmethod
    def send_ad_report_email(business_name, contact_email, stats_dict):
        """
        Sends a weekly performance report for an ad booking.
        """
        subject = f'Weekly Ad Performance Report: {business_name}'
        
        total_impressions = stats_dict.get('total_impressions', 0)
        total_clicks = stats_dict.get('total_clicks', 0)
        
        message = f"Hello {business_name},\n\nHere is your ad performance report for the past week:\n\nTotal Views: {total_impressions}\nTotal Clicks: {total_clicks}\n\n"
        
        if stats_dict.get('has_variant_b'):
            message += f"Variant A - Views: {stats_dict.get('impressions_a', 0)}, Clicks: {stats_dict.get('clicks_a', 0)}\n"
            message += f"Variant B - Views: {stats_dict.get('impressions_b', 0)}, Clicks: {stats_dict.get('clicks_b', 0)}\n\n"
            
        message += "Thank you for advertising with FlexyRide. If you wish to extend your campaign, please log into your dashboard.\n\nBest regards,\nThe FlexyRide Team"

        try:
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [contact_email],
                fail_silently=False,
            )
            logger.info(f"Ad report email sent to {contact_email}")
        except Exception as e:
            logger.error(f"Failed to send ad report email to {contact_email}: {str(e)}")
    @staticmethod
    def send_sos_alert_email(incident):
        """
        Urgent notification to admin when SOS is triggered.
        """
        from profiles.models import Profile
        reporter_name = "Unknown"
        try:
            profile = Profile.objects.get(user=incident.reporter)
            reporter_name = profile.full_name or incident.reporter.email
        except:
            reporter_name = incident.reporter.email

        subject = f'🚨 SOS ALERT: {reporter_name}'
        message = (
            f"URGENT: SOS triggered by {incident.reporter.role} {incident.reporter.email}\n"
            f"Name: {reporter_name}\n"
            f"Ride ID: {incident.ride.id}\n"
            f"Description: {incident.description}\n"
            f"Coordinates: {incident.location_lat}, {incident.location_lng}\n"
            f"Google Maps Link: https://www.google.com/maps?q={incident.location_lat},{incident.location_lng}\n\n"
            f"Please investigate immediately via the Admin Dashboard."
        )
        
        try:
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [settings.ADMIN_EMAIL],
                fail_silently=False,
            )
            logger.info(f"SOS Alert email sent for incident {incident.id}")
        except Exception as e:
            logger.error(f"Failed to send SOS Alert email: {str(e)}")
