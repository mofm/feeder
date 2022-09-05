from django.db import models
from django.contrib.auth.models import User


class Category(models.Model):
    name = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.name


class Feed(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    pub_date = models.DateTimeField()
    link = models.URLField()
    channel_img = models.URLField()
    feed_img = models.URLField()
    channel_name = models.CharField(max_length=100)
    guid = models.CharField(max_length=200)
    category = models.ForeignKey('Category', related_name='feeds', on_delete=models.CASCADE)

    def __str__(self) -> str:
        return f"{self.channel_name}: {self.title}"


class UserFavorites(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created_on = models.DateTimeField(auto_now_add=True)
    favorites = models.ForeignKey(Feed, on_delete=models.PROTECT, related_name='favorites', blank=False)
