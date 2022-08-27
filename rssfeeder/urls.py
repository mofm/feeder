from django.urls import path, re_path
from .views import index, SearchResults, LoginView, LogoutView


urlpatterns = [
    re_path(
        r'^login/$',
        LoginView.as_view(),
        name='login'
    ),
    re_path(
        r'^logout/$',
        LogoutView.as_view(),
        name='logout'
    ),
    path("", index, name="home"),
    path("news", index, name="newspage"),
    path("tech", index, name="techpage"),
    path("videos", index, name="videospage"),
    path("science", index, name="sciencepage"),
    path("search/", SearchResults.as_view(), name="search"),
]
