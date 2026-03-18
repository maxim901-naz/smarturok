# lessons/forms.py
from django import forms
from django.utils import timezone
from django.db import transaction
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo
from .models import LessonBooking, HomeworkSubmission, TeacherAvailability
from accounts.models import Lesson  # Импортируем модель Lesson
from accounts.models import Subject
from .utils import SERIES_WEEKS, BOOKING_MIN_HOURS, TEACHER_TZ

class LessonBookingForm(forms.Form):
    """
    Форма для записи ученика на урок.
    Создает сразу объект Lesson, а не LessonBooking.
    """
    slot = forms.ChoiceField(
        choices=[],
        label="Выберите свободное время",
        required=True,
        widget=forms.HiddenInput()
    )
    slots = forms.CharField(required=False, widget=forms.HiddenInput())
    subject = forms.ModelChoiceField(queryset=Subject.objects.none(), label="Предмет", required=True)
    
    def __init__(self, *args, **kwargs):
        self.student = kwargs.pop('student')
        self.teacher = kwargs.pop('teacher')
        super().__init__(*args, **kwargs)
        if self.teacher:
            self.fields['subject'].queryset = self.teacher.subjects_taught.all()
            if not self.fields['subject'].queryset.exists() and getattr(self.teacher, 'desired_subject', None):
                self.fields['subject'].queryset = Subject.objects.filter(id=self.teacher.desired_subject_id)
        else:
            self.fields['subject'].queryset = Subject.objects.none()
        
        if self.teacher:
            # Получаем доступные слоты
            available_slots = self._get_available_slots()
            
            # Создаем choices для поля slot
            slot_choices = [('', '-- Выберите время --')]
            for slot_data in available_slots:
                slot_choices.append((slot_data['id'], slot_data['display_text']))
            
            self.fields['slot'].choices = slot_choices
            
            # Добавляем атрибут для группировки в шаблон
            self.available_slots_grouped = self._group_slots_by_date(available_slots)
            self.available_slots_by_weekday = self._group_slots_by_weekday(available_slots)

    def _teacher_tz(self):
        tz_name = "Europe/Moscow"
        try:
            return ZoneInfo(tz_name)
        except Exception:
            return TEACHER_TZ

    def _student_tz(self):
        tz_name = getattr(self.student, "time_zone", None) or "Europe/Moscow"
        try:
            return ZoneInfo(tz_name)
        except Exception:
            return TEACHER_TZ

    def _get_available_slots(self):
        """Получаем все доступные слоты учителя, исключая те, на которые уже есть уроки."""
        from django.utils import timezone
        teacher_tz = self._teacher_tz()
        student_tz = self._student_tz()
        now = timezone.now().astimezone(teacher_tz)
        min_dt = now + timedelta(hours=BOOKING_MIN_HOURS)
        today = now.date()
        current_time = now.time()

        slots_data = []

        # Получаем все слоты учителя
        all_slots = TeacherAvailability.objects.filter(teacher=self.teacher)
        
        for slot in all_slots:
            if slot.is_recurring:
                # Пропускаем, если не указан день недели
                if slot.weekday is None:
                    continue

                # Находим ближайший день недели для регулярного слота
                weekday_target = slot.weekday
                days_ahead = (weekday_target - today.weekday() + 7) % 7
                if days_ahead == 0 and slot.time <= current_time:
                    days_ahead = 7  # если сегодня уже поздно — следующий такой день
                
                # Создаем слоты на SERIES_WEEKS вперед
                for week in range(SERIES_WEEKS):
                    slot_date = today + timedelta(days=days_ahead + week*7)
                    
                    # Слоты только в будущем
                    slot_dt = timezone.make_aware(datetime.combine(slot_date, slot.time), teacher_tz)
                    if slot_dt <= min_dt:
                        continue
                    if (slot_date > today) or (slot_date == today and slot.time > current_time):
                        # Проверяем, есть ли уже урок на эту дату и время
                        if Lesson.objects.filter(teacher=self.teacher, date=slot_date, time=slot.time).exists():
                            continue
                        
                        local_start = slot_dt.astimezone(student_tz)
                        display_text = f"{local_start.strftime('%d.%m.%Y')} ({slot.get_weekday_display()}) {local_start.strftime('%H:%M')} (рег.)"
                        slots_data.append({
                            'id': f"rec_{slot.id}_{slot_date.strftime('%Y%m%d')}",
                            'date': slot_date,
                            'time': slot.time,
                            'display_date': local_start.date(),
                            'display_time': local_start.time(),
                            'display_text': display_text,
                            'group_date': local_start.date(),
                            'is_recurring': True,
                            'slot_obj': slot
                        })

            else:
                # Разовые слоты
                if slot.date:
                    slot_dt = timezone.make_aware(datetime.combine(slot.date, slot.time), teacher_tz)
                    if slot_dt <= min_dt:
                        continue
                if slot.date and ((slot.date > today) or (slot.date == today and slot.time > current_time)):
                    # Проверяем, есть ли уже урок на эту дату и время
                    if Lesson.objects.filter(teacher=self.teacher, date=slot.date, time=slot.time).exists():
                        continue
                    
                    local_start = slot_dt.astimezone(student_tz)
                    display_text = f"{local_start.strftime('%d.%m.%Y')} {local_start.strftime('%H:%M')}"
                    slots_data.append({
                        'id': f"once_{slot.id}",
                        'date': slot.date,
                        'time': slot.time,
                        'display_date': local_start.date(),
                        'display_time': local_start.time(),
                        'display_text': display_text,
                        'group_date': local_start.date(),
                        'is_recurring': False,
                        'slot_obj': slot
                    })

        # Сортируем слоты по дате и времени
        slots_data.sort(key=lambda x: (x['date'], x['time']))

        return slots_data
    
    def _group_slots_by_date(self, slots_data):
        """Группирует слоты по дате для удобного отображения в шаблоне"""
        grouped = {}
        for slot in slots_data:
            group_date = slot.get('group_date') or slot['date']
            date_key = group_date.strftime('%Y-%m-%d')
            if date_key not in grouped:
                grouped[date_key] = {
                    'date': group_date,
                    'date_display': group_date.strftime('%d.%m.%Y'),
                    'slots': []
                }
            grouped[date_key]['slots'].append(slot)
        
        # Сортируем по дате
        sorted_groups = sorted(grouped.values(), key=lambda x: x['date'])
        
        return sorted_groups

    def _group_slots_by_weekday(self, slots_data):
        """Компактная группировка слотов по дням недели для UI в стиле колонок."""
        labels = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']
        columns = [{'weekday': i, 'label': labels[i], 'slots': []} for i in range(7)]

        for slot in slots_data:
            display_date = slot.get('group_date') or slot.get('display_date') or slot['date']
            weekday = display_date.weekday()
            columns[weekday]['slots'].append(slot)

        for col in columns:
            col['slots'].sort(
                key=lambda s: (
                    s.get('display_date') or s.get('group_date') or s['date'],
                    s.get('display_time') or s['time']
                )
            )

        return columns


    def clean_subject(self):
        subject = self.cleaned_data.get('subject')
        if not subject:
            raise forms.ValidationError("Выберите предмет")
        if self.teacher:
            subjects = list(self.teacher.subjects_taught.all())
            if subjects and subject not in subjects:
                raise forms.ValidationError("Этот предмет недоступен у выбранного преподавателя")
            if not subjects and getattr(self.teacher, 'desired_subject', None) and subject != self.teacher.desired_subject:
                raise forms.ValidationError("Этот предмет недоступен у выбранного преподавателя")
        return subject

    def clean_slot(self):
        return self.cleaned_data.get('slot')

    def clean_slots(self):
        raw = (self.cleaned_data.get('slots') or '').strip()
        if not raw:
            return []

        seen = set()
        slot_ids = []
        for item in raw.split(','):
            sid = item.strip()
            if not sid or sid in seen:
                continue
            seen.add(sid)
            slot_ids.append(sid)

        valid_slot_ids = {str(value) for value, _ in self.fields['slot'].choices if value}
        invalid = [sid for sid in slot_ids if sid not in valid_slot_ids]
        if invalid:
            raise forms.ValidationError("Часть выбранных слотов уже недоступна. Обновите страницу и выберите снова.")

        recurring_count = sum(1 for sid in slot_ids if sid.startswith('rec_'))
        if recurring_count > 4:
            raise forms.ValidationError("За один раз можно выбрать не более 4 регулярных слотов.")

        self._validate_selected_slots_overlap(slot_ids)

        return slot_ids

    @staticmethod
    def _time_to_minutes(time_obj):
        return time_obj.hour * 60 + time_obj.minute

    @staticmethod
    def _ranges_overlap(start_a, end_a, start_b, end_b):
        return start_a < end_b and start_b < end_a

    def _parse_slot_reference(self, slot_id):
        parts = slot_id.split('_')
        if not parts:
            raise forms.ValidationError("Некорректный слот.")

        slot_type = parts[0]
        if slot_type == 'once':
            if len(parts) < 2:
                raise forms.ValidationError("Некорректный разовый слот.")
            return slot_type, int(parts[1]), None

        if slot_type == 'rec':
            if len(parts) < 3:
                raise forms.ValidationError("Некорректный регулярный слот.")
            raw_date = parts[3] if len(parts) >= 4 else parts[2]
            try:
                start_date = date(int(raw_date[0:4]), int(raw_date[4:6]), int(raw_date[6:8]))
            except Exception:
                raise forms.ValidationError("Некорректная дата регулярного слота.")
            return slot_type, int(parts[1]), start_date

        raise forms.ValidationError("Неизвестный тип слота.")

    def _build_occurrences_for_validation(self, slot_type, slot_obj, start_date, min_dt, teacher_tz, slot_id):
        duration = slot_obj.duration_minutes or 30
        occurrences = []

        if slot_type == 'once':
            if not slot_obj.date:
                raise forms.ValidationError("Разовый слот без даты недоступен.")
            lesson_dt = timezone.make_aware(datetime.combine(slot_obj.date, slot_obj.time), teacher_tz)
            if lesson_dt > min_dt:
                occurrences.append({
                    'slot_id': slot_id,
                    'date': slot_obj.date,
                    'start': self._time_to_minutes(slot_obj.time),
                    'end': self._time_to_minutes(slot_obj.time) + duration,
                })
            return occurrences

        if slot_type == 'rec':
            for week in range(SERIES_WEEKS):
                lesson_date = start_date + timedelta(weeks=week)
                lesson_dt = timezone.make_aware(datetime.combine(lesson_date, slot_obj.time), teacher_tz)
                if lesson_dt <= min_dt:
                    continue
                occurrences.append({
                    'slot_id': slot_id,
                    'date': lesson_date,
                    'start': self._time_to_minutes(slot_obj.time),
                    'end': self._time_to_minutes(slot_obj.time) + duration,
                })
            return occurrences

        return occurrences

    def _validate_selected_slots_overlap(self, slot_ids):
        if len(slot_ids) < 2:
            return

        teacher_tz = self._teacher_tz()
        now = timezone.now().astimezone(teacher_tz)
        min_dt = now + timedelta(hours=BOOKING_MIN_HOURS)

        parsed = [self._parse_slot_reference(sid) for sid in slot_ids]
        slot_ids_db = [slot_pk for _, slot_pk, _ in parsed]
        slot_map = {
            slot.id: slot
            for slot in TeacherAvailability.objects.filter(teacher=self.teacher, id__in=slot_ids_db)
        }
        if len(slot_map) != len(set(slot_ids_db)):
            raise forms.ValidationError("Часть выбранных слотов больше недоступна.")

        by_date = {}
        for source_id, (slot_type, slot_pk, start_date) in zip(slot_ids, parsed):
            slot_obj = slot_map[slot_pk]
            occurrences = self._build_occurrences_for_validation(
                slot_type=slot_type,
                slot_obj=slot_obj,
                start_date=start_date,
                min_dt=min_dt,
                teacher_tz=teacher_tz,
                slot_id=source_id,
            )
            for occ in occurrences:
                by_date.setdefault(occ['date'], []).append(occ)

        for _, occurrences in by_date.items():
            occurrences.sort(key=lambda item: item['start'])
            for i, first in enumerate(occurrences):
                for second in occurrences[i + 1:]:
                    if second['start'] >= first['end']:
                        break
                    if first['slot_id'] == second['slot_id']:
                        continue
                    if self._ranges_overlap(first['start'], first['end'], second['start'], second['end']):
                        raise forms.ValidationError(
                            "Выбранные слоты пересекаются по времени. Уберите пересекающиеся занятия."
                        )

    def clean(self):
        cleaned_data = super().clean()
        slot_ids = cleaned_data.get('slots') or []
        slot_id = (cleaned_data.get('slot') or '').strip()

        if not slot_id and slot_ids:
            slot_id = slot_ids[0]
            cleaned_data['slot'] = slot_id

        if not slot_id:
            self.add_error('slot', "Пожалуйста, выберите время для занятия")
            return cleaned_data

        valid_slot_ids = {str(value) for value, _ in self.fields['slot'].choices if value}
        if slot_id not in valid_slot_ids:
            self.add_error('slot', "Выбранный слот недоступен. Обновите страницу и выберите снова.")

        return cleaned_data

    def _teacher_has_lesson_overlap(self, lesson_date, lesson_time, duration_minutes):
        start = self._time_to_minutes(lesson_time)
        end = start + (duration_minutes or 30)
        teacher_lessons = Lesson.objects.filter(teacher=self.teacher, date=lesson_date)
        for existing in teacher_lessons:
            existing_start = self._time_to_minutes(existing.time)
            existing_end = existing_start + (existing.duration_minutes or 30)
            if self._ranges_overlap(start, end, existing_start, existing_end):
                return True
        return False

    def save(self):
        slot_id = self.cleaned_data['slot']
        selected_slots = list(self.cleaned_data.get('slots') or [])
        if selected_slots and slot_id not in selected_slots:
            selected_slots.insert(0, slot_id)
        if not selected_slots:
            selected_slots = [slot_id]

        subject = self.cleaned_data.get('subject') or self.teacher.get_primary_subject()
        teacher_tz = self._teacher_tz()
        now = timezone.now().astimezone(teacher_tz)
        min_dt = now + timedelta(hours=BOOKING_MIN_HOURS)

        lessons_created = []
        with transaction.atomic():
            for selected_slot_id in selected_slots:
                lesson_or_lessons = self._save_single_slot(
                    slot_id=selected_slot_id,
                    subject=subject,
                    teacher_tz=teacher_tz,
                    now=now,
                    min_dt=min_dt
                )
                if isinstance(lesson_or_lessons, list):
                    lessons_created.extend(lesson_or_lessons)
                elif lesson_or_lessons is not None:
                    lessons_created.append(lesson_or_lessons)

        if not lessons_created:
            raise forms.ValidationError("Не удалось создать уроки. Попробуйте выбрать другое время.")

        self._create_or_get_chat()
        return lessons_created if len(lessons_created) > 1 else lessons_created[0]

    def _save_single_slot(self, slot_id, subject, teacher_tz, now, min_dt):
        parts = slot_id.split('_')
        if not parts:
            raise forms.ValidationError("Некорректный слот.")

        if parts[0] == 'rec':
            real_slot_id = int(parts[1])
            date_str = parts[3] if len(parts) >= 4 else parts[2]

            try:
                real_slot = TeacherAvailability.objects.select_for_update().get(id=real_slot_id, teacher=self.teacher)
            except TeacherAvailability.DoesNotExist:
                raise forms.ValidationError("Выбранный слот не существует")

            if real_slot.is_booked:
                raise forms.ValidationError("Регулярный слот уже занят.")

            start_date = date(int(date_str[0:4]), int(date_str[4:6]), int(date_str[6:8]))
            start_dt = timezone.make_aware(datetime.combine(start_date, real_slot.time), teacher_tz)
            if start_dt <= min_dt:
                raise forms.ValidationError(f"Нельзя записаться менее чем за {BOOKING_MIN_HOURS} часа(ов) до урока")

            weekday_names_english = {
                0: "Monday",
                1: "Tuesday",
                2: "Wednesday",
                3: "Thursday",
                4: "Friday",
                5: "Saturday",
                6: "Sunday"
            }
            english_weekday = weekday_names_english.get(real_slot.weekday, "Monday")

            created = []
            for week in range(SERIES_WEEKS):
                lesson_date = start_date + timedelta(weeks=week)
                lesson_dt = timezone.make_aware(datetime.combine(lesson_date, real_slot.time), teacher_tz)
                if lesson_date < now.date() or lesson_dt <= min_dt:
                    continue
                if self._teacher_has_lesson_overlap(
                    lesson_date=lesson_date,
                    lesson_time=real_slot.time,
                    duration_minutes=real_slot.duration_minutes or 30
                ):
                    continue

                lesson = Lesson.objects.create(
                    subject=subject,
                    teacher=self.teacher,
                    student=self.student,
                    date=lesson_date,
                    time=real_slot.time,
                    duration_minutes=real_slot.duration_minutes or 30,
                    is_recurring=True,
                    days_of_week=english_weekday,
                    end_date=start_date + timedelta(weeks=SERIES_WEEKS)
                )
                created.append(lesson)

            if not created:
                raise forms.ValidationError("Для выбранного регулярного слота не осталось доступных дат.")

            LessonBooking.objects.create(
                student=self.student,
                teacher=self.teacher,
                subject=subject,
                date=start_date,
                time=real_slot.time,
                is_confirmed=True,
                is_recurring=True
            )
            real_slot.is_booked = True
            real_slot.save(update_fields=['is_booked'])
            return created

        if parts[0] == 'once':
            real_slot_id = int(parts[1])
            try:
                real_slot = TeacherAvailability.objects.select_for_update().get(id=real_slot_id, teacher=self.teacher)
            except TeacherAvailability.DoesNotExist:
                raise forms.ValidationError("Выбранный слот не существует")

            if real_slot.is_booked:
                raise forms.ValidationError("Этот слот уже занят.")
            if not real_slot.date:
                raise forms.ValidationError("Разовый слот без даты недоступен для бронирования.")

            slot_dt = timezone.make_aware(datetime.combine(real_slot.date, real_slot.time), teacher_tz)
            if slot_dt <= min_dt:
                raise forms.ValidationError(f"Нельзя записаться менее чем за {BOOKING_MIN_HOURS} часа(ов) до урока")
            if self._teacher_has_lesson_overlap(
                lesson_date=real_slot.date,
                lesson_time=real_slot.time,
                duration_minutes=real_slot.duration_minutes or 30
            ):
                raise forms.ValidationError("Этот слот уже занят другим уроком.")

            lesson = Lesson.objects.create(
                subject=subject,
                teacher=self.teacher,
                student=self.student,
                date=real_slot.date,
                time=real_slot.time,
                duration_minutes=real_slot.duration_minutes or 30,
                is_recurring=False
            )

            LessonBooking.objects.create(
                student=self.student,
                teacher=self.teacher,
                subject=subject,
                date=real_slot.date,
                time=real_slot.time,
                is_confirmed=True,
                is_recurring=False
            )
            real_slot.is_booked = True
            real_slot.save(update_fields=['is_booked'])
            return lesson

        raise forms.ValidationError("Неизвестный тип слота")

    def _create_or_get_chat(self):
        """Создает или получает чат между учителем и учеником"""
        try:
            # Импортируем здесь чтобы избежать циклических импортов
            from chat.models import Chat
            
            # Убедимся что учитель и ученик правильно определены
            teacher = self.teacher
            student = self.student
            
            print(f"DEBUG forms.py: Создание чата: учитель={teacher.username}, ученик={student.username}")
            
            # Создаем или получаем чат
            chat, created = Chat.objects.get_or_create(
                teacher=teacher,
                student=student
            )
            
            print(f"DEBUG forms.py: Чат {'создан' if created else 'уже существует'} ID: {chat.id}")
            
            # Добавляем приветственное сообщение если чат новый
            if created:
                from chat.models import Message
                from django.utils import timezone
                
                welcome_message = f"Привет! Я ваш преподаватель {teacher.get_full_name() or teacher.username}. Давайте начнем наше обучение!"
                
                Message.objects.create(
                    chat=chat,
                    sender=teacher,
                    text=welcome_message,
                    timestamp=timezone.now()
                )
                
                print(f"DEBUG forms.py: Добавлено приветственное сообщение")
            
            return chat
            
        except Exception as e:
            print(f"DEBUG forms.py: Ошибка при создании чата: {str(e)}")
            # Не прерываем процесс создания урока из-за ошибки чата
            return None

class HomeworkSubmissionForm(forms.ModelForm):
    class Meta:
        model = HomeworkSubmission
        fields = ['file', 'comment']
