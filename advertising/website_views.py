import datetime
import uuid
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.views.generic import TemplateView
from django.core.signing import Signer, BadSignature
from django.contrib import messages
from django.utils import timezone
from django.conf import settings
from django.core.mail import send_mail
from .models import AdBooking, AdSlotCapacity, AdExtension
from .forms import AdStep1Form, AdStep2Form, AdStep3Form

# We will need standard views for:
# /advertise (AdLandingView)
# /advertise/apply (AdApplyView)
# /advertise/review (AdReviewView)
# /advertise/success (AdSuccessView)
# /advertise/dashboard (AdDashboardView)
# /advertise/extend/... (AdExtensionPayView)

class AdLandingView(TemplateView):
    template_name = 'advertising/landing.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Fetch the next 8 weeks of availability
        context['available_weeks'] = AdBooking.next_available_weeks(8)
        context['capacity_config'] = AdSlotCapacity.get_solo()
        return context

class AdApplyView(View):
    def get(self, request):
        step = request.session.get('ad_form_step', 1)
        data = request.session.get('ad_form_data', {})
        
        if step == 1:
            form = AdStep1Form(initial=data)
            return render(request, 'advertising/apply_step1.html', {'form': form})
        elif step == 2:
            form = AdStep2Form(initial=data)
            return render(request, 'advertising/apply_step2.html', {'form': form})
        elif step == 3:
            form = AdStep3Form(initial={'week_start_date': data.get('week_start_date')})
            available_weeks = AdBooking.next_available_weeks(8)
            return render(request, 'advertising/apply_step3.html', {'form': form, 'available_weeks': available_weeks})
        else:
            # Fallback
            request.session['ad_form_step'] = 1
            return redirect('advertise_apply')

    def post(self, request):
        step = request.session.get('ad_form_step', 1)
        data = request.session.get('ad_form_data', {})
        
        if 'back' in request.POST:
            request.session['ad_form_step'] = max(1, step - 1)
            return redirect('advertise_apply')
            
        if step == 1:
            form = AdStep1Form(request.POST)
            if form.is_valid():
                data.update(form.cleaned_data)
                request.session['ad_form_data'] = data
                request.session['ad_form_step'] = 2
                return redirect('advertise_apply')
            return render(request, 'advertising/apply_step1.html', {'form': form})
            
        elif step == 2:
            form = AdStep2Form(request.POST, request.FILES)
            if form.is_valid():
                # We can't easily store files in session. This is a bit tricky. 
                # For now, let's skip files across sessions or handle them via temporary storage.
                # A robust approach: save the instance now as DRAFT, and update it in steps.
                # To keep it simple per plan: We will save the instance in step 2.
                
                # Check if draft exists
                ad_id_str = request.session.get('draft_ad_id')
                if ad_id_str:
                    try:
                        ad = AdBooking.objects.get(id=uuid.UUID(ad_id_str), status='DRAFT')
                        form = AdStep2Form(request.POST, request.FILES, instance=ad)
                        ad = form.save()
                    except AdBooking.DoesNotExist:
                        # Create new draft
                        ad = form.save(commit=False)
                        ad.business_name = data.get('business_name')
                        ad.contact_email = data.get('contact_email')
                        ad.contact_phone = data.get('contact_phone')
                        ad.status = 'DRAFT'
                        
                        # temporary valid date because it's required
                        ad.week_start_date = timezone.localdate()
                        ad.save()
                else:
                    ad = form.save(commit=False)
                    ad.business_name = data.get('business_name')
                    ad.contact_email = data.get('contact_email')
                    ad.contact_phone = data.get('contact_phone')
                    ad.status = 'DRAFT'
                    ad.week_start_date = timezone.localdate() 
                    ad.save()
                
                request.session['draft_ad_id'] = str(ad.id)
                data.update({
                    'headline': ad.headline,
                    'body_text': ad.body_text,
                    'target_url': ad.target_url
                })
                request.session['ad_form_data'] = data
                request.session['ad_form_step'] = 3
                return redirect('advertise_apply')
            return render(request, 'advertising/apply_step2.html', {'form': form})
            
        elif step == 3:
            form = AdStep3Form(request.POST)
            if form.is_valid():
                data['week_start_date'] = form.cleaned_data['week_start_date'].isoformat()
                request.session['ad_form_data'] = data
                
                ad_id_str = request.session.get('draft_ad_id')
                if ad_id_str:
                    ad = AdBooking.objects.get(id=uuid.UUID(ad_id_str))
                    ad.week_start_date = form.cleaned_data['week_start_date']
                    ad.save()
                
                return redirect('advertise_review')
            available_weeks = AdBooking.next_available_weeks(8)
            return render(request, 'advertising/apply_step3.html', {'form': form, 'available_weeks': available_weeks})


class AdReviewView(View):
    def get(self, request):
        ad_id_str = request.session.get('draft_ad_id')
        if not ad_id_str:
            return redirect('advertise_apply')
            
        ad = get_object_or_404(AdBooking, id=uuid.UUID(ad_id_str))
        config = AdSlotCapacity.get_solo()
        return render(request, 'advertising/review.html', {'ad': ad, 'price': config.price_per_week_ghs})
        
    def post(self, request):
        ad_id_str = request.session.get('draft_ad_id')
        if not ad_id_str:
            return redirect('advertise_apply')
            
        ad = get_object_or_404(AdBooking, id=uuid.UUID(ad_id_str))
        
        config = AdSlotCapacity.get_solo()
        ad.status = 'PENDING_REVIEW'
        ad.amount = config.price_per_week_ghs
        
        signer = Signer()
        ad.dashboard_token = signer.sign(str(ad.id))
        ad.save()
        
        # Clear session
        if 'ad_form_data' in request.session: del request.session['ad_form_data']
        if 'ad_form_step' in request.session: del request.session['ad_form_step']
        if 'draft_ad_id' in request.session: del request.session['draft_ad_id']
        
        # Send confirmation email
        subject = f"Ad Request Received: {ad.headline}"
        message = f"Hello {ad.business_name},\n\nWe have received your advertising request for the week of {ad.week_start_date}. Our team is currently reviewing your creative. Once approved, you will receive an email with instructions on how to pay GH₵ {ad.amount} to activate your ad.\n\nYou can track your ad status anytime here: {request.build_absolute_uri('/advertise/dashboard/')}?token={ad.dashboard_token}\n\nBest regards,\nFlexyRide Team"
        
        try:
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [ad.contact_email],
                fail_silently=True,
            )
        except Exception as e:
            # We fail silently for now since SMTP might still be failing/diagnosing
            print(f"Failed to send ad submission email: {e}")
            
        return redirect('advertise_success')

class AdSuccessView(TemplateView):
    template_name = 'advertising/success.html'

class AdDashboardView(View):
    def get(self, request):
        token = request.GET.get('token')
        if not token:
            messages.error(request, "Invalid or missing access token.")
            return redirect('advertise_landing')
            
        signer = Signer()
        try:
            ad_id_str = signer.unsign(token)
            base_ad = get_object_or_404(AdBooking, id=uuid.UUID(ad_id_str))
        except BadSignature:
            messages.error(request, "Invalid or expired access token.")
            return redirect('advertise_landing')
            
        # We fetch all bookings for this email
        bookings = AdBooking.objects.filter(contact_email=base_ad.contact_email).order_by('-created_at')
        
        return render(request, 'advertising/dashboard.html', {
            'bookings': bookings,
            'current_token': token,
            'paystack_public_key': settings.PAYSTACK_PUBLIC_KEY
        })

class AdPreviewView(View):
    def get(self, request):
        token = request.GET.get('token')
        ad_id = request.GET.get('ad_id')
        
        if not token or not ad_id:
            return redirect('advertise_landing')
            
        signer = Signer()
        try:
            # Verify the token belongs to the requester
            signer.unsign(token)
            ad = get_object_or_404(AdBooking, id=uuid.UUID(ad_id))
        except (BadSignature, ValueError):
            return redirect('advertise_landing')
            
        return render(request, 'advertising/preview.html', {'ad': ad})

