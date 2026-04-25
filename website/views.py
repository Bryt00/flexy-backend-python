from django.shortcuts import render, redirect
from django.views.generic import TemplateView, ListView, DetailView, FormView
from django.http import HttpResponse
from django.urls import reverse_lazy
from django.contrib import messages
from django import forms
from django.db.models import Q
from .models import BlogPost, City, ContactInquiry, Testimonial, FAQItem, JobOpening

class HomeView(TemplateView):
    template_name = 'website/home.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['latest_posts'] = BlogPost.objects.filter(is_published=True).order_by('-published_at')[:3]
        cities = City.objects.filter(is_active=True)
        context['cities_count'] = cities.count()
        context['cities'] = cities
        context['testimonials'] = Testimonial.objects.all().order_by('-created_at')[:3]
        return context

class AboutView(TemplateView):
    template_name = 'website/about.html'

class ServicesView(TemplateView):
    template_name = 'website/services.html'

class HowItWorksView(TemplateView):
    template_name = 'website/how_it_works.html'

class DriveWithUsView(TemplateView):
    template_name = 'website/drive_with_us.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['cities'] = City.objects.filter(is_active=True).order_by('name')
        return context

class SafetyView(TemplateView):
    template_name = 'website/safety.html'

class CitiesView(ListView):
    model = City
    template_name = 'website/cities.html'
    context_object_name = 'cities'
    
    def get_queryset(self):
        return City.objects.filter(is_active=True)

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

class FAQView(TemplateView):
    template_name = 'website/faq.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
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
        return context

class PressView(TemplateView):
    template_name = 'website/press.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['press_posts'] = BlogPost.objects.filter(is_published=True, category='company').order_by('-published_at')[:5]
        return context

class CorporateView(TemplateView):
    template_name = 'website/corporate.html'

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

# Legal Pages
class TermsView(TemplateView):
    template_name = 'website/legal/terms.html'

class PrivacyView(TemplateView):
    template_name = 'website/legal/privacy.html'

class CookiesView(TemplateView):
    template_name = 'website/legal/cookies.html'

class DownloadView(TemplateView):
    template_name = 'website/download.html'

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
