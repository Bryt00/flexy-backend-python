from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from .models import BlogPost, City


class StaticViewSitemap(Sitemap):
    priority = 0.8
    changefreq = 'monthly'

    def items(self):
        return [
            'home', 'about', 'services', 'how_it_works', 'drive_with_us',
            'safety', 'cities', 'blog_list', 'contact', 'download',
            'faq', 'careers', 'press', 'corporate',
            'advertise_landing',
        ]

    def location(self, item):
        return reverse(item)


class BlogPostSitemap(Sitemap):
    priority = 0.6
    changefreq = 'weekly'

    def items(self):
        return BlogPost.objects.filter(is_published=True).order_by('-published_at')

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        return reverse('blog_detail', args=[obj.slug])


class CitySitemap(Sitemap):
    priority = 0.5
    changefreq = 'monthly'

    def items(self):
        return City.objects.filter(is_active=True).order_by('name')

    def location(self, obj):
        return reverse('cities')
