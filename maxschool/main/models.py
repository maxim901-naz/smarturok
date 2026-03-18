from django.db import models


class Review(models.Model):
    name = models.CharField(max_length=120)
    text = models.TextField()
    rating = models.PositiveSmallIntegerField(default=5)
    is_published = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.rating}/5)"


class MaterialCategory(models.Model):
    title = models.CharField(max_length=120)
    slug = models.SlugField(max_length=120, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['sort_order', 'title']

    def __str__(self):
        return self.title


class MaterialItem(models.Model):
    category = models.ForeignKey(MaterialCategory, on_delete=models.CASCADE, related_name='materials')
    title = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    subject = models.ForeignKey('accounts.Subject', on_delete=models.SET_NULL, null=True, blank=True)
    grade = models.PositiveSmallIntegerField(null=True, blank=True)
    file = models.FileField(upload_to='materials/', blank=True, null=True)
    external_url = models.URLField(blank=True)
    is_published = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title
