from django.urls import path, re_path
from .views import index, SearchResults, LoginView, LogoutView, userfavorites, AddFavorite
from rssfeeder.models import Category


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
    path("search/", SearchResults.as_view(), name="search"),
    path("favorites", userfavorites, name="favorites"),
    path("favops", AddFavorite.as_view(), name="favops"),
]

for i in Category.objects.all():
    if i.name == "Default":
        urlpatterns.append(
            path("", index, name="home")
        )
    else:
        urlpatterns.append(
            path(i.name, index, name=i.name)
        )
