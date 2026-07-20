import random

class PrimaryReplicaRouter:
    def db_for_read(self, model, **hints):
        """
        Routes read queries to a randomly selected standby database if standbys exist,
        otherwise falls back to the default primary database.
        """
        from django.conf import settings
        standbys = [key for key in settings.DATABASES.keys() if key.startswith('standby_')]
        if standbys:
            return random.choice(standbys)
        return 'default'

    def db_for_write(self, model, **hints):
        """
        Routes all write queries to the primary database ('default').
        """
        return 'default'

    def allow_relation(self, obj1, obj2, **hints):
        """
        Allows any relation since standby databases are replicas of the primary.
        """
        return True

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """
        Restricts migrations exclusively to the primary database ('default').
        """
        return db == 'default'
