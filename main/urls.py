from django.urls import path
from . import views

urlpatterns = [
    path('', views.explore, name='explore'),
    path('post/new/', views.post_create, name='post_create'),
    path('post/<int:pk>/', views.post_detail, name='post_detail'),
    path('profile/<str:username>/', views.profile, name='profile'),
    path('like/', views.like_post, name='like_post'),       # for AJAX
    path('comment/', views.add_comment, name='add_comment'),# AJAX
    path('signup/', views.signup, name='signup'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('edit-profile/', views.edit_profile, name='edit_profile'),
    path("get-comments/<int:post_id>/", views.get_comments, name="get_comments"),
    # path('comment/', views.add_comment, name='add_comment'),
    path('book_photoshoot/<int:profile_id>/', views.book_photoshoot, name='book_photoshoot'),
    path('delete-post/<int:pk>/', views.delete_post, name='delete_post'),




]
