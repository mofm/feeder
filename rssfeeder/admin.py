from django.contrib import admin
from .models import Feed, Category


# Register your models here.
@admin.register(Feed)
class EpisodeAdmin(admin.ModelAdmin):
    list_display = ("channel_name", "title", "pub_date", "category")


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name",)
