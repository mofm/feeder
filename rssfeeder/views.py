from django.shortcuts import redirect
from django.http import Http404
from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib.auth.models import User
from django.views.generic import TemplateView, View, ListView
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.mixins import PermissionRequiredMixin, LoginRequiredMixin
from django.contrib.auth.views import PasswordChangeView
from django.urls import reverse_lazy
from django.db import IntegrityError
from django.db.models import Q
from .models import Feed, UserFavorites, Category
from .forms import UserUpdateForm


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


class IndexView(PermissionRequiredMixin, TemplateView):
    login_url = '/login'
    permission_required = 'rssfeeder.view_feed'
    template_name = 'index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        posts = catdata().get(self.request.path)
        if posts:
            context.update(paginate(posts, self.request))
        else:
            context.update({'page_obj': None})
        return context


class ChannelView(PermissionRequiredMixin, TemplateView):
    login_url = '/login'
    permission_required = 'rssfeeder.view_feed'
    template_name = 'index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        posts = Feed.objects.filter(channel_name=self.kwargs['channel']).order_by("-pub_date")
        if posts:
            context.update(paginate(posts, self.request))
        else:
            raise Http404("Channel does not exist")
        return context


class SearchResults(PermissionRequiredMixin, TemplateView):
    login_url = '/login'
    permission_required = 'rssfeeder.view_feed'
    template_name = 'search.html'
    model = Feed

    def get_queryset(self):
        query = self.request.GET.get("q")
        if query:
            object_list = self.model.objects.filter(
                Q(title__icontains=query) | Q(description__icontains=query)
            ).distinct()
            return object_list
        return []

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(paginate(self.get_queryset().order_by('pub_date'), self.request))
        return context


class LoginView(TemplateView, View):
    template_name = 'login.html'

    def get(self, request, *args, **kwargs):
        return self.render_to_response({})

    def post(self, request, *args, **kwargs):
        user = authenticate(username=self.request.POST.get('username'),
                            password=self.request.POST.get('password'))
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
        if not self.request.user.is_authenticated:
            return redirect('home')

        logout(request)
        messages.success(request, "You are now logged out!")
        return redirect('home')


class UserFavoritesView(PermissionRequiredMixin, ListView):
    login_url = '/login'
    permission_required = 'rssfeeder.view_feed'
    template_name = 'favorites.html'
    model = UserFavorites

    def get_queryset(self):
        user = self.request.user.id
        object_list = self.model.objects.filter(user=user).order_by("-created_on")
        return object_list

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(paginate(self.get_queryset(), self.request))
        return context


class AddFavorite(PermissionRequiredMixin, View):
    login_url = '/login'
    permission_required = 'rssfeeder.view_feed'

    def post(self, request, *args, **kwargs):
        user = User.objects.get(id=self.request.user.id)
        feed = Feed.objects.get(pk=self.request.POST.get('pk'))

        if 'addfavorite' in request.POST:
            UserFavorites.objects.get_or_create(user=user, favorites=feed)
            messages.success(request, "Feed added to favorites!")
        elif 'removefavorite' in request.POST:
            UserFavorites.objects.filter(user=user).get(favorites=feed).delete()
            messages.success(request, "Feed removed from favorites!")

        return redirect(request.META.get('HTTP_REFERER'))


class ProfileView(LoginRequiredMixin, TemplateView):
    login_url = '/login'
    template_name = 'profile.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile_form = UserUpdateForm(self.request.POST or None, instance=self.request.user)
        context.update({'form': profile_form})
        return context

    def post(self, request, *args, **kwargs):
        context = self.get_context_data()
        try:
            if 'profile_form' in request.POST and context['profile_form'].is_valid():
                context['profile_form'].save()
                messages.success(request, "Profile updated successfully!")
        except IntegrityError:
            messages.warning(request, "Email already exists!")

        return self.render_to_response(context)


class ChangePasswordView(LoginRequiredMixin, SuccessMessageMixin, PasswordChangeView):
    login_url = '/login'
    template_name = 'change_password.html'
    success_message = "Successfully Changed Your Password"
    success_url = reverse_lazy('home')
