from django.urls import path, re_path
from .views import IndexView, SearchResults, LoginView, LogoutView, UserFavoritesView, \
    AddFavorite, ProfileView, ChangePasswordView, ChannelView


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
    path("", IndexView.as_view(), name="home"),
    path("channel/<str:channel>", ChannelView.as_view(), name="channel"),
    path("news", IndexView.as_view(), name="newspage"),
    path("tech", IndexView.as_view(), name="techpage"),
    path("videos", IndexView.as_view(), name="videospage"),
    path("science", IndexView.as_view(), name="sciencepage"),
    path("search/", SearchResults.as_view(), name="search"),
    path("favorites", UserFavoritesView.as_view(), name="favorites"),
    path("favops", AddFavorite.as_view(), name="favops"),
    path("profile/<username>", ProfileView.as_view(), name="profile"),
    path('password-change/', ChangePasswordView.as_view(), name='password_change'),
]
