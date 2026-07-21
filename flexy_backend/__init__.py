from .celery import app as celery_app

__all__ = ('celery_app',)

# Patch BaseDatabaseOperations when GIS is disabled to prevent migrations from crashing on old PointFields
try:
    from django.db.backends.base.operations import BaseDatabaseOperations
    if not hasattr(BaseDatabaseOperations, 'geo_db_type'):
        BaseDatabaseOperations.geo_db_type = lambda self, field: 'geometry'
except Exception:
    pass
