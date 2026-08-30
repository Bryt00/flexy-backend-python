"""
drf-spectacular postprocessing hooks for automatic endpoint tagging.

Maps URL path prefixes to human-readable Swagger tag groups so every
endpoint is categorised without needing per-view @extend_schema(tags=...).
Explicit tags set via @extend_schema always take priority.
"""

# Mapping of URL path prefixes to tag names.
# Order matters — first match wins.
PREFIX_TAG_MAP = [
    ('/v1/auth/', 'Authentication'),
    ('/v1/profile/', 'Profiles'),
    ('/v1/rides/', 'Rides'),
    ('/v1/deliveries/', 'Deliveries'),
    ('/v1/vehicles/', 'Vehicles'),
    ('/v1/payments/', 'Payments'),
    ('/v1/subscriptions/', 'Subscriptions'),
    ('/v1/admin/subscriptions/', 'Subscriptions'),
    ('/v1/notifications/', 'Notifications'),
    ('/v1/marketing/', 'Marketing'),
    ('/v1/files/', 'Files'),
    ('/v1/ads/', 'Advertising'),
    ('/api/advertising/', 'Advertising'),
    ('/v1/integrations/', 'Integrations'),
    ('/v1/settings/', 'Settings'),
    ('/v1/website/', 'Settings'),
    ('/api/auth/', 'Authentication'),
    ('/campaigns/', 'Marketing'),
]


def postprocess_auto_tag(result, generator, **kwargs):
    """
    Postprocessing hook that replaces the default generic 'v1' tag
    with a domain-specific tag based on the endpoint's URL path.

    Endpoints that already have explicitly set tags (via @extend_schema)
    are left untouched — this only replaces the auto-generated 'v1' tags.
    """
    for path, methods in result.get('paths', {}).items():
        for method, operation in methods.items():
            if not isinstance(operation, dict):
                continue

            tags = operation.get('tags', [])

            # Only replace auto-generated tags (typically 'v1', 'api', etc.)
            auto_tags = {'v1', 'api', 'campaigns'}
            if tags and not auto_tags.issuperset(set(tags)):
                # Explicit tags were set by @extend_schema — keep them
                continue

            # Find matching tag by URL prefix
            for prefix, tag_name in PREFIX_TAG_MAP:
                if path.startswith(prefix):
                    operation['tags'] = [tag_name]
                    break
            else:
                # Fallback for unmatched paths
                operation['tags'] = ['System']

    return result
