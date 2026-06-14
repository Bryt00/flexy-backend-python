"""
API Response Caching utilities for DRF views.

Usage in a ViewSet action:
    from core_auth.cache_utils import cached_api_response, invalidate_user_cache

    @action(detail=False, methods=['get'])
    def me(self, request):
        return cached_api_response(
            request, 'profile', timeout=300,
            fetcher=lambda: super_logic_here()
        )

    # On mutation (POST/PUT/PATCH):
    invalidate_user_cache(request.user.id, 'profile')
"""

import logging
from functools import wraps
from django.core.cache import cache
from rest_framework.response import Response

logger = logging.getLogger(__name__)


def make_cache_key(user_id, prefix, query_string=''):
    """Generate a per-user cache key."""
    if user_id:
        key = f"api:{prefix}:{user_id}"
    else:
        key = f"api:{prefix}:anon"
    if query_string:
        key += f":{query_string}"
    return key


def cached_api_response(request, prefix, timeout, fetcher, per_user=True, global_cache=False):
    """
    Check cache first. On miss, call fetcher() which must return a Response.
    Cache the response data and return with Cache-Control headers.
    
    Args:
        request: DRF request object
        prefix: Cache key prefix (e.g. 'profile', 'wallet')
        timeout: Cache TTL in seconds
        fetcher: Callable that returns a DRF Response
        per_user: If True, cache is scoped per user. If False, shared across users.
        global_cache: If True, same cache for all users (e.g. site settings, plans)
    """
    user_id = request.user.id if per_user and hasattr(request, 'user') and request.user.is_authenticated else None
    
    if global_cache:
        user_id = None
    
    query_string = request.META.get('QUERY_STRING', '')
    cache_key = make_cache_key(user_id, prefix, query_string)
    
    # Try cache first
    cached_data = cache.get(cache_key)
    if cached_data is not None:
        logger.debug(f"[CACHE HIT] {cache_key}")
        response = Response(cached_data)
        response['Cache-Control'] = f'private, max-age={timeout}'
        response['X-Cache'] = 'HIT'
        return response
    
    # Cache miss — call the fetcher
    logger.debug(f"[CACHE MISS] {cache_key}")
    response = fetcher()
    
    # Only cache successful responses
    if response.status_code == 200:
        cache.set(cache_key, response.data, timeout)
    
    response['Cache-Control'] = f'private, max-age={timeout}'
    response['X-Cache'] = 'MISS'
    return response


def invalidate_user_cache(user_id, prefix):
    """Invalidate a specific cached response for a user."""
    cache_key = make_cache_key(user_id, prefix)
    cache.delete(cache_key)
    logger.debug(f"[CACHE INVALIDATED] {cache_key}")


def invalidate_global_cache(prefix):
    """Invalidate a global (non-per-user) cached response."""
    cache_key = make_cache_key(None, prefix)
    cache.delete(cache_key)
    logger.debug(f"[CACHE INVALIDATED] {cache_key}")
