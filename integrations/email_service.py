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
