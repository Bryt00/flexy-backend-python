from django.urls import path, include
from django.contrib.sitemaps.views import sitemap
from . import views
from .sitemaps import StaticViewSitemap, BlogPostSitemap, CitySitemap

sitemaps = {
    'static': StaticViewSitemap,
    'blog': BlogPostSitemap,
    'cities': CitySitemap,
}

urlpatterns = [
    path('', views.HomeView.as_view(), name='home'),
    path('about/', views.AboutView.as_view(), name='about'),
    path('services/', views.ServicesView.as_view(), name='services'),
    path('how-it-works/', views.HowItWorksView.as_view(), name='how_it_works'),
    path('drive-with-us/', views.DriveWithUsView.as_view(), name='drive_with_us'),
    path('safety/', views.SafetyView.as_view(), name='safety'),
    path('cities/', views.CitiesView.as_view(), name='cities'),
    path('blog/', views.BlogListView.as_view(), name='blog_list'),
    path('blog/<slug:slug>/', views.BlogDetailView.as_view(), name='blog_detail'),
    path('contact/', views.ContactView.as_view(), name='contact'),
    path('download/', views.DownloadView.as_view(), name='download'),
    path('faq/', views.FAQView.as_view(), name='faq'),
    path('careers/', views.CareersView.as_view(), name='careers'),
    path('careers/<slug:slug>/', views.JobDetailView.as_view(), name='career_detail'),
    path('press/', views.PressView.as_view(), name='press'),
    path('corporate/', views.CorporateView.as_view(), name='corporate'),
    path('legal/terms/', views.TermsView.as_view(), name='terms'),
    path('legal/privacy/', views.PrivacyView.as_view(), name='privacy'),
    path('legal/cookies/', views.CookiesView.as_view(), name='cookies'),
    path('advertise/', include('advertising.website_urls')),
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),
    path('robots.txt', views.RobotsView.as_view(), name='robots'),
]
