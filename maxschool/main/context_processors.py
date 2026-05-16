from django.conf import settings


def analytics_ids(request):
    return {
        "analytics": {
            "ga4_id": settings.GA4_MEASUREMENT_ID,
            "yandex_id": settings.YANDEX_METRIKA_COUNTER_ID,
            "meta_pixel_id": settings.META_PIXEL_ID,
        }
    }
