from datetime import timedelta

from django.conf import settings
from django.core.cache import cache
from django.db.models import Q
from django.utils import timezone
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from accounts.models import CustomUser, TrialRequest, Subject
from .models import Review, MaterialCategory, MaterialItem


def _get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '').strip()


def _clean_tracking_value(value, max_length=255):
    return (value or '').strip().replace('\r', ' ').replace('\n', ' ')[:max_length]


def _analytics_context():
    return {
        'ga4_id': settings.GA4_MEASUREMENT_ID,
        'yandex_id': settings.YANDEX_METRIKA_COUNTER_ID,
        'meta_pixel_id': settings.META_PIXEL_ID,
    }


def _split_lines(text):
    return [line.strip() for line in (text or '').splitlines() if line.strip()]


def _split_delimited_lines(text, parts_count):
    rows = []
    for line in _split_lines(text):
        parts = [part.strip() for part in line.split('|', parts_count - 1)]
        if len(parts) != parts_count:
            continue
        if not all(parts):
            continue
        rows.append(parts)
    return rows


def home(request):
    teachers = CustomUser.objects.filter(role='teacher', is_approved=True).prefetch_related('subjects_taught', 'desired_subject')
    subjects = Subject.objects.all()
    reviews = Review.objects.filter(is_published=True).order_by('-created_at')[:12]
    return render(request, 'main/index.html', {
        'teachers': teachers,
        'subjects': subjects,
        'reviews': reviews,
        'analytics': _analytics_context(),
    })


def teachers_list(request):
    teachers = CustomUser.objects.filter(role='teacher', is_approved=True)
    return render(request, 'main/teachers_list.html', {'teachers': teachers})


def materials_list(request):
    categories = MaterialCategory.objects.filter(is_active=True).order_by('sort_order', 'title')
    latest_items = MaterialItem.objects.filter(is_published=True).select_related('category', 'subject')[:12]
    subjects = Subject.objects.all()
    return render(request, 'main/materials_list.html', {'categories': categories, 'latest_items': latest_items, 'subjects': subjects})


def materials_category(request, slug):
    category = get_object_or_404(MaterialCategory, slug=slug, is_active=True)
    items = MaterialItem.objects.filter(category=category, is_published=True).select_related('subject').order_by('-created_at')
    subjects = Subject.objects.all()

    subject_id = request.GET.get('subject')
    grade = request.GET.get('grade')

    if subject_id and subject_id.isdigit():
        items = items.filter(subject_id=int(subject_id))
    if grade and grade.isdigit():
        items = items.filter(grade=int(grade))

    return render(request, 'main/materials_category.html', {
        'category': category,
        'items': items,
        'subjects': subjects,
        'selected_subject': subject_id or '',
        'selected_grade': grade or '',
        'grade_options': [4, 5, 6, 7, 8],
    })


def subject_detail(request, slug):
    subject = get_object_or_404(Subject, slug=slug)
    teachers = (
        CustomUser.objects
        .filter(role='teacher', is_approved=True)
        .filter(Q(subjects_taught=subject) | Q(desired_subject=subject))
        .distinct()[:6]
    )

    metrics_rows = _split_delimited_lines(subject.metrics, 2)
    if not metrics_rows:
        metrics_rows = [
            ['Формат', 'Индивидуально 1:1'],
            ['Возраст', 'Дети и подростки'],
            ['Контроль прогресса', 'После каждого урока'],
            ['Старт', 'С пробного урока'],
        ]
    metrics = [{'label': row[0], 'value': row[1]} for row in metrics_rows[:4]]

    results_title = subject.results_title or 'Почему этот курс дает результат'
    result_points_rows = _split_delimited_lines(subject.result_points, 2)
    if not result_points_rows:
        result_points_rows = [
            ['Диагностика на старте', 'Понимаем текущий уровень и сразу строим персональный план.'],
            ['Стабильная практика', 'Ученик тренируется на заданиях нужного формата без перегруза.'],
        ]
    result_points = [{'title': row[0], 'description': row[1]} for row in result_points_rows[:4]]

    include_items_title = subject.include_items_title or 'Что входит в обучение'
    include_items = _split_lines(subject.include_items)
    if not include_items:
        include_items = [
            'Индивидуальные занятия 1 на 1',
            'Домашние задания с разбором ошибок',
            'Обратная связь для родителя',
            'Гибкий график и перенос уроков',
        ]

    benefits = _split_lines(subject.benefits)
    if not benefits:
        benefits = [
            'Понимание ключевых тем и уверенность на уроках в школе.',
            'Индивидуальный план подготовки под уровень ученика.',
            'Регулярная обратная связь для родителей по прогрессу.',
            'Домашние задания с разбором ошибок и поддержкой преподавателя.',
        ]

    program = _split_lines(subject.program)
    if not program:
        program = [
            'Диагностика уровня и постановка учебной цели.',
            'База и закрытие пробелов по теме.',
            'Интенсивная практика на заданиях формата экзаменов.',
            'Итоговый контроль и план на следующий этап.',
        ]

    progress_title = subject.progress_title or 'Что меняется уже в первые 2-4 недели'
    progress_subtitle = subject.progress_subtitle or 'Фокус на понятность, скорость решения и уверенность ученика на школьных уроках.'
    progress_cards_rows = _split_delimited_lines(subject.progress_cards, 3)
    if not progress_cards_rows:
        progress_cards_rows = [
            ['Понимание тем', '+ глубокое', 'Ученик перестает учить "по шаблону" и начинает понимать логику.'],
            ['Домашние задания', 'быстрее', 'Уходит зависание на задачах, появляется уверенный темп решения.'],
            ['Оценки и контроль', 'стабильнее', 'Результат становится предсказуемым за счет системной работы.'],
        ]
    progress_cards = [
        {'title': row[0], 'highlight': row[1], 'description': row[2]}
        for row in progress_cards_rows[:3]
    ]

    hero_title = subject.hero_title or f'{subject.name} онлайн с опытным преподавателем'
    hero_subtitle = subject.hero_subtitle or 'Индивидуальные занятия, понятные объяснения и стабильный прогресс с первых недель обучения.'
    page_title = subject.seo_title or f'{subject.name} онлайн для школьников | SmartUrok'
    page_description = subject.seo_description or f'Индивидуальные онлайн-занятия по предмету «{subject.name}». Подберем преподавателя и начнем с бесплатного пробного урока.'

    return render(request, 'main/subject_detail.html', {
        'subject': subject,
        'teachers': teachers,
        'metrics': metrics,
        'results_title': results_title,
        'result_points': result_points,
        'include_items_title': include_items_title,
        'include_items': include_items,
        'benefits': benefits,
        'program': program,
        'progress_title': progress_title,
        'progress_subtitle': progress_subtitle,
        'progress_cards': progress_cards,
        'hero_title': hero_title,
        'hero_subtitle': hero_subtitle,
        'page_title': page_title,
        'page_description': page_description,
        'analytics': _analytics_context(),
    })


def privacy_policy(request):
    return render(request, 'main/privacy_policy.html')


def public_offer(request):
    return render(request, 'main/public_offer.html')


def home_lead(request):
    if request.method != 'POST':
        return redirect('home')

    # Honeypot: bots often fill hidden fields.
    if (request.POST.get('website') or '').strip():
        return redirect('home')

    def _parse_positive_int(value):
        cleaned = (value or '').strip().replace(' ', '').replace(',', '')
        if not cleaned.isdigit():
            return None
        return int(cleaned)

    name = (request.POST.get('name') or '').strip()
    email = (request.POST.get('email') or '').strip()
    phone = (request.POST.get('phone') or '').strip()
    preferred_time = (request.POST.get('preferred_time') or '').strip()
    message = (request.POST.get('message') or '').strip()
    subject_id = (request.POST.get('subject') or '').strip()
    promo_interest = _clean_tracking_value(request.POST.get('promo_interest'), max_length=120)
    pricing_subject_id = (request.POST.get('pricing_subject_id') or '').strip()
    pricing_subject_name = _clean_tracking_value(request.POST.get('pricing_subject_name'), max_length=120)
    pricing_lessons_count = _parse_positive_int(request.POST.get('pricing_lessons_count'))
    pricing_discount_percent = _parse_positive_int(request.POST.get('pricing_discount_percent'))
    pricing_total_price = _parse_positive_int(request.POST.get('pricing_total_price'))
    pricing_old_price = _parse_positive_int(request.POST.get('pricing_old_price'))
    consent_given = request.POST.get('privacy_consent') == '1'
    lead_form = _clean_tracking_value(request.POST.get('lead_form'), max_length=64)
    attribution_map = [
        ('Форма', lead_form),
        ('UTM source', _clean_tracking_value(request.POST.get('utm_source'))),
        ('UTM medium', _clean_tracking_value(request.POST.get('utm_medium'))),
        ('UTM campaign', _clean_tracking_value(request.POST.get('utm_campaign'))),
        ('UTM content', _clean_tracking_value(request.POST.get('utm_content'))),
        ('UTM term', _clean_tracking_value(request.POST.get('utm_term'))),
        ('GCLID', _clean_tracking_value(request.POST.get('gclid'))),
        ('FBCLID', _clean_tracking_value(request.POST.get('fbclid'))),
        ('YCLID', _clean_tracking_value(request.POST.get('yclid'))),
        ('Landing', _clean_tracking_value(request.POST.get('landing_path'), max_length=500)),
        ('Referrer', _clean_tracking_value(request.POST.get('referrer'), max_length=500)),
    ]

    client_ip = _get_client_ip(request) or 'unknown'
    user_agent = (request.META.get('HTTP_USER_AGENT') or '')[:255]

    # Promo modal should keep only explicit interest from popup chips.
    # Calculator pricing context is ignored here to avoid ambiguous leads.
    if lead_form == 'promo_modal':
        subject_id = ''
        pricing_subject_name = ''
        pricing_lessons_count = None
        pricing_discount_percent = None
        pricing_total_price = None
        pricing_old_price = None
    else:
        promo_interest = ''
        if not subject_id and pricing_subject_id.isdigit():
            subject_id = pricing_subject_id

    subject = None
    if subject_id.isdigit():
        subject = Subject.objects.filter(id=int(subject_id)).first()

    if not name or not email or not phone:
        messages.error(request, 'Пожалуйста, заполните имя, email и телефон.')
        return redirect('home')

    if not consent_given:
        messages.error(request, 'Нужно подтвердить согласие на обработку персональных данных.')
        return redirect('home')

    # Basic per-IP throttling to reduce spam.
    throttle_key = f'home_lead:ip:{client_ip}'
    attempts = cache.get(throttle_key, 0)
    if attempts >= 5:
        messages.error(request, 'Слишком много запросов. Попробуйте чуть позже.')
        return redirect('home')
    cache.set(throttle_key, attempts + 1, timeout=10 * 60)

    # Short dedupe window for accidental repeated submits.
    duplicate_from = timezone.now() - timedelta(minutes=3)
    if TrialRequest.objects.filter(
        email__iexact=email,
        phone=phone,
        created_at__gte=duplicate_from,
    ).exists():
        messages.info(request, 'Заявка уже отправлена. Мы скоро свяжемся с вами.')
        return redirect('home')

    attribution_lines = [f'{label}: {value}' for label, value in attribution_map if value]
    if attribution_lines:
        attribution_block = 'Маркетинг-атрибуция:\n' + '\n'.join(attribution_lines)
        message = f'{message}\n\n{attribution_block}' if message else attribution_block

    TrialRequest.objects.create(
        name=name,
        email=email,
        phone=phone,
        subject=subject,
        preferred_time=preferred_time,
        message=message,
        lead_form=lead_form,
        promo_interest=promo_interest,
        pricing_subject_name=pricing_subject_name,
        pricing_lessons_count=pricing_lessons_count,
        pricing_discount_percent=pricing_discount_percent,
        pricing_total_price=pricing_total_price,
        pricing_old_price=pricing_old_price,
        personal_data_consent=True,
        consent_at=timezone.now(),
        consent_ip=client_ip if client_ip != 'unknown' else None,
        consent_user_agent=user_agent,
    )
    messages.success(request, 'Заявка отправлена! Мы свяжемся с вами в ближайшее время.')
    return redirect('home')


def submit_review(request):
    if request.method != 'POST':
        return redirect('home')

    name = (request.POST.get('name') or '').strip()
    text = (request.POST.get('text') or '').strip()
    rating = request.POST.get('rating') or '5'

    try:
        rating_val = int(rating)
    except ValueError:
        rating_val = 5
    rating_val = max(1, min(5, rating_val))

    if not name or not text:
        messages.error(request, 'Пожалуйста, заполните имя и отзыв.')
        return redirect('home')

    Review.objects.create(
        name=name,
        text=text,
        rating=rating_val,
        is_published=False
    )
    messages.success(request, 'Спасибо! Отзыв отправлен и появится после модерации.')
    return redirect('home')
