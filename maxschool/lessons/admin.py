from django.contrib import admin

from .models import (
    LessonBooking,
    LessonCard,
    LessonDeck,
    LessonDeckSession,
)


@admin.register(LessonBooking)
class LessonBookingAdmin(admin.ModelAdmin):
    list_display = ('student', 'teacher', 'subject', 'date', 'time', 'is_confirmed')
    list_filter = ('subject', 'date', 'is_confirmed')
    search_fields = ('student__username', 'student__email', 'teacher__username', 'teacher__email')


class LessonCardInline(admin.StackedInline):
    model = LessonCard
    extra = 1
    fields = (
        'order',
        'card_type',
        'title',
        'body',
        'image',
        'attachment',
        'video_url',
        'teacher_notes',
        'is_active',
    )


@admin.register(LessonDeck)
class LessonDeckAdmin(admin.ModelAdmin):
    list_display = ('title', 'subject', 'grade', 'topic', 'cards_count', 'is_active', 'sort_order')
    list_filter = ('is_active', 'subject', 'grade')
    search_fields = ('title', 'topic', 'description', 'cards__title', 'cards__body')
    list_editable = ('is_active', 'sort_order')
    inlines = (LessonCardInline,)

    @admin.display(description='Карточек')
    def cards_count(self, obj):
        return obj.cards.count()


@admin.register(LessonCard)
class LessonCardAdmin(admin.ModelAdmin):
    list_display = ('deck', 'order', 'card_type', 'title', 'is_active')
    list_filter = ('card_type', 'is_active', 'deck__subject', 'deck__grade')
    search_fields = ('title', 'body', 'teacher_notes', 'deck__title', 'deck__topic')
    list_editable = ('order', 'is_active')


@admin.register(LessonDeckSession)
class LessonDeckSessionAdmin(admin.ModelAdmin):
    list_display = ('lesson', 'deck', 'current_card', 'updated_by', 'updated_at')
    list_filter = ('deck__subject', 'deck__grade', 'updated_at')
    search_fields = (
        'lesson__student__username',
        'lesson__teacher__username',
        'deck__title',
        'current_card__title',
    )
    readonly_fields = ('updated_at',)
