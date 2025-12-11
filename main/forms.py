from django import forms
from .models import Post, Comment, PhotographerProfile
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ['title','description','location','image','video']

class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['text']

class SignUpForm(UserCreationForm):
    email = forms.EmailField(required=True)
    class Meta:
        model = User
        fields = ('username','email','password1','password2')

class PhotographerProfileForm(forms.ModelForm):
    class Meta:
        model = PhotographerProfile
        fields = ['bio','contact','portfolio_link','profile_pic']
