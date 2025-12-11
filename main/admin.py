from django.contrib import admin
from .models import Post, Location, Comment, Like, PhotographerProfile
admin.site.register([Post, Location, Comment, Like, PhotographerProfile])
