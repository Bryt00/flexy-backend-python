from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache
from .models import (
    BlogPost, City, Testimonial, FAQItem, JobOpening,
    WebsiteSettings, BrandFeature, ServiceCategory, SafetyFeature,
    LegalDocument, HeroBanner, DriverBenefit
)

@receiver(post_save, sender=BlogPost)
@receiver(post_delete, sender=BlogPost)
@receiver(post_save, sender=City)
@receiver(post_delete, sender=City)
@receiver(post_save, sender=Testimonial)
@receiver(post_delete, sender=Testimonial)
@receiver(post_save, sender=FAQItem)
@receiver(post_delete, sender=FAQItem)
@receiver(post_save, sender=JobOpening)
@receiver(post_delete, sender=JobOpening)
@receiver(post_save, sender=WebsiteSettings)
@receiver(post_delete, sender=WebsiteSettings)
@receiver(post_save, sender=BrandFeature)
@receiver(post_delete, sender=BrandFeature)
@receiver(post_save, sender=ServiceCategory)
@receiver(post_delete, sender=ServiceCategory)
@receiver(post_save, sender=SafetyFeature)
@receiver(post_delete, sender=SafetyFeature)
@receiver(post_save, sender=LegalDocument)
@receiver(post_delete, sender=LegalDocument)
@receiver(post_save, sender=HeroBanner)
@receiver(post_delete, sender=HeroBanner)
@receiver(post_save, sender=DriverBenefit)
@receiver(post_delete, sender=DriverBenefit)
def clear_website_cache(sender, **kwargs):
    cache.clear()
