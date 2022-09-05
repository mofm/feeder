from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.models import User
from django.views.generic import TemplateView, View, ListView
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import permission_required
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db.models import Q
from .models import Feed, UserFavorites, Category


def catdata():
    cat_data = {}
    for cat in Category.objects.all():
        if cat.name == 'Default':
            cat_data['/'] = Feed.objects.filter(category__name='Default').order_by("-pub_date")
        else:
            cat_data[f"/{cat.name}"] = Feed.objects.filter(category__name=cat.name).order_by("-pub_date")

    return cat_data


def paginate(posts, request):
    p = Paginator(posts, 10)  # creating a paginator object
    # getting the desired page number from url
    page_number = request.GET.get('page')
    try:
        page_obj = p.get_page(page_number)  # returns the desired page object
    except PageNotAnInteger:
        # if page_number is not an integer then assign the first page
        page_obj = p.page(1)
    except EmptyPage:
        # if page is empty then return last page
        page_obj = p.page(p.num_pages)
    context = {'page_obj': page_obj}
    return context


@permission_required('rssfeeder.view_feed', login_url='/login')
def index(request):
    posts = catdata().get(request.path)
    context = paginate(posts, request)
    # sending the page object to index.html
    return render(request, 'index.html', context)


class SearchResults(PermissionRequiredMixin, ListView):
    login_url = '/login'
    permission_required = 'rssfeeder.view_feed'
    template_name = 'search.html'
    model = Feed
    context_object_name = "page_obj"

    def get_queryset(self):
        query = self.request.GET.get("q")
        if query:
            object_list = self.model.objects.filter(
                Q(title__icontains=query) | Q(description__icontains=query)
            )
            return object_list


class LoginView(TemplateView, View):
    template_name = 'login.html'

    def get(self, request, *args, **kwargs):
        return self.render_to_response({})

    def post(self, request, *args, **kwargs):
        user = authenticate(username=request.POST.get('username'),
                            password=request.POST.get('password'))
        next_url = request.POST.get('next')
        if not next_url:
            next_url = 'home'

        if user is not None:
            # the password verified for the user
            if user.is_active:
                login(request, user)
                messages.success(request, "You are now logged in!")
            else:
                messages.warning(request, "The password is valid, but the account has been disabled!")
        else:
            # the authentication system was unable to verify the username and password
            messages.warning(request, "The username and password were incorrect.")

        return redirect(next_url)


class LogoutView(View):
    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('home')

        logout(request)
        messages.success(request, "You are now logged out!")
        return redirect('home')


@permission_required('rssfeeder.view_feed', login_url='/login')
def userfavorites(request):
    user = request.user.id
    posts = UserFavorites.objects.filter(user=user)
    context = paginate(posts, request)
    return render(request, 'favorites.html', context)


class AddFavorite(PermissionRequiredMixin, View):
    login_url = '/login'
    permission_required = 'rssfeeder.view_feed'

    def post(self, request, *args, **kwargs):
        user = User.objects.get(id=request.user.id)
        feed = Feed.objects.get(pk=request.POST.get('pk'))

        if 'addfavorite' in request.POST:
            UserFavorites.objects.get_or_create(user=user, favorites=feed)
            messages.success(request, "Feed added to favorites!")
        elif 'removefavorite' in request.POST:
            UserFavorites.objects.filter(user=user).get(favorites=feed).delete()
            messages.success(request, "Feed removed from favorites!")

        return redirect(request.META.get('HTTP_REFERER'))
