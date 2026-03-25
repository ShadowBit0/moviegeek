from django.urls import path, re_path

from moviegeeks import views

urlpatterns = [
    path('', views.index, name='index'),
    path('movie/<str:movie_id>/', views.detail, name='detail'),
    re_path(r'^genre/(?P<genre_id>[\w\s,&-]+)/$', views.genre, name='genre'),
    path('search/', views.search_for_movie, name='search_for_movie'),
    path('api/item/<str:item_id>/', views.item_detail_api, name='item_detail_api'),
]
