from django import forms
from .models import AdBooking
import datetime

class AdStep1Form(forms.ModelForm):
    class Meta:
        model = AdBooking
        fields = ['business_name', 'contact_email', 'contact_phone']

class AdStep2Form(forms.ModelForm):
    class Meta:
        model = AdBooking
        fields = ['headline', 'body_text', 'image', 'target_url']
        widgets = {
            'body_text': forms.Textarea(attrs={'rows': 4}),
        }

class AdStep3Form(forms.ModelForm):
    # This is a bit tricky since we will use a custom week picker in JS, 
    # but we store the week_start_date. It will be hidden or populated via JS.
    week_start_date = forms.DateField(widget=forms.HiddenInput())
    
    class Meta:
        model = AdBooking
        fields = ['week_start_date']

    def clean_week_start_date(self):
        date = self.cleaned_data['week_start_date']
        if date.weekday() != 0:
            raise forms.ValidationError("Start date must be a Monday.")
            
        # Check slot availability
        available_slots = AdBooking.slots_available_for_week(date)
        if available_slots <= 0:
            raise forms.ValidationError(f"The week of {date.strftime('%B %d, %Y')} is fully booked.")
            
        return date
