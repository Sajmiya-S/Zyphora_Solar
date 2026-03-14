from django.db import models
from django.utils.text import slugify




class BlogPost(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, blank=True)
    summary = models.TextField(blank=True,null=True)
    content = models.TextField()
    image = models.ImageField(upload_to='blog_images/')
    published_date = models.DateField(auto_now_add=True)

    def save(self):
        if not self.slug:
            self.slug = slugify(self.title)

        return super().save()

    def __str__(self):
        return self.title


