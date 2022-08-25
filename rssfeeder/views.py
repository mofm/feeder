from django.shortcuts import render
from django.views.generic import ListView
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from .models import Feed


cat_data = {
    "/news": Feed.objects.filter(category__name='News').order_by("-pub_date"),
    "/tech": Feed.objects.filter(category__name='Tech').order_by("-pub_date"),
    "/videos": Feed.objects.filter(category__name='Videos').order_by("-pub_date"),
    "/science": Feed.objects.filter(category__name='Science').order_by("-pub_date"),
    "/": Feed.objects.filter(category__name='Default').order_by("-pub_date"),
}


@login_required(login_url='/admin/login/?next=/admin/')
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


class SearchResults(LoginRequiredMixin, ListView):
    login_url = '/admin/login/?next=/admin/'
    template_name = 'search.html'
    model = Feed
    context_object_name = "page_obj"

    def get_queryset(self):
        query = self.request.GET.get("q")
        return Feed.objects.filter(Q(title__icontains=query) | Q(description__icontains=query))
