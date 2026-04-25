from django.db import models
from django.utils.text import slugify
from django_ckeditor_5.fields import CKEditor5Field

class BlogPost(models.Model):
    CATEGORY_CHOICES = [
        ('company', 'Company News'),
        ('safety', 'Safety Tips'),
        ('driver', 'Driver Stories'),
        ('travel', 'Ghana Travel'),
        ('product', 'Product Updates'),
    ]
    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, blank=True)
    excerpt = models.TextField(max_length=300)
    content = CKEditor5Field('Text', config_name='extends')
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='company')
    cover_image = models.ImageField(upload_to='blog/', blank=True, null=True)
    cover_image_url = models.URLField(max_length=500, blank=True, null=True, help_text="Alternative to cover_image for external URLs")
    author_name = models.CharField(max_length=100)
    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title


class ContactInquiry(models.Model):
    CATEGORY = [
        ('general', 'General'),
        ('driver', 'Become a Driver'),
        ('support', 'Customer Support'),
        ('press', 'Press & Media'),
        ('partnership', 'Partnership'),
    ]
    name = models.CharField(max_length=255)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    category = models.CharField(max_length=20, choices=CATEGORY, default='general')
    message = models.TextField()
    is_resolved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = 'Contact Inquiries'

    def __str__(self):
        return f"{self.name} - {self.category}"


class City(models.Model):
    name = models.CharField(max_length=100)
    region = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    launch_date = models.DateField(blank=True, null=True)
    cover_image = models.ImageField(upload_to='cities/', blank=True, null=True)
    cover_image_url = models.URLField(max_length=500, blank=True, null=True, help_text="Alternative to cover_image for external URLs")
    driver_count = models.IntegerField(default=0)
    latitude = models.FloatField(null=True, blank=True, help_text="For map pulsars")
    longitude = models.FloatField(null=True, blank=True, help_text="For map pulsars")
    
    class Meta:
        verbose_name_plural = 'Cities'

    def __str__(self):
        return f"{self.name}, {self.region}"


class Testimonial(models.Model):
    name = models.CharField(max_length=100)
    role = models.CharField(max_length=50, help_text="e.g. Rider, Driver, Partner")
    quote = models.TextField()
    photo_url = models.URLField(max_length=500, blank=True, null=True)
    rating = models.IntegerField(default=5)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.role})"


class FAQItem(models.Model):
    CATEGORY_CHOICES = [
        ('riders', 'For Riders'),
        ('drivers', 'For Drivers'),
        ('payments', 'Payments'),
        ('safety', 'Safety'),
        ('general', 'General'),
    ]
    question = models.CharField(max_length=300)
    answer = models.TextField()
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='general')
    order = models.IntegerField(default=0, help_text='Lower number = shown first')
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['order', 'id']
        verbose_name = 'FAQ Item'
        verbose_name_plural = 'FAQ Items'

    def __str__(self):
        return self.question


class JobOpening(models.Model):
    DEPARTMENT_CHOICES = [
        ('engineering', 'Engineering'),
        ('operations', 'Operations'),
        ('marketing', 'Marketing'),
        ('support', 'Customer Support'),
        ('finance', 'Finance'),
        ('design', 'Design'),
    ]
    TYPE_CHOICES = [
        ('full_time', 'Full-Time'),
        ('part_time', 'Part-Time'),
        ('contract', 'Contract'),
        ('internship', 'Internship'),
    ]
    title = models.CharField(max_length=200)
    department = models.CharField(max_length=20, choices=DEPARTMENT_CHOICES)
    location = models.CharField(max_length=100, default='Accra, Ghana')
    job_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='full_time')
    description = models.TextField()
    requirements = models.TextField(blank=True)
    apply_url = models.URLField(blank=True, help_text='External application link (optional)')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Job Opening'
        verbose_name_plural = 'Job Openings'

    def __str__(self):
        return f"{self.title} ({self.department})"
