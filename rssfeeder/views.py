from django.shortcuts import render
from django.contrib import messages
from django.views.generic import ListView, TemplateView, View
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.shortcuts import redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import permission_required
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db.models import Q
from .models import Feed


cat_data = {
    "/news": Feed.objects.filter(category__name='News').order_by("-pub_date"),
    "/tech": Feed.objects.filter(category__name='Tech').order_by("-pub_date"),
    "/videos": Feed.objects.filter(category__name='Videos').order_by("-pub_date"),
    "/science": Feed.objects.filter(category__name='Science').order_by("-pub_date"),
    "/": Feed.objects.filter(category__name='Default').order_by("-pub_date"),
}


@permission_required('rssfeeder.view_feed', login_url='/login')
def index(request):
    posts = cat_data.get(request.path)
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
        return Feed.objects.filter(Q(title__icontains=query) | Q(description__icontains=query))


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
