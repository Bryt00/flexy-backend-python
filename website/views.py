import json
import time
import uuid
import secrets
import random
import math
from datetime import timedelta
from django.utils import timezone
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.views.generic import TemplateView, ListView, DetailView, FormView
from django.http import HttpResponse, JsonResponse
from django.urls import reverse_lazy
from django.contrib import messages
from django import forms
from django.db.models import Q
from django.contrib.auth import login, logout
from django.views.decorators.csrf import csrf_exempt
from .models import (
    BlogPost, City, ContactInquiry, Testimonial, FAQItem, JobOpening,
    WebsiteSettings, BrandFeature, ServiceCategory, SafetyFeature, LegalDocument, HeroBanner, DriverBenefit, PassengerBenefit,
    PressRelease, PressDownload
)

from django.core.cache import cache

from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page

def get_global_context():
    # Cache global context for 15 minutes to reduce DB load
    settings = cache.get('global_website_settings')
    if not settings:
        settings = WebsiteSettings.objects.first()
        if not settings:
            settings = WebsiteSettings(
                total_riders_count="500k+",
                total_drivers_count="10k+",
                foundation_year=2024,
                mission_statement="To provide safe, reliable, and affordable transportation for every Ghanaian...",
                vision_statement="To become the backbone of urban infrastructure in West Africa..."
            )
        cache.set('global_website_settings', settings, 60 * 15)
    return {'site_settings': settings}

class HomeView(TemplateView):
    template_name = 'website/home.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(get_global_context())
        home_context = cache.get('website_home_context')
        if home_context is None:
            latest_posts = list(BlogPost.objects.filter(is_published=True).order_by('-published_at')[:3])
            cities = list(City.objects.filter(is_active=True))
            testimonials = list(Testimonial.objects.all().order_by('-created_at')[:3])
            features = list(BrandFeature.objects.all())
            hero = HeroBanner.objects.filter(page_name='home').first()
            home_context = {
                'latest_posts': latest_posts,
                'cities': cities,
                'cities_count': len(cities),
                'testimonials': testimonials,
                'features': features,
                'hero': hero,
            }
            cache.set('website_home_context', home_context, 60 * 15)
        context.update(home_context)
        return context

@method_decorator(cache_page(60 * 15), name='dispatch')
class AboutView(TemplateView):
    template_name = 'website/about.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(get_global_context())
        context['hero'] = HeroBanner.objects.filter(page_name='about').first()
        return context

class ServicesView(TemplateView):
    template_name = 'website/services.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(get_global_context())
        services_context = cache.get('website_services_context')
        if services_context is None:
            services_context = {
                'services': list(ServiceCategory.objects.filter(is_active=True)),
                'hero': HeroBanner.objects.filter(page_name='services').first()
            }
            cache.set('website_services_context', services_context, 60 * 15)
        context.update(services_context)
        return context

@method_decorator(cache_page(60 * 15), name='dispatch')
class HowItWorksView(TemplateView):
    template_name = 'website/how_it_works.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(get_global_context())
        return context

@method_decorator(cache_page(60 * 15), name='dispatch')
class DriveWithUsView(TemplateView):
    template_name = 'website/drive_with_us.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(get_global_context())
        context['cities'] = City.objects.filter(is_active=True).order_by('name')
        context['hero'] = HeroBanner.objects.filter(page_name='drive_with_us').first()
        context['benefits'] = list(DriverBenefit.objects.all())
        context['passenger_benefits'] = list(PassengerBenefit.objects.filter(is_active=True))
        return context

@method_decorator(cache_page(60 * 15), name='dispatch')
class SafetyView(TemplateView):
    template_name = 'website/safety.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(get_global_context())
        context['safety_features'] = SafetyFeature.objects.all()
        context['hero'] = HeroBanner.objects.filter(page_name='safety').first()
        return context

class CitiesView(ListView):
    model = City
    template_name = 'website/cities.html'
    context_object_name = 'cities'
    
    def get_queryset(self):
        return City.objects.filter(is_active=True)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(get_global_context())
        return context

class BlogListView(ListView):
    model = BlogPost
    template_name = 'website/blog/list.html'
    context_object_name = 'posts'
    paginate_by = 9

    def get_queryset(self):
        qs = BlogPost.objects.filter(is_published=True).order_by('-published_at')
        q = self.request.GET.get('q', '').strip()
        category = self.request.GET.get('category', '').strip()
        if q:
            qs = qs.filter(Q(title__icontains=q) | Q(excerpt__icontains=q) | Q(author_name__icontains=q))
        if category:
            qs = qs.filter(category=category)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(get_global_context())
        context['q'] = self.request.GET.get('q', '')
        context['active_category'] = self.request.GET.get('category', '')
        context['categories'] = BlogPost.CATEGORY_CHOICES
        return context

class BlogDetailView(DetailView):
    model = BlogPost
    template_name = 'website/blog/detail.html'
    context_object_name = 'post'
    
    def get_queryset(self):
        return BlogPost.objects.filter(is_published=True)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(get_global_context())
        return context

class FAQView(TemplateView):
    template_name = 'website/faq.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(get_global_context())
        faqs = cache.get('website_faqs')
        if faqs is None:
            faqs = list(FAQItem.objects.filter(is_active=True))
            cache.set('website_faqs', faqs, 60 * 15)
        # Group by category
        grouped = {}
        for faq in faqs:
            label = faq.get_category_display()
            if label not in grouped:
                grouped[label] = []
            grouped[label].append(faq)
        context['grouped_faqs'] = grouped
        context['total_count'] = len(faqs)
        return context

class CareersView(TemplateView):
    template_name = 'website/careers.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(get_global_context())
        openings = cache.get('website_job_openings')
        if openings is None:
            openings = list(JobOpening.objects.filter(is_active=True))
            cache.set('website_job_openings', openings, 60 * 15)
        # Group by department
        grouped = {}
        for job in openings:
            label = job.get_department_display()
            if label not in grouped:
                grouped[label] = []
            grouped[label].append(job)
        context['grouped_jobs'] = grouped
        context['total_openings'] = len(openings)
        context['hero'] = HeroBanner.objects.filter(page_name='careers').first()
        return context

class JobDetailView(DetailView):
    model = JobOpening
    template_name = 'website/careers_detail.html'
    context_object_name = 'job'
    
    def get_queryset(self):
        return JobOpening.objects.filter(is_active=True)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(get_global_context())
        # Suggest other roles
        context['other_jobs'] = JobOpening.objects.filter(is_active=True).exclude(id=self.object.id).order_by('?')[:3]
        return context

class PressListView(ListView):
    model = PressRelease
    template_name = 'website/press/list.html'
    context_object_name = 'press_releases'
    paginate_by = 9

    def get_queryset(self):
        qs = PressRelease.objects.filter(is_published=True).order_by('-published_at')
        
        category = self.request.GET.get('category', '').strip()
        year = self.request.GET.get('year', '').strip()
        q = self.request.GET.get('q', '').strip()

        if category:
            qs = qs.filter(category=category)
        if year and year.isdigit():
            qs = qs.filter(published_at__year=int(year))
        if q:
            qs = qs.filter(Q(title__icontains=q) | Q(subtitle__icontains=q) | Q(content__icontains=q) | Q(location__icontains=q))

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(get_global_context())
        context['q'] = self.request.GET.get('q', '')
        context['active_category'] = self.request.GET.get('category', '')
        context['active_year'] = self.request.GET.get('year', '')
        context['categories'] = PressRelease.CATEGORY_CHOICES
        
        from django.db.models.functions import ExtractYear
        years = PressRelease.objects.filter(is_published=True).annotate(year=ExtractYear('published_at')).values_list('year', flat=True).distinct().order_by('-year')
        context['years'] = list(years) if years else [2026, 2025, 2024]
        return context


class PressDetailView(DetailView):
    model = PressRelease
    template_name = 'website/press/detail.html'
    context_object_name = 'release'

    def get_queryset(self):
        return PressRelease.objects.filter(is_published=True)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(get_global_context())
        
        # Related press releases
        context['related_releases'] = PressRelease.objects.filter(is_published=True).exclude(id=self.object.id).order_by('-published_at')[:3]
        
        # Downloads
        downloads = list(self.object.downloads.filter(is_active=True))
        if not downloads:
            downloads = list(PressDownload.objects.filter(is_active=True, press_release__isnull=True)[:2])
        context['downloads'] = downloads
        
        return context

@method_decorator(cache_page(60 * 15), name='dispatch')
class CorporateView(TemplateView):
    template_name = 'website/corporate.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(get_global_context())
        return context

# Contact Form
class ContactForm(forms.ModelForm):
    website_url = forms.URLField(required=False, widget=forms.TextInput(attrs={'tabindex': '-1', 'autocomplete': 'off'}))
    
    class Meta:
        model = ContactInquiry
        fields = ['name', 'email', 'phone', 'category', 'message']

class ContactView(FormView):
    template_name = 'website/contact.html'
    form_class = ContactForm
    success_url = reverse_lazy('contact')
    
    def form_valid(self, form):
        # Honeypot check
        if form.cleaned_data.get('website_url'):
            # Silently reject
            messages.success(self.request, "Thank you! Your message has been received.")
            return redirect(self.success_url)
            
        form.save()
        messages.success(self.request, "Thank you! Your message has been received.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(get_global_context())
        context['hero'] = HeroBanner.objects.filter(page_name='contact').first()
        return context

# Legal Pages
class LegalHubView(TemplateView):
    template_name = 'website/legal/hub.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(get_global_context())
        
        all_docs = LegalDocument.objects.all().order_by('title')
        grouped_docs = {}
        for category_key, category_name in LegalDocument.CATEGORY_CHOICES:
            docs = [d for d in all_docs if d.category == category_key]
            if docs:
                grouped_docs[category_name] = docs
                
        if not grouped_docs and all_docs:
            grouped_docs['General Terms & Policies'] = list(all_docs)
            
        context['grouped_docs'] = grouped_docs
        return context

@method_decorator(cache_page(60 * 15), name='dispatch')
class LegalDocumentView(TemplateView):
    template_name = 'website/legal/detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(get_global_context())
        slug = kwargs.get('slug') or self.kwargs.get('slug')
        doc_type = kwargs.get('doc_type') or self.kwargs.get('doc_type')
        document = None
        if slug:
            document = LegalDocument.objects.filter(slug=slug).first()
        elif doc_type:
            document = LegalDocument.objects.filter(document_type=doc_type).order_by('-last_updated').first()
        
        if not document:
            # Provide a placeholder so the template renders gracefully
            from types import SimpleNamespace
            from django.utils import timezone
            type_labels = {'terms': 'Terms and Conditions', 'privacy': 'Privacy Policy', 'cookies': 'Cookie Policy'}
            document = SimpleNamespace(
                title=type_labels.get(doc_type, 'Legal Document'),
                content='<p>This document is currently being prepared. Please check back soon.</p>',
                last_updated=timezone.now(),
            )
        context['document'] = document
        return context

class TermsView(LegalHubView):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['badge_title'] = 'Terms and Conditions'
        context['page_title'] = 'How can we help?'
        context['page_subtitle'] = 'Explore terms and conditions documents for FlexyRide services.'
        return context

class PrivacyView(LegalHubView):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['badge_title'] = 'Privacy Policy at FlexyRide'
        context['page_title'] = 'How can we help?'
        context['page_subtitle'] = 'Explore privacy policy documents for FlexyRide services.'
        return context

class CookiesView(LegalDocumentView):
    def get_context_data(self, **kwargs):
        kwargs['doc_type'] = 'cookies'
        return super().get_context_data(**kwargs)

class DeleteAccountView(TemplateView):
    template_name = 'website/delete_account.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(get_global_context())
        return context

@method_decorator(cache_page(60 * 15), name='dispatch')
class DownloadView(TemplateView):
    template_name = 'website/download.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(get_global_context())
        return context

@method_decorator(cache_page(60 * 60 * 24), name='dispatch')
class RobotsView(TemplateView):
    def get(self, request, *args, **kwargs):
        content = (
            "User-agent: *\n"
            "Disallow: /admin/\n"
            "Disallow: /api/\n"
            "Disallow: /advertise/review/\n"
            "Disallow: /advertise/dashboard/\n\n"
            f"Sitemap: {request.build_absolute_uri('/sitemap.xml')}\n"
        )
        return HttpResponse(content, content_type='text/plain')

class CityDetailView(DetailView):
    model = City
    template_name = 'website/city_detail.html'
    context_object_name = 'city'

    def get_object(self, queryset=None):
        from django.utils.text import slugify
        slug = self.kwargs.get('slug')
        for city in City.objects.filter(is_active=True):
            if slugify(city.name) == slug:
                return city
        from django.http import Http404
        raise Http404("City not found")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(get_global_context())
        from website.models import Testimonial
        city_name = self.object.name.lower()
        context['testimonials'] = Testimonial.objects.filter(
            Q(quote__icontains=city_name) | Q(role__icontains=city_name)
        )[:3]
        if not context['testimonials'].exists():
            context['testimonials'] = Testimonial.objects.all().order_by('-created_at')[:3]
        return context


# ==============================================================================
# DEVELOPER PORTAL & API DOCUMENTATION VIEWS
# ==============================================================================

class DeveloperView(TemplateView):
    """
    Unified Developer Portal & Interactive API Documentation console.
    Rendered with void navbar & footer for a dedicated portal experience.
    """
    template_name = 'website/developer.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(get_global_context())
        context['hide_navbar'] = True
        context['hide_footer'] = True
        user = self.request.user
        context['is_authenticated'] = user.is_authenticated

        from integrations.models import APIKey, AVAILABLE_SCOPES, DEFAULT_SCOPES
        if user.is_authenticated:
            context['current_user'] = {
                'id': str(user.id),
                'email': getattr(user, 'email', ''),
                'phone': getattr(user, 'phone_number', ''),
                'name': f"{getattr(user, 'first_name', '')} {getattr(user, 'last_name', '')}".strip() or getattr(user, 'email', 'Developer'),
                'role': getattr(user, 'role', 'developer'),
            }
            keys = APIKey.objects.filter(user=user, is_active=True).order_by('-created_at')
            context['api_keys'] = [
                {
                    'id': str(k.id),
                    'name': k.name,
                    'environment': k.environment,
                    'prefix': k.prefix,
                    'scopes': k.scopes or [],
                    'webhook_url': k.webhook_url or '',
                    'webhook_secret': k.webhook_secret or '',
                    'rate_limit': k.rate_limit,
                    'created_at': k.created_at.strftime('%d %b %Y') if k.created_at else '',
                    'last_used_at': k.last_used_at.strftime('%d %b %Y, %H:%M') if k.last_used_at else 'Never',
                } for k in keys
            ]
        else:
            context['current_user'] = None
            context['api_keys'] = []

        context['available_scopes'] = [
            {'scope': s[0], 'description': s[1]} for s in AVAILABLE_SCOPES
        ]
        context['default_scopes'] = list(DEFAULT_SCOPES)
        context['api_keys_json'] = json.dumps(context['api_keys'])
        context['available_scopes_json'] = json.dumps(context['available_scopes'])
        context['live_base_url'] = 'https://api.flexyridegh.com/api'
        context['sandbox_base_url'] = 'https://sandbox-api.flexyridegh.com/api'
        context['local_base_url'] = '/v1'
        context['ws_url'] = 'wss://api.flexyridegh.com/ws'
        return context


@method_decorator(csrf_exempt, name='dispatch')
class DeveloperAjaxLoginView(View):
    """Logs the developer in via AJAX, binding their session."""
    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
        except Exception:
            data = request.POST

        email = data.get('email', '').strip()
        password = data.get('password', '')

        if not email or not password:
            return JsonResponse({'success': False, 'error': 'Email and password are required.'}, status=400)

        from django.contrib.auth import get_user_model
        User = get_user_model()
        user = User.objects.filter(email__iexact=email).first()
        if user and user.check_password(password):
            login(request, user)
            return JsonResponse({
                'success': True,
                'user': {
                    'id': str(user.id),
                    'email': user.email,
                    'name': f"{getattr(user, 'first_name', '')} {getattr(user, 'last_name', '')}".strip() or user.email,
                }
            })
        return JsonResponse({'success': False, 'error': 'Invalid email or password.'}, status=401)


@method_decorator(csrf_exempt, name='dispatch')
class DeveloperAjaxLogoutView(View):
    """Logs out the developer user from the session via POST or GET."""
    def post(self, request, *args, **kwargs):
        logout(request)
        try:
            request.session.flush()
        except Exception:
            pass
        response = JsonResponse({'success': True})
        session_cookie = getattr(settings, 'SESSION_COOKIE_NAME', 'sessionid')
        response.delete_cookie(session_cookie)
        return response

    def get(self, request, *args, **kwargs):
        logout(request)
        try:
            request.session.flush()
        except Exception:
            pass
        response = redirect('developer')
        session_cookie = getattr(settings, 'SESSION_COOKIE_NAME', 'sessionid')
        response.delete_cookie(session_cookie)
        return response


@method_decorator(csrf_exempt, name='dispatch')
class DeveloperAjaxKeysView(View):
    def get(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Unauthorized'}, status=401)
        from integrations.models import APIKey
        keys = APIKey.objects.filter(user=request.user, is_active=True).order_by('-created_at')
        data = [
            {
                'id': str(k.id),
                'name': k.name,
                'environment': k.environment,
                'prefix': k.prefix,
                'scopes': k.scopes or [],
                'webhook_url': k.webhook_url or '',
                'webhook_secret': k.webhook_secret or '',
                'rate_limit': k.rate_limit,
                'created_at': k.created_at.strftime('%d %b %Y') if k.created_at else '',
                'last_used_at': k.last_used_at.strftime('%d %b %Y, %H:%M') if k.last_used_at else 'Never',
            } for k in keys
        ]
        return JsonResponse({'keys': data})

    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Unauthorized'}, status=401)
        try:
            payload = json.loads(request.body)
        except Exception:
            payload = request.POST

        name = payload.get('name', '').strip()
        if not name:
            return JsonResponse({'error': 'Name is required'}, status=400)

        environment = payload.get('environment', 'LIVE')
        if environment not in ['LIVE', 'SANDBOX']:
            environment = 'LIVE'

        scopes = payload.get('scopes')
        webhook_url = payload.get('webhook_url', '').strip() or None

        from integrations.models import APIKey
        raw_key, instance = APIKey.generate_key(
            name=name,
            user=request.user,
            environment=environment,
            scopes=scopes,
            webhook_url=webhook_url
        )

        return JsonResponse({
            'success': True,
            'key': {
                'id': str(instance.id),
                'name': instance.name,
                'environment': instance.environment,
                'prefix': instance.prefix,
                'scopes': instance.scopes or [],
                'webhook_url': instance.webhook_url or '',
                'webhook_secret': instance.webhook_secret or '',
                'rate_limit': instance.rate_limit,
                'created_at': instance.created_at.strftime('%d %b %Y'),
                'last_used_at': 'Never'
            },
            'raw_key': raw_key,
            'webhook_secret': instance.webhook_secret
        })


@method_decorator(csrf_exempt, name='dispatch')
class DeveloperAjaxRotateKeyView(View):
    def post(self, request, key_id, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Unauthorized'}, status=401)
        from integrations.models import APIKey
        try:
            key = APIKey.objects.get(id=key_id, user=request.user, is_active=True)
        except APIKey.DoesNotExist:
            return JsonResponse({'error': 'Key not found'}, status=404)

        new_raw_key = key.rotate_secret()
        cache.delete(f"auth_apikey_id:{key.prefix}")
        return JsonResponse({
            'success': True,
            'id': str(key.id),
            'prefix': key.prefix,
            'raw_key': new_raw_key
        })


@method_decorator(csrf_exempt, name='dispatch')
class DeveloperAjaxRevokeKeyView(View):
    def post(self, request, key_id, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Unauthorized'}, status=401)
        from integrations.models import APIKey
        try:
            key = APIKey.objects.get(id=key_id, user=request.user, is_active=True)
        except APIKey.DoesNotExist:
            return JsonResponse({'error': 'Key not found'}, status=404)

        key.is_active = False
        key.save()
        cache.delete(f"auth_apikey_id:{key.prefix}")
        return JsonResponse({'success': True})


@method_decorator(csrf_exempt, name='dispatch')
class DeveloperAjaxTestWebhookView(View):
    def post(self, request, key_id, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Unauthorized'}, status=401)
        from integrations.models import APIKey
        from integrations.webhooks import WebhookService
        try:
            key = APIKey.objects.get(id=key_id, user=request.user, is_active=True)
        except APIKey.DoesNotExist:
            return JsonResponse({'error': 'Key not found'}, status=404)

        if not key.webhook_url:
            return JsonResponse({'success': False, 'error': 'No webhook URL configured on this key'}, status=400)

        result = WebhookService.send_event(
            webhook_url=key.webhook_url,
            secret=key.webhook_secret or '',
            event_type='delivery.test_ping',
            data={
                'event': 'delivery.test_ping',
                'delivery_id': f'test_{uuid.uuid4().hex[:10]}',
                'timestamp': timezone.now().isoformat(),
                'status': 'DISPATCHED'
            }
        )
        return JsonResponse(result)


@method_decorator(csrf_exempt, name='dispatch')
class DeveloperPlaygroundProxyView(View):
    def post(self, request, *args, **kwargs):
        try:
            payload = json.loads(request.body)
        except Exception:
            payload = request.POST

        method = payload.get('method', 'GET').upper()
        endpoint = payload.get('endpoint', '').strip()
        body = payload.get('payload')

        start_time = time.time()

        if '/v1/deliveries/estimate' in endpoint:
            pickup_lat = body.get('pickup_lat', 5.55602) if isinstance(body, dict) else 5.55602
            pickup_lng = body.get('pickup_lng', -0.18241) if isinstance(body, dict) else -0.18241
            dropoff_lat = body.get('dropoff_lat', 5.60512) if isinstance(body, dict) else 5.60512
            dropoff_lng = body.get('dropoff_lng', -0.17721) if isinstance(body, dict) else -0.17721
            weight_tier = body.get('weight_tier_id', 'standard') if isinstance(body, dict) else 'standard'

            dlat = math.radians(float(dropoff_lat) - float(pickup_lat))
            dlng = math.radians(float(dropoff_lng) - float(pickup_lng))
            a = math.sin(dlat/2)**2 + math.cos(math.radians(float(pickup_lat))) * math.cos(math.radians(float(dropoff_lat))) * math.sin(dlng/2)**2
            c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
            dist_km = round(6371 * c, 2)
            if dist_km == 0:
                dist_km = 7.42
            fare = round(10.0 + (dist_km * 2.0), 2)
            latency_ms = int((time.time() - start_time) * 1000) + 12

            return JsonResponse({
                'status': 200,
                'status_text': '200 OK',
                'latency_ms': latency_ms,
                'data': {
                    'success': True,
                    'data': {
                        'distance_km': dist_km,
                        'duration_minutes': int(dist_km * 3) + 5,
                        'currency': 'GHS',
                        'base_fare': 10.00,
                        'distance_fare': round(dist_km * 2.0, 2),
                        'estimated_fare': fare,
                        'weight_tier': weight_tier,
                        'surge_multiplier': 1.0,
                        'quote_expires_at': (timezone.now() + timedelta(minutes=15)).isoformat()
                    }
                }
            })

        elif '/v1/deliveries' in endpoint and method == 'POST':
            tracking_num = f"FLX-DEL-{random.randint(10000, 99999)}"
            del_id = f"del_{uuid.uuid4().hex[:15]}"
            latency_ms = int((time.time() - start_time) * 1000) + 18
            return JsonResponse({
                'status': 201,
                'status_text': '201 Created',
                'latency_ms': latency_ms,
                'data': {
                    'success': True,
                    'data': {
                        'id': del_id,
                        'tracking_number': tracking_num,
                        'status': 'REQUESTED',
                        'fare': 28.50,
                        'currency': 'GHS',
                        'sender_name': body.get('sender_name') if isinstance(body, dict) else 'Store Partner',
                        'recipient_name': body.get('recipient_name') if isinstance(body, dict) else 'Recipient',
                        'tracking_url': f"https://flexyridegh.com/track/{tracking_num}",
                        'created_at': timezone.now().isoformat()
                    }
                }
            })

        elif '/v1/rides/estimate' in endpoint:
            latency_ms = int((time.time() - start_time) * 1000) + 14
            return JsonResponse({
                'status': 200,
                'status_text': '200 OK',
                'latency_ms': latency_ms,
                'data': {
                    'success': True,
                    'data': {
                        'distance_km': 6.8,
                        'duration_minutes': 18,
                        'tiers': [
                            {'tier_id': 'standard', 'name': 'FlexyGo', 'fare_ghs': 32.50, 'eta_minutes': 3},
                            {'tier_id': 'comfort', 'name': 'FlexyComfort', 'fare_ghs': 48.00, 'eta_minutes': 5},
                            {'tier_id': 'van', 'name': 'FlexyVan (7 Seater)', 'fare_ghs': 75.00, 'eta_minutes': 8}
                        ]
                    }
                }
            })

        elif '/v1/deliveries' in endpoint and 'cancel' in endpoint:
            latency_ms = int((time.time() - start_time) * 1000) + 12
            return JsonResponse({
                'status': 200,
                'status_text': '200 OK',
                'latency_ms': latency_ms,
                'data': {
                    'status': 'success',
                    'message': 'Delivery order successfully cancelled',
                    'data': {
                        'id': 'e81d77a0-07bf-4cf2-8321-df54c79401ab',
                        'status': 'CANCELLED',
                        'cancellation_fee': 0.00,
                        'cancelled_at': timezone.now().isoformat()
                    }
                }
            })

        elif '/v1/deliveries/categories' in endpoint or '/v1/settings/vehicle-categories' in endpoint:
            latency_ms = int((time.time() - start_time) * 1000) + 9
            return JsonResponse({
                'status': 200,
                'status_text': '200 OK',
                'latency_ms': latency_ms,
                'data': {
                    'status': 'success',
                    'data': [
                        {'id': 'motorbike', 'name': 'Express Motorcycle', 'base_fare': 15.00, 'max_weight_kg': 15.0, 'description': 'Fastest parcel dispatch for letters, food, small electronics.'},
                        {'id': 'pragya', 'name': 'Pragya Tricycle', 'base_fare': 20.00, 'max_weight_kg': 50.0, 'description': 'Affordable medium-capacity local courier cargo.'},
                        {'id': 'courier_van', 'name': 'Courier Delivery Van', 'base_fare': 45.00, 'max_weight_kg': 500.0, 'description': 'Heavy bulk cargo, pallets, and multi-box fulfillment.'}
                    ]
                }
            })

        elif '/v1/deliveries' in endpoint and method == 'GET':
            latency_ms = int((time.time() - start_time) * 1000) + 15
            return JsonResponse({
                'status': 200,
                'status_text': '200 OK',
                'latency_ms': latency_ms,
                'data': {
                    'status': 'success',
                    'data': {
                        'id': 'e81d77a0-07bf-4cf2-8321-df54c79401ab',
                        'tracking_code': 'FX-DEL-984310',
                        'status': 'IN_TRANSIT',
                        'driver': {
                            'name': 'Kofi Boateng',
                            'phone': '+233240001122',
                            'vehicle_plate': 'GW-4402-21',
                            'vehicle_model': 'Honda ACE 125 Motorbike',
                            'rating': 4.92,
                            'current_lat': 5.5891,
                            'current_lng': -0.1982
                        },
                        'estimated_eta_minutes': 7,
                        'pickup_time': timezone.now().isoformat(),
                        'completed_at': None
                    }
                }
            })

        elif '/v1/rides/request' in endpoint and method == 'POST':
            trip_id = f"trip_{uuid.uuid4().hex[:12]}"
            latency_ms = int((time.time() - start_time) * 1000) + 20
            return JsonResponse({
                'status': 201,
                'status_text': '201 Created',
                'latency_ms': latency_ms,
                'data': {
                    'status': 'success',
                    'message': 'Ride request broadcasting to nearby drivers',
                    'data': {
                        'trip_id': trip_id,
                        'status': 'SEARCHING',
                        'tier': body.get('tier', 'comfort') if isinstance(body, dict) else 'comfort',
                        'estimated_fare': 52.00,
                        'currency': 'GHS',
                        'created_at': timezone.now().isoformat()
                    }
                }
            })

        elif '/v1/rides' in endpoint and method == 'GET':
            latency_ms = int((time.time() - start_time) * 1000) + 14
            return JsonResponse({
                'status': 200,
                'status_text': '200 OK',
                'latency_ms': latency_ms,
                'data': {
                    'status': 'success',
                    'data': {
                        'trip_id': 'trip_88fa12bc0991',
                        'status': 'ACCEPTED',
                        'driver': {
                            'name': 'Emmanuel Cudjoe',
                            'phone': '+233241112233',
                            'vehicle_plate': 'GR-8890-22',
                            'vehicle_model': 'Toyota Corolla 2021',
                            'rating': 4.95,
                            'current_lat': 5.6189,
                            'current_lng': -0.1702
                        },
                        'eta_minutes': 4,
                        'fare': 52.00
                    }
                }
            })

        else:
            latency_ms = int((time.time() - start_time) * 1000) + 10
            return JsonResponse({
                'status': 200,
                'status_text': '200 OK',
                'latency_ms': latency_ms,
                'data': {
                    'success': True,
                    'message': f"Request to {endpoint} simulated successfully",
                    'timestamp': timezone.now().isoformat()
                }
            })


class DeveloperGuideDownloadView(View):
    """Allows developers to download the full API Integration Guide in raw Markdown."""
    def get(self, request, *args, **kwargs):
        from django.http import FileResponse, Http404
        from django.conf import settings
        import os

        # Check candidate locations for API_INTEGRATION_GUIDE.md
        candidate_paths = [
            os.path.join(settings.BASE_DIR, '..', 'docs', 'API_INTEGRATION_GUIDE.md'),
            os.path.join(settings.BASE_DIR, 'docs', 'API_INTEGRATION_GUIDE.md'),
            '/home/r4v3n_00/dockets/work/patmac/flexyride/docs/API_INTEGRATION_GUIDE.md',
        ]
        for p in candidate_paths:
            if os.path.exists(p):
                return FileResponse(
                    open(p, 'rb'),
                    as_attachment=True,
                    filename='FlexyRide_API_Integration_Guide.md',
                    content_type='text/markdown'
                )
        raise Http404("API Integration Guide document not found.")
