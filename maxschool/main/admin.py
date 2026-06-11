from django.contrib import admin
from django.utils.html import format_html, format_html_join, strip_tags

from .models import (
    HomeSuccessStory,
    MaterialCategory,
    MaterialImage,
    MaterialItem,
    MaterialTest,
    MaterialTestAttempt,
    MaterialTestOption,
    MaterialTestQuestion,
    Review,
)


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('name', 'rating', 'is_published', 'created_at')
    list_filter = ('is_published', 'rating')
    search_fields = ('name', 'text')
    list_editable = ('is_published',)


@admin.register(HomeSuccessStory)
class HomeSuccessStoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'achievement', 'sort_order', 'is_published', 'created_at')
    list_filter = ('is_published',)
    search_fields = ('name', 'achievement', 'story_text')
    list_editable = ('sort_order', 'is_published')


@admin.register(MaterialCategory)
class MaterialCategoryAdmin(admin.ModelAdmin):
    list_display = ('title', 'slug', 'is_active', 'sort_order')
    list_editable = ('is_active', 'sort_order')
    prepopulated_fields = {'slug': ('title',)}
    search_fields = ('title',)


@admin.register(MaterialItem)
class MaterialItemAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        'slug',
        'category',
        'subject',
        'task_number',
        'content_type',
        'exam_type',
        'access_level',
        'status',
        'is_published',
        'views_count',
        'has_test_bank',
        'test_attempts_total',
        'updated_at',
    )
    list_filter = (
        'category',
        'subject',
        'grade',
        'content_type',
        'exam_type',
        'access_level',
        'status',
        'is_published',
    )
    search_fields = ('title', 'slug', 'description', 'seo_title', 'seo_focus_query', 'meta_description', 'article_markdown', 'faq_items')
    readonly_fields = (
        'is_published',
        'published_at',
        'views_count',
        'created_at',
        'updated_at',
        'seo_template_guide',
        'seo_preview',
        'seo_checklist',
        'content_template_guide',
        'image_workflow_note',
    )
    prepopulated_fields = {'slug': ('title',)}
    list_editable = ('status', 'access_level')
    raw_id_fields = ('related_theory', 'related_test')

    fieldsets = (
        ('Main', {
            'fields': (
                'title',
                'slug',
                'category',
                'subject',
                'grade',
                'task_number',
                'content_type',
                'exam_type',
            )
        }),
        ('SEO', {
            'fields': (
                'seo_title',
                'seo_focus_query',
                'meta_description',
                'description',
                'faq_items',
                'seo_template_guide',
                'seo_preview',
                'seo_checklist',
            )
        }),
        ('Content', {
            'fields': (
                'content_template_guide',
                'video_url',
                'article_markdown',
                'file',
                'external_url',
                'test_payload',
                'image_workflow_note',
            )
        }),
        ('Learning flow', {
            'fields': ('related_theory', 'related_test')
        }),
        ('Publishing and access', {
            'fields': ('status', 'access_level', 'is_published', 'published_at', 'views_count')
        }),
        ('Service', {
            'fields': ('created_at', 'updated_at')
        }),
    )

    def test_attempts_total(self, obj):
        return obj.test_attempts.count()

    def has_test_bank(self, obj):
        return MaterialTest.objects.filter(material=obj).exists()

    test_attempts_total.short_description = 'Test attempts'
    has_test_bank.short_description = 'Test bank'
    has_test_bank.boolean = True

    def _seo_title_value(self, obj):
        if not obj:
            return ''
        base_title = (obj.seo_title or obj.title or '').strip()
        if not base_title:
            return ''
        return base_title if 'smarturok' in base_title.lower() else f'{base_title} | SmartUrok'

    def _meta_description_value(self, obj):
        if not obj:
            return ''
        fallback = strip_tags(obj.description or '').strip()
        return (obj.meta_description or fallback or f'Материал SmartUrok: {obj.title}.').strip()[:160]

    def seo_preview(self, obj):
        if not obj:
            return 'Save the material to see SEO preview.'

        title = self._seo_title_value(obj)
        description = self._meta_description_value(obj)
        return format_html(
            '<div style="max-width: 720px; padding: 12px; border: 1px solid #e5e7eb; border-radius: 8px; background: #f8fafc;">'
            '<div style="font-size: 13px; color: #64748b; margin-bottom: 6px;">Search preview</div>'
            '<div style="font-size: 18px; color: #1a0dab; line-height: 1.25;">{}</div>'
            '<div style="font-size: 12px; color: #64748b; margin: 4px 0;">https://smarturok.ru/materials/item/{}/</div>'
            '<div style="font-size: 13px; color: #334155; line-height: 1.45;">{}</div>'
            '<div style="font-size: 12px; color: #64748b; margin-top: 8px;">Title: {} chars · Description: {} chars</div>'
            '</div>',
            title,
            obj.slug or '',
            description,
            len(title),
            len(description),
        )

    seo_preview.short_description = 'SEO preview'

    def seo_checklist(self, obj):
        if not obj:
            return 'Save the material to see SEO checklist.'

        title = self._seo_title_value(obj)
        description = self._meta_description_value(obj)
        has_content = bool(
            (obj.article_markdown or '').strip()
            or obj.file
            or obj.video_url
            or obj.external_url
            or obj.test_payload
            or MaterialTest.objects.filter(material=obj).exists()
        )
        faq_lines = [line for line in (obj.faq_items or '').splitlines() if '|' in line and line.strip()]
        checks = [
            ('URL/slug есть и не меняется после публикации', bool(obj.slug), 'Не меняйте slug у уже опубликованных материалов без необходимости.'),
            ('Материал публичный', obj.status == 'published' and obj.access_level == 'public', 'Для SEO нужны status=Опубликовано и access=Доступно всем.'),
            ('SEO title заполнен', bool((obj.seo_title or '').strip()), 'Лучше: тема + класс/экзамен + “правила/примеры/тест”.'),
            ('SEO title нормальной длины', 35 <= len(title) <= 75, 'Ориентир 35-75 символов вместе с SmartUrok.'),
            ('Meta description заполнен', bool((obj.meta_description or '').strip()), 'Кратко: что разберем, для кого, что получит ученик.'),
            ('Meta description нормальной длины', 100 <= len(description) <= 160, 'Ориентир 100-160 символов.'),
            ('Есть предмет и раздел', bool(obj.category_id and obj.subject_id), 'Помогает фильтрам, перелинковке и смыслу страницы.'),
            ('Есть класс или номер задания', bool(obj.grade or obj.task_number), 'Особенно полезно для запросов “6 класс”, “задание 1 ОГЭ”.'),
            ('Есть основной контент', has_content, 'Статья/тест/видео/PDF должны быть заполнены.'),
            ('Есть FAQ', len(faq_lines) >= 3, 'Добавьте 3-6 вопросов: вопрос | ответ.'),
            ('Есть связанный следующий шаг', bool(obj.related_test_id or obj.related_theory_id), 'Идеально: статья -> тест, тест -> теория.'),
        ]

        rows = format_html_join(
            '',
            '<li style="margin: 4px 0;"><span style="font-weight: 700; color: {};">{}</span> <strong>{}</strong><br><span style="color: #64748b;">{}</span></li>',
            (
                ('#15803d' if passed else '#b45309', 'OK' if passed else 'TODO', label, hint)
                for label, passed, hint in checks
            )
        )
        return format_html('<ul style="margin: 0; padding-left: 18px;">{}</ul>', rows)

    seo_checklist.short_description = 'SEO checklist'

    def _template_context(self, obj):
        subject = obj.subject.name if obj and obj.subject_id else '[предмет]'
        grade = f'{obj.grade} класс' if obj and obj.grade else '[класс]'
        task_number = obj.task_number if obj and obj.task_number else '[номер задания]'
        title = (obj.title or '').strip() if obj else ''
        topic = title or '[тема]'
        return {
            'topic': topic,
            'subject': subject,
            'grade': grade,
            'task_number': task_number,
        }

    def _template_card(self, title, body, subtitle=''):
        return format_html(
            '<details style="margin: 10px 0; border: 1px solid #e5e7eb; border-radius: 10px; background: #ffffff;">'
            '<summary style="cursor: pointer; padding: 10px 12px; font-weight: 700; color: #0f172a;">{}'
            '{}'
            '</summary>'
            '<pre style="white-space: pre-wrap; margin: 0; padding: 12px; background: #f8fafc; border-top: 1px solid #e5e7eb; color: #334155; font-size: 12px; line-height: 1.55;">{}</pre>'
            '</details>',
            title,
            format_html('<span style="display: block; margin-top: 3px; color: #64748b; font-weight: 400; font-size: 12px;">{}</span>', subtitle) if subtitle else '',
            body,
        )

    def seo_template_guide(self, obj):
        ctx = self._template_context(obj)
        blocks = [
            self._template_card(
                'Школьная тема',
                (
                    f"SEO title:\n{ctx['topic']}: правила, примеры и задания | {ctx['grade']}\n\n"
                    f"SEO focus query:\n{ctx['topic'].lower()} {ctx['grade']} правила примеры\n\n"
                    f"Meta description:\nРазберите тему «{ctx['topic']}»: простые правила, пошаговые примеры, типичные ошибки и задания для тренировки. Подходит для {ctx['grade']}."
                ),
                'Для запросов вроде “отрицательные числа 6 класс”, “проценты правила примеры”.',
            ),
            self._template_card(
                'ОГЭ',
                (
                    f"SEO title:\nЗадание {ctx['task_number']} ОГЭ по {ctx['subject']}: разбор, алгоритм и практика\n\n"
                    f"SEO focus query:\nзадание {ctx['task_number']} огэ {ctx['subject'].lower()} разбор практика\n\n"
                    f"Meta description:\nРазбор задания {ctx['task_number']} ОГЭ по предмету «{ctx['subject']}»: алгоритм решения, примеры, типичные ошибки и тренировочные задания с ответами."
                ),
                'Для экзаменационных материалов ОГЭ.',
            ),
            self._template_card(
                'ЕГЭ',
                (
                    f"SEO title:\nЗадание {ctx['task_number']} ЕГЭ по {ctx['subject']}: теория, разбор и практика\n\n"
                    f"SEO focus query:\nзадание {ctx['task_number']} егэ {ctx['subject'].lower()} теория разбор\n\n"
                    f"Meta description:\nПодготовка к заданию {ctx['task_number']} ЕГЭ по предмету «{ctx['subject']}»: краткая теория, пошаговый разбор, ловушки и практика для закрепления."
                ),
                'Для экзаменационных материалов ЕГЭ.',
            ),
            self._template_card(
                'Английский',
                (
                    f"SEO title:\n{ctx['topic']}: правило, примеры и упражнения по английскому\n\n"
                    f"SEO focus query:\n{ctx['topic'].lower()} английский правило примеры упражнения\n\n"
                    f"Meta description:\nПонятное объяснение темы «{ctx['topic']}» по английскому: правило, примеры предложений, частые ошибки и упражнения для самостоятельной практики."
                ),
                'Для грамматики, словаря и школьного английского.',
            ),
        ]
        return format_html(
            '<div style="max-width: 860px;">'
            '<div style="padding: 12px; border: 1px solid #fed7aa; border-radius: 10px; background: #fff7ed; color: #7c2d12;">'
            '<strong>Как пользоваться:</strong> выберите подходящий шаблон, скопируйте SEO title, focus query и meta description, затем адаптируйте под конкретную статью.'
            '</div>{}</div>',
            format_html_join('', '{}', ((block,) for block in blocks)),
        )

    seo_template_guide.short_description = 'SEO templates'

    def content_template_guide(self, obj):
        ctx = self._template_context(obj)
        school_article = (
            f"> Коротко: в этой статье разберем тему «{ctx['topic']}», покажем правила, примеры и задания для самостоятельной тренировки.\n\n"
            "## Что вы узнаете\n"
            f"- что означает тема «{ctx['topic']}»;\n"
            "- какие правила нужно запомнить;\n"
            "- как решать типовые задания;\n"
            "- какие ошибки чаще всего допускают ученики.\n\n"
            "## Краткое правило\n"
            "Напишите правило простыми словами, без перегруза терминами.\n\n"
            "## Пример 1\n"
            "Условие задачи.\n\n"
            "Решение:\n"
            "1. Первый шаг.\n"
            "2. Второй шаг.\n"
            "3. Ответ.\n\n"
            "## Типичные ошибки\n"
            "- Ошибка 1 и как ее избежать.\n"
            "- Ошибка 2 и как ее избежать.\n\n"
            "## Задания для тренировки\n"
            "1. Задание.\n"
            "2. Задание.\n"
            "3. Задание.\n\n"
            "## Ответы\n"
            "1. Ответ.\n"
            "2. Ответ.\n"
            "3. Ответ.\n"
        )
        exam_article = (
            f"> Разберем задание {ctx['task_number']} по предмету «{ctx['subject']}»: что проверяют, какой алгоритм использовать и как избежать типичных ошибок.\n\n"
            "## Что проверяет задание\n"
            "Опишите навык, который нужен ученику.\n\n"
            "## Алгоритм решения\n"
            "1. Что делаем сначала.\n"
            "2. Как проверяем условие.\n"
            "3. Как оформляем ответ.\n\n"
            "## Разбор примера\n"
            "Условие.\n\n"
            "Решение по шагам.\n\n"
            "Ответ.\n\n"
            "## Частые ошибки\n"
            "- Ошибка 1.\n"
            "- Ошибка 2.\n\n"
            "## Практика\n"
            "Добавьте 3-5 заданий или свяжите статью с тестом через поле related_test."
        )
        english_article = (
            f"> Разберем тему «{ctx['topic']}» по английскому: правило, примеры, частые ошибки и упражнения.\n\n"
            "## Когда используется\n"
            "Объясните ситуацию простыми словами.\n\n"
            "## Правило\n"
            "Структура:\n"
            "`подлежащее + ...`\n\n"
            "## Примеры\n"
            "| English | Перевод |\n"
            "|---|---|\n"
            "| Example sentence. | Пример перевода. |\n\n"
            "## Частые ошибки\n"
            "- Ошибка 1.\n"
            "- Ошибка 2.\n\n"
            "## Упражнения\n"
            "1. Заполните пропуск.\n"
            "2. Переведите предложение.\n"
            "3. Исправьте ошибку."
        )
        faq_template = (
            "FAQ items заполняйте в отдельном поле FAQ, по одной строке:\n\n"
            f"Что важно знать по теме «{ctx['topic']}»? | Нужно понимать основное правило и уметь применять его на примерах.\n"
            f"Какие ошибки чаще всего бывают в теме «{ctx['topic']}»? | Ученики часто пропускают ключевое условие задачи или применяют правило механически.\n"
            f"Как быстро закрепить тему «{ctx['topic']}»? | Разберите 2-3 примера, затем решите короткий тест и проверьте ошибки.\n"
        )
        blocks = [
            self._template_card('Статья по школьной теме', school_article, 'Для математики, русского, физики, информатики и других школьных тем.'),
            self._template_card('Разбор задания ОГЭ/ЕГЭ', exam_article, 'Для материалов с exam_type ОГЭ/ЕГЭ и номером задания.'),
            self._template_card('Английский язык', english_article, 'Для grammar/vocabulary материалов.'),
            self._template_card('FAQ для поля faq_items', faq_template, 'Скопируйте строки в поле FAQ items и адаптируйте.'),
        ]
        return format_html(
            '<div style="max-width: 900px;">'
            '<div style="padding: 12px; border: 1px solid #bfdbfe; border-radius: 10px; background: #eff6ff; color: #1e3a8a;">'
            '<strong>Шаблоны структуры:</strong> копируйте нужный блок в Article markdown, затем заменяйте примеры и формулировки под конкретную тему.'
            '</div>{}</div>',
            format_html_join('', '{}', ((block,) for block in blocks)),
        )

    content_template_guide.short_description = 'Content templates'


    def image_workflow_note(self, obj):
        return format_html(
            "<b>How to use images:</b><br>"
            "1) Upload files in the <i>Material images</i> block below.<br>"
            "2) For article markdown use snippet <code>![alt](/media/...)</code>.<br>"
            "3) For tests in <code>test_payload</code> use <code>image_url</code> / <code>image_alt</code> "
            "for question and options.<br>"
            "4) For the test bank use image fields directly in question and option rows."
        )

    image_workflow_note.short_description = 'Image workflow'


class MaterialImageInline(admin.TabularInline):
    model = MaterialImage
    extra = 0
    fields = (
        'preview',
        'image',
        'title',
        'alt_text',
        'usage',
        'sort_order',
        'markdown_for_article',
        'snippet_for_test',
    )
    readonly_fields = ('preview', 'markdown_for_article', 'snippet_for_test')
    ordering = ('sort_order', 'id')

    def preview(self, obj):
        if not obj.pk or not obj.image:
            return '-'
        return format_html(
            '<img src="{}" alt="{}" style="max-width: 140px; max-height: 80px; border-radius: 6px;"/>',
            obj.image.url,
            obj.alt_text or obj.title or 'preview',
        )

    preview.short_description = 'Preview'

    def markdown_for_article(self, obj):
        return obj.markdown_snippet if obj.pk else ''

    markdown_for_article.short_description = 'Markdown for article'

    def snippet_for_test(self, obj):
        return obj.test_json_snippet if obj.pk else ''

    snippet_for_test.short_description = 'JSON for payload test'


MaterialItemAdmin.inlines = (MaterialImageInline,)


class MaterialTestOptionInline(admin.TabularInline):
    model = MaterialTestOption
    extra = 1
    fields = ('order', 'label', 'value', 'image', 'image_alt', 'is_correct', 'is_active')


@admin.register(MaterialTestQuestion)
class MaterialTestQuestionAdmin(admin.ModelAdmin):
    list_display = ('code', 'test', 'question_type', 'points', 'order', 'is_active', 'updated_at')
    list_filter = ('question_type', 'is_active', 'test__material__subject')
    search_fields = ('code', 'prompt', 'test__material__title')
    list_editable = ('points', 'order', 'is_active')
    inlines = [MaterialTestOptionInline]


class MaterialTestQuestionInline(admin.TabularInline):
    model = MaterialTestQuestion
    extra = 1
    fields = ('order', 'code', 'question_type', 'points', 'required', 'is_active', 'prompt', 'image', 'image_alt')
    show_change_link = True


@admin.register(MaterialTest)
class MaterialTestAdmin(admin.ModelAdmin):
    list_display = (
        'material',
        'title',
        'passing_score_percent',
        'duration_minutes',
        'max_attempts',
        'is_active',
        'questions_total',
        'updated_at',
    )
    list_filter = ('is_active', 'material__subject', 'material__exam_type')
    search_fields = ('title', 'material__title', 'material__slug')
    inlines = [MaterialTestQuestionInline]

    def questions_total(self, obj):
        return obj.questions.count()

    questions_total.short_description = 'Questions'


@admin.register(MaterialTestAttempt)
class MaterialTestAttemptAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'material',
        'user',
        'attempt_no',
        'score_points',
        'max_points',
        'score_percent',
        'passed',
        'submitted_at',
    )
    list_filter = ('passed', 'material', 'material__subject', 'submitted_at')
    search_fields = ('material__title', 'user__username', 'user__email', 'session_key')
    readonly_fields = (
        'material',
        'user',
        'session_key',
        'attempt_no',
        'max_points',
        'score_points',
        'score_percent',
        'passed',
        'duration_seconds',
        'answers_payload',
        'result_payload',
        'started_at',
        'submitted_at',
    )
