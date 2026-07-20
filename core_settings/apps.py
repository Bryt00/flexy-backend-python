from django.apps import AppConfig


class CoreSettingsConfig(AppConfig):
    name = 'core_settings'
    verbose_name = 'Core Settings'

    def ready(self):
        import core_settings.signals
