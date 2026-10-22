from django.conf import settings
from django.urls import reverse


def google_oauth(request):
    return {
        'google_oauth_enabled': settings.GOOGLE_OAUTH_ENABLED,
        'google_oauth_callback_url': request.build_absolute_uri(reverse('google_callback')),
    }