from django.db import models
from django.core.validators import URLValidator
from django.contrib.auth.models import User


class Category(models.Model):
    name = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.name


class Feed(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    pub_date = models.DateTimeField(db_index=True)
    link = models.TextField(validators=[URLValidator()])
    channel_img = models.URLField()
    feed_img = models.URLField()
    channel_name = models.CharField(max_length=100, db_index=True)
    guid = models.CharField(max_length=200, db_index=True, unique=True)
    category = models.ForeignKey('Category', related_name='feeds', on_delete=models.CASCADE, db_index=True)

    def __str__(self) -> str:
        return f"{self.channel_name}: {self.title}"


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, db_index=True)
    created_on = models.DateTimeField(auto_now_add=True)
    favorites = models.ManyToManyField('Feed', related_name='favorited_by')
    read = models.ManyToManyField('Feed', related_name='read_by')

    def __str__(self):
        return self.user.username