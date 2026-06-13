from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from accounts.models import Subject
from .material_hubs import MATERIAL_HUBS, MATERIAL_HUB_SITEMAP_MIN_ITEMS, material_hub_queryset
from .models import MaterialCategory, MaterialItem


class StaticViewSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.8

    def items(self):
        return [
            "home",
            "teachers_list",
            "materials_list",
            "oge_landing",
            "ege_landing",
            "english_landing",
            "school_subjects_landing",
            "vpr_landing",
            "privacy_policy",
            "public_offer",
            "trial",
            "teacher_application",
        ]

    def location(self, item):
        return reverse(item)


class SubjectSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.7

    def items(self):
        return Subject.objects.exclude(slug__isnull=True).exclude(slug="").order_by("id")

    def location(self, item):
        return reverse("subject_detail", kwargs={"slug": item.slug})

    def lastmod(self, item):
        return (
            MaterialItem.objects
            .filter(status="published", access_level="public", subject=item)
            .order_by("-updated_at", "-published_at", "-created_at")
            .values_list("updated_at", flat=True)
            .first()
        )


class MaterialCategorySitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.6

    def items(self):
        return MaterialCategory.objects.filter(is_active=True).order_by("sort_order", "id")

    def location(self, item):
        return reverse("materials_category", kwargs={"slug": item.slug})

    def lastmod(self, item):
        return (
            item.materials
            .filter(status="published", access_level="public")
            .order_by("-updated_at", "-published_at", "-created_at")
            .values_list("updated_at", flat=True)
            .first()
        )


class MaterialHubSitemap(Sitemap):
    changefreq = "weekly"

    def items(self):
        items = []
        subjects = Subject.objects.exclude(slug__isnull=True).exclude(slug="").order_by("id")
        for hub_slug in MATERIAL_HUBS:
            for subject in subjects:
                queryset = material_hub_queryset(hub_slug, subject)
                if queryset.count() < MATERIAL_HUB_SITEMAP_MIN_ITEMS:
                    continue
                items.append({
                    "hub_slug": hub_slug,
                    "subject_slug": subject.slug,
                    "lastmod": (
                        queryset
                        .order_by("-updated_at", "-published_at", "-created_at")
                        .values_list("updated_at", flat=True)
                        .first()
                    ),
                })
        return items

    def location(self, item):
        return reverse("materials_hub", kwargs={
            "hub_slug": item["hub_slug"],
            "subject_slug": item["subject_slug"],
        })

    def lastmod(self, item):
        return item["lastmod"]

    def priority(self, item):
        if item["hub_slug"] in {"oge", "ege"}:
            return 0.85
        return 0.75


class MaterialItemSitemap(Sitemap):
    changefreq = "weekly"

    def items(self):
        return (
            MaterialItem.objects
            .filter(status="published", access_level="public")
            .exclude(slug__isnull=True)
            .exclude(slug="")
            .order_by("-published_at", "-created_at")
        )

    def location(self, obj):
        return reverse("material_detail", kwargs={"slug": obj.slug})

    def lastmod(self, obj):
        return obj.updated_at or obj.published_at or obj.created_at

    def priority(self, obj):
        # Keep exam materials slightly higher and boost fresh publications.
        if obj.exam_type in {"oge", "ege"}:
            return 0.9
        return 0.8 if obj.published_at else 0.7
