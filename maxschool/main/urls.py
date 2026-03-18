from django.urls import path
from .views import (
    home,
    teachers_list,
    subject_detail,
    home_lead,
    submit_review,
    materials_list,
    materials_category,
    privacy_policy,
    public_offer,
)
# from django.conf.urls.static import static
# from django.conf import settings
urlpatterns = [
    path('', home, name='home'),
     path('teachers/', teachers_list, name='teachers_list'),
     path('lead/', home_lead, name='home_lead'),
     path('reviews/submit/', submit_review, name='submit_review'),
     path('materials/', materials_list, name='materials_list'),
     path('materials/<slug:slug>/', materials_category, name='materials_category'),
     path('subjects/<str:slug>/', subject_detail, name='subject_detail'),
     path('privacy/', privacy_policy, name='privacy_policy'),
     path('offer/', public_offer, name='public_offer'),
]
# if settings.DEBUG:
#     urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
