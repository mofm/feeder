from django.urls import path
from .views import index, SearchResults


urlpatterns = [
    path("news", index, name="newspage"),
    path("tech", index, name="techpage"),
    path("videos", index, name="videospage"),
    path("science", index, name="sciencepage"),
    path('search/', SearchResults.as_view(), name="search"),
]
