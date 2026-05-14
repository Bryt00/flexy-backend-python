from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import TemplateView, ListView, DetailView, FormView
from django.http import HttpResponse
from django.urls import reverse_lazy
from django.contrib import messages
from django import forms
from django.db.models import Q
from .models import (
    BlogPost, City, ContactInquiry, Testimonial, FAQItem, JobOpening,
    WebsiteSettings, BrandFeature, ServiceCategory, SafetyFeature, LegalDocument, HeroBanner
)

def get_global_context():
    settings = WebsiteSettings.objects.first()
    if not settings:
        settings = WebsiteSettings(
            total_riders_count="500k+",
            total_drivers_count="10k+",
            foundation_year=2024,
            mission_statement="To provide safe, reliable, and affordable transportation for every Ghanaian...",
            vision_statement="To become the backbone of urban infrastructure in West Africa..."
        )
    return {'site_settings': settings}

class HomeView(TemplateView):
    template_name = 'website/home.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(get_global_context())
        context['latest_posts'] = BlogPost.objects.filter(is_published=True).order_by('-published_at')[:3]
        cities = City.objects.filter(is_active=True)
        context['cities_count'] = cities.count()
        context['cities'] = cities
        context['testimonials'] = Testimonial.objects.all().order_by('-created_at')[:3]
        context['features'] = BrandFeature.objects.all()
        context['hero'] = HeroBanner.objects.filter(page_name='home').first()
        return context

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
        context['services'] = ServiceCategory.objects.filter(is_active=True)
        context['hero'] = HeroBanner.objects.filter(page_name='services').first()
        return context

class HowItWorksView(TemplateView):
    template_name = 'website/how_it_works.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(get_global_context())
        return context

class DriveWithUsView(TemplateView):
    template_name = 'website/drive_with_us.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(get_global_context())
        context['cities'] = City.objects.filter(is_active=True).order_by('name')
        return context

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
        faqs = FAQItem.objects.filter(is_active=True)
        # Group by category
        grouped = {}
        for faq in faqs:
            label = faq.get_category_display()
            if label not in grouped:
                grouped[label] = []
            grouped[label].append(faq)
        context['grouped_faqs'] = grouped
        context['total_count'] = faqs.count()
        return context

class CareersView(TemplateView):
    template_name = 'website/careers.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(get_global_context())
        openings = JobOpening.objects.filter(is_active=True)
        # Group by department
        grouped = {}
        for job in openings:
            label = job.get_department_display()
            if label not in grouped:
                grouped[label] = []
            grouped[label].append(job)
        context['grouped_jobs'] = grouped
        context['total_openings'] = openings.count()
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

class PressView(TemplateView):
    template_name = 'website/press.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(get_global_context())
        context['press_posts'] = BlogPost.objects.filter(is_published=True, category='company').order_by('-published_at')[:5]
        return context

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
            type_labels = {'terms': 'Terms of Service', 'privacy': 'Privacy Policy', 'cookies': 'Cookie Policy'}
            document = SimpleNamespace(
                title=type_labels.get(doc_type, 'Legal Document'),
                content='<p>This document is currently being prepared. Please check back soon.</p>',
                last_updated=timezone.now(),
            )
        context['document'] = document
        return context

class TermsView(LegalDocumentView):
    def get_context_data(self, **kwargs):
        kwargs['doc_type'] = 'terms'
        return super().get_context_data(**kwargs)

class PrivacyView(LegalDocumentView):
    def get_context_data(self, **kwargs):
        kwargs['doc_type'] = 'privacy'
        return super().get_context_data(**kwargs)

class CookiesView(LegalDocumentView):
    def get_context_data(self, **kwargs):
        kwargs['doc_type'] = 'cookies'
        return super().get_context_data(**kwargs)

class DownloadView(TemplateView):
    template_name = 'website/download.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(get_global_context())
        return context

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
