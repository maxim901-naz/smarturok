from django.db.models import Q
from django.urls import reverse

from .models import MaterialItem


MATERIAL_HUBS = {
    'oge': {
        'label': 'ОГЭ',
        'eyebrow': 'Экзаменационная база',
        'exam_types': ('oge',),
        'direction_slug': 'oge',
        'trial_interest': 'oge',
        'title_template': 'ОГЭ по предмету «{subject}»: теория, разборы и тесты',
        'meta_template': 'Материалы для подготовки к ОГЭ по предмету «{subject}»: разборы заданий, теория, тесты и практика SmartUrok.',
        'hero_text_template': 'Собрали материалы по ОГЭ: короткая теория, алгоритмы решения, тренировка заданий и тесты для проверки результата.',
        'primary_cta': 'Записаться на пробный ОГЭ',
        'empty_note': 'Когда появятся новые разборы ОГЭ по этому предмету, они автоматически попадут сюда.',
    },
    'ege': {
        'label': 'ЕГЭ',
        'eyebrow': 'Подготовка на баллы',
        'exam_types': ('ege',),
        'direction_slug': 'ege',
        'trial_interest': 'ege',
        'title_template': 'ЕГЭ по предмету «{subject}»: теория, задания и практика',
        'meta_template': 'Материалы для подготовки к ЕГЭ по предмету «{subject}»: теория, разборы заданий, тесты и практика SmartUrok.',
        'hero_text_template': 'Страница помогает двигаться системно: от базовой теории к разбору заданий, тренировке и пробникам.',
        'primary_cta': 'Записаться на пробный ЕГЭ',
        'empty_note': 'Когда появятся новые материалы ЕГЭ по этому предмету, они автоматически попадут сюда.',
    },
    'vpr': {
        'label': 'ВПР и контрольные',
        'eyebrow': 'Школьные проверки',
        'exam_types': (),
        'direction_slug': 'vpr',
        'trial_interest': 'vpr',
        'title_template': 'ВПР и контрольные по предмету «{subject}»: подготовка и практика',
        'meta_template': 'Материалы для подготовки к ВПР и контрольным по предмету «{subject}»: повторение тем, практика и разбор ошибок.',
        'hero_text_template': 'Подборка для спокойной подготовки к проверочным работам: повторяем темы, тренируем формат и разбираем типичные ошибки.',
        'primary_cta': 'Подготовиться к ВПР',
        'empty_note': 'Когда появятся материалы по ВПР или контрольным, они автоматически попадут сюда.',
    },
    'school': {
        'label': 'Школьная программа',
        'eyebrow': 'Теория и практика',
        'exam_types': ('general', 'school'),
        'direction_slug': 'school-subjects',
        'trial_interest': 'school_subjects',
        'title_template': '{subject}: материалы, правила, примеры и тесты',
        'meta_template': 'Учебные материалы по предмету «{subject}»: понятная теория, примеры, тесты и задания для школьников.',
        'hero_text_template': 'База знаний по предмету: правила простым языком, примеры решения, тренировка и тесты для закрепления.',
        'primary_cta': 'Подобрать преподавателя',
        'empty_note': 'Когда появятся новые школьные материалы по этому предмету, они автоматически попадут сюда.',
    },
}
MATERIAL_HUB_SITEMAP_MIN_ITEMS = 2


def vpr_material_query():
    return (
        Q(title__icontains='ВПР')
        | Q(title__icontains='МЦКО')
        | Q(title__icontains='контрольн')
        | Q(description__icontains='ВПР')
        | Q(description__icontains='МЦКО')
        | Q(category__title__icontains='ВПР')
        | Q(category__title__icontains='МЦКО')
        | Q(category__title__icontains='контрольн')
        | Q(category__slug__icontains='vpr')
        | Q(category__slug__icontains='mcko')
        | Q(category__slug__icontains='control')
    )


def published_materials_queryset():
    return (
        MaterialItem.objects
        .filter(status='published')
        .select_related('category', 'subject', 'related_theory', 'related_test')
    )


def material_hub_queryset(hub_slug, subject):
    hub = MATERIAL_HUBS.get(hub_slug)
    if not hub or not subject:
        return MaterialItem.objects.none()

    queryset = (
        published_materials_queryset()
        .filter(access_level='public', subject=subject)
        .exclude(slug__isnull=True)
        .exclude(slug='')
    )

    if hub_slug == 'vpr':
        return queryset.filter(vpr_material_query())
    if hub_slug == 'school':
        return queryset.filter(exam_type__in=hub['exam_types']).exclude(vpr_material_query())

    return queryset.filter(exam_type__in=hub['exam_types'])


def material_hub_url(hub_slug, subject):
    if not subject or not subject.slug:
        return ''
    return reverse('materials_hub', kwargs={'hub_slug': hub_slug, 'subject_slug': subject.slug})
