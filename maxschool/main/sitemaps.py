from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from accounts.models import Subject
from .models import MaterialCategory, MaterialItem


class StaticViewSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.8

    def items(self):
        return [
            "home",
            "teachers_list",
            "materials_list",
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
            .filter(is_published=True, subject=item)
            .order_by("-created_at")
            .values_list("created_at", flat=True)
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
            .filter(is_published=True)
            .order_by("-created_at")
            .values_list("created_at", flat=True)
            .first()
        )
