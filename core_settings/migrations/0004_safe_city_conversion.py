from django.db import migrations, models
import django.db.models.deletion

def migrate_city_names_to_objects(apps, schema_editor):
    PricingRule = apps.get_model('core_settings', 'PricingRule')
    City = apps.get_model('website', 'City')
    
    for rule in PricingRule.objects.all():
        city_name = rule.city_temp
        if city_name:
            # Try to find a matching city, or create one if it doesn't exist
            city_obj, _ = City.objects.get_or_create(
                name=city_name,
                defaults={'is_active': True}
            )
            rule.city = city_obj
            rule.save()

class Migration(migrations.Migration):

    dependencies = [
        ('core_settings', '0003_vehiclecategory_image'),
        ('website', '0001_initial'), # Ensure City model exists
    ]

    operations = [
        # 1. Rename existing 'city' char field to 'city_temp'
        migrations.RenameField(
            model_name='pricingrule',
            old_name='city',
            new_name='city_temp',
        ),
        # 2. Add the new ForeignKey 'city' (nullable for now)
        migrations.AddField(
            model_name='pricingrule',
            name='city',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE, 
                related_name='pricing_rules', 
                to='website.city', 
                null=True, 
                blank=True
            ),
        ),
        # 3. Data Migration: Map strings to City objects
        migrations.RunPython(migrate_city_names_to_objects),
        # 4. Remove the temp field
        migrations.RemoveField(
            model_name='pricingrule',
            name='city_temp',
        ),
    ]
