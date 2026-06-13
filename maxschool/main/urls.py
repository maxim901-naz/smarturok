from django.urls import path
from .views import (
    home,
    teachers_list,
    learning_direction,
    subject_detail,
    home_lead,
    submit_review,
    materials_list,
    materials_hub,
    materials_category,
    material_detail,
    privacy_policy,
    public_offer,
)
# from django.conf.urls.static import static
# from django.conf import settings
urlpatterns = [
    path('', home, name='home'),
     path('oge/', learning_direction, {'slug': 'oge'}, name='oge_landing'),
     path('ege/', learning_direction, {'slug': 'ege'}, name='ege_landing'),
     path('english/', learning_direction, {'slug': 'english'}, name='english_landing'),
     path('school-subjects/', learning_direction, {'slug': 'school-subjects'}, name='school_subjects_landing'),
     path('vpr/', learning_direction, {'slug': 'vpr'}, name='vpr_landing'),
     path('teachers/', teachers_list, name='teachers_list'),
     path('lead/', home_lead, name='home_lead'),
     path('reviews/submit/', submit_review, name='submit_review'),
     path('materials/', materials_list, name='materials_list'),
     path('materials/item/<str:slug>/', material_detail, name='material_detail'),
     path('materials/<slug:hub_slug>/<str:subject_slug>/', materials_hub, name='materials_hub'),
     path('materials/<slug:slug>/', materials_category, name='materials_category'),
     path('subjects/<str:slug>/', subject_detail, name='subject_detail'),
     path('privacy/', privacy_policy, name='privacy_policy'),
     path('offer/', public_offer, name='public_offer'),
]
# if settings.DEBUG:
#     urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
