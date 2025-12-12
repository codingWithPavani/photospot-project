# main/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth import login, authenticate, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseBadRequest
from django.utils import timezone

from django.db.models import Count, F, ExpressionWrapper, IntegerField, Q

from .models import Post, Location, Like, Comment, PhotographerProfile
from .forms import PostForm, CommentForm, SignUpForm, PhotographerProfileForm

# -----------------------------
# Helper / Home views
# -----------------------------
# def explore(request):
#     """
#     Home / Explore page:
#     - optional search by location name, title, description or city
#     - shows recent posts
#     - shows a small trending panel (annotated by likes & comments score)
#     """
#     q = request.GET.get('q', '').strip()
#     posts = Post.objects.select_related('uploader', 'location').all()

#     if q:
#         posts = posts.filter(
#             Q(location__name__icontains=q) |
#             Q(location__city__icontains=q) |
#             Q(title__icontains=q) |
#             Q(description__icontains=q)
#         )

#     posts = posts.order_by('-created_at')

#     # Trending calculation:
#     # score = 2 * likes + 1 * comments (recent posts are favored in tie by created_at)
#     trending = (
#         Post.objects
#             .annotate(like_count=Count('likes', distinct=True), comment_count=Count('comments', distinct=True))
#             .annotate(score=ExpressionWrapper(F('like_count') * 2 + F('comment_count'), output_field=IntegerField()))
#             .order_by('-score', '-created_at')[:6]
#     )

#     context = {
#         'posts': posts,
#         'trending': trending,
#         'query': q,
#         'now': timezone.now(),
#     }
#     return render(request, 'main/explore.html', context)





def explore(request):
    q = request.GET.get('q', '').strip()

    posts = (
        Post.objects
        .select_related('uploader', 'location')
        .annotate(
            like_count=Count('likes', distinct=True),
            comment_count=Count('comments', distinct=True)
        )
    )

    if q:
        posts = posts.filter(
            Q(location__name__icontains=q) |
            Q(location__city__icontains=q) |
            Q(title__icontains=q) |
            Q(description__icontains=q)
        )

    posts = posts.order_by('-created_at')

    trending = (
        Post.objects
        .annotate(
            like_count=Count('likes', distinct=True),
            comment_count=Count('comments', distinct=True),
            score=ExpressionWrapper(
                F('like_count') * 2 + F('comment_count'),
                output_field=IntegerField()
            )
        )
        .order_by('-score', '-created_at')[:6]
    )

    return render(request, 'main/explore.html', {
        'posts': posts,
        'trending': trending,
        'query': q
    })




# -----------------------------
# Post create / detail
# -----------------------------
@login_required
def post_create(request):
    """
    Create a new Post (image/video + location).
    Make sure the form in template uses enctype="multipart/form-data".
    """
    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            p = form.save(commit=False)
            p.uploader = request.user
            p.save()
            messages.success(request, 'Post uploaded successfully.')
            return redirect('post_detail', pk=p.pk)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = PostForm()

    return render(request, 'main/post_form.html', {'form': form})


def post_detail(request, pk):
    """
    Show a single post with comments and a comment form.
    """
    post = get_object_or_404(Post.objects.select_related('uploader', 'location'), pk=pk)
    comment_form = CommentForm()
    # Preload comments and likes count to reduce DB queries in template
    comments = post.comments.select_related('user').order_by('created_at')
    like_count = post.likes.count()
    context = {
        'post': post,
        'comment_form': comment_form,
        'comments': comments,
        'like_count': like_count,
    }
    return render(request, 'main/post_detail.html', context)


# -----------------------------
# Like / Comment endpoints (AJAX)
# -----------------------------
@login_required
def like_post(request):
    """
    Toggle like/unlike via AJAX POST.
    Expects 'post_id' in POST body.
    Returns JSON: { 'liked': bool, 'count': int }
    """
    if request.method != 'POST':
        return HttpResponseBadRequest('Invalid request method.')

    post_id = request.POST.get('post_id')
    if not post_id:
        return JsonResponse({'error': 'post_id required'}, status=400)

    post = get_object_or_404(Post, id=post_id)

    like, created = Like.objects.get_or_create(user=request.user, post=post)
    if not created:
        # Like existed: remove it (toggle off)
        like.delete()
        liked = False
    else:
        liked = True

    count = post.likes.count()
    return JsonResponse({'liked': liked, 'count': count})


# @login_required
# def add_comment(request):
#     """
#     Add a comment via AJAX POST.
#     Expects 'post_id' and 'text' in POST.
#     Returns JSON with comment details for client rendering.
#     """
#     if request.method != 'POST':
#         return HttpResponseBadRequest('Invalid request method.')

#     post_id = request.POST.get('post_id')
#     text = request.POST.get('text', '').strip()

#     if not post_id or not text:
#         return JsonResponse({'error': 'post_id and text are required.'}, status=400)

#     post = get_object_or_404(Post, id=post_id)
#     comment = Comment.objects.create(user=request.user, post=post, text=text)

#     return JsonResponse({
#         'user': request.user.username,
#         'text': comment.text,
#         'created': comment.created_at.strftime('%Y-%m-%d %H:%M'),
#         'post_id': post_id
#     })






import json
from django.views.decorators.csrf import csrf_exempt

# @login_required
# def add_comment(request):
#     """
#     Add a comment via AJAX POST (supports JSON).
#     """
#     if request.method != 'POST':
#         return HttpResponseBadRequest('Invalid request method.')

#     # If JSON body → load it
#     if request.headers.get("Content-Type") == "application/json":
#         data = json.loads(request.body)
#         post_id = data.get("post_id")
#         text = data.get("comment", "").strip()
#     else:
#         # Form-data fallback
#         post_id = request.POST.get("post_id")
#         text = request.POST.get("comment", "").strip()

#     if not post_id or not text:
#         return JsonResponse({"error": "post_id and comment are required."}, status=400)

#     post = get_object_or_404(Post, id=post_id)

#     comment = Comment.objects.create(
#         user=request.user,
#         post=post,
#         text=text
#     )

#     return JsonResponse({
#         "user": request.user.username,
#         "comment": comment.text,
#         "created": comment.created_at.strftime("%d %b %Y %H:%M")
#     })





from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404
import json
from .models import Post, Comment  # Adjust import based on your app

@login_required
def add_comment(request):
    """
    Add a comment via AJAX POST (supports JSON and form-data).
    Returns JSON with new comment info and updated comment count.
    """
    if request.method != "POST":
        return HttpResponseBadRequest("Invalid request method.")

    # Parse data from JSON or form-data
    if request.headers.get("Content-Type") == "application/json":
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON."}, status=400)
        post_id = data.get("post_id")
        text = data.get("comment", "").strip()
    else:
        post_id = request.POST.get("post_id")
        text = request.POST.get("comment", "").strip()

    # Validate inputs
    if not post_id or not text:
        return JsonResponse({"error": "post_id and comment are required."}, status=400)

    # Get the post
    post = get_object_or_404(Post, id=post_id)

    # Create the comment
    comment = Comment.objects.create(
        user=request.user,
        post=post,
        text=text
    )

    # Get updated comment count
    comment_count = post.comments.count()

    # Prepare response
    response_data = {
        "success": True,
        "user": request.user.username,
        "comment": comment.text,
        "created": comment.created_at.strftime("%d %b %Y %H:%M"),
        "comment_count": comment_count
    }

    return JsonResponse(response_data)


# -----------------------------
# User profile & auth views
# -----------------------------
def profile(request, username):
    """
    Show a user's profile and their posts.
    """
    owner = get_object_or_404(User, username=username)
    posts = owner.posts.select_related('location').order_by('-created_at')
    profile = PhotographerProfile.objects.filter(user=owner).first()
    return render(request, 'main/profile.html', {'owner': owner, 'posts': posts, 'profile': profile})


def signup(request):
    """
    Simple signup using SignUpForm (UserCreationForm extension).
    On success, logs in the user and redirects to explore.
    """
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Optionally create PhotographerProfile automatically via signals (recommended)
            login(request, user)
            messages.success(request, f'Welcome, {user.username}!')
            return redirect('explore')
        else:
            messages.error(request, 'Please fix the errors below.')
    else:
        form = SignUpForm()

    return render(request, 'main/signup.html', {'form': form})


def user_login(request):
    """
    Simple login view. For production, prefer Django's auth views.
    """
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        pwd = request.POST.get('password', '')
        user = authenticate(username=username, password=pwd)
        if user:
            login(request, user)
            return redirect('explore')
        else:
            messages.error(request, 'Invalid credentials, please try again.')
    return render(request, 'main/login.html')


def user_logout(request):
    """
    Logout the user and redirect to login page.
    """
    auth_logout(request)
    return redirect('login')





from django.contrib.auth.decorators import login_required

@login_required
def edit_profile(request):
    profile = PhotographerProfile.objects.get_or_create(user=request.user)[0]

    if request.method == "POST":
        profile.bio = request.POST.get("bio")
        profile.contact = request.POST.get("contact")
        profile.portfolio_link = request.POST.get("portfolio_link")

        if 'profile_pic' in request.FILES:
            profile.profile_pic = request.FILES['profile_pic']

        profile.save()
        return redirect('profile', username=request.user.username)

    return render(request, 'main/edit_profile.html', {"profile": profile})






from django.http import JsonResponse

# def get_comments(request, post_id):
#     post = get_object_or_404(Post, id=post_id)
#     comments = post.comments.select_related('user').order_by('created_at')

#     return JsonResponse({
#         "comments": [
#             {
#                 "user": c.user.username,
#                 "text": c.text,
#                 "created": c.created_at.strftime("%d %b %Y %H:%M")
#             }
#             for c in comments
#         ]
#     })











def get_comments(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    comments = post.comments.select_related('user').order_by('created_at')

    return JsonResponse({
        "comments": [
            {
                "user": c.user.username,
                "text": c.text,
                "created": c.created_at.strftime("%d %b %Y %H:%M"),
                "profile_pic_url": c.user.photographerprofile.profile_pic.url if hasattr(c.user, 'photographerprofile') and c.user.photographerprofile.profile_pic else None
            }
            for c in comments
        ]
    })







from django.shortcuts import render, redirect, get_object_or_404
from django.core.mail import send_mail
from django.contrib import messages
from django.conf import settings
from .models import PhotographerProfile  # Assuming your profile model is named Profile

def book_photoshoot(request, profile_id):
    profile = get_object_or_404(PhotographerProfile, id=profile_id)

    if request.method == 'POST':
        date = request.POST.get('date')
        event_type = request.POST.get('event_type')
        message_text = request.POST.get('message')

        # Compose email
        subject = f"New Photoshoot Booking from {request.user.username}"
        message_body = f"""
        You have received a new booking request:

        Client: {request.user.username}
        Email: {request.user.email}
        Date: {date}
        Event Type: {event_type}
        Message: {message_text}
        """

        recipient_list = [profile.user.email]  # Assuming profile has OneToOneField to User
        send_mail(subject, message_body, settings.DEFAULT_FROM_EMAIL, recipient_list)
        

        # main/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth import login, authenticate, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseBadRequest
from django.utils import timezone

from django.db.models import Count, F, ExpressionWrapper, IntegerField, Q

from .models import Post, Location, Like, Comment, PhotographerProfile
from .forms import PostForm, CommentForm, SignUpForm, PhotographerProfileForm

# -----------------------------
# Helper / Home views
# -----------------------------
# def explore(request):
#     """
#     Home / Explore page:
#     - optional search by location name, title, description or city
#     - shows recent posts
#     - shows a small trending panel (annotated by likes & comments score)
#     """
#     q = request.GET.get('q', '').strip()
#     posts = Post.objects.select_related('uploader', 'location').all()

#     if q:
#         posts = posts.filter(
#             Q(location__name__icontains=q) |
#             Q(location__city__icontains=q) |
#             Q(title__icontains=q) |
#             Q(description__icontains=q)
#         )

#     posts = posts.order_by('-created_at')

#     # Trending calculation:
#     # score = 2 * likes + 1 * comments (recent posts are favored in tie by created_at)
#     trending = (
#         Post.objects
#             .annotate(like_count=Count('likes', distinct=True), comment_count=Count('comments', distinct=True))
#             .annotate(score=ExpressionWrapper(F('like_count') * 2 + F('comment_count'), output_field=IntegerField()))
#             .order_by('-score', '-created_at')[:6]
#     )

#     context = {
#         'posts': posts,
#         'trending': trending,
#         'query': q,
#         'now': timezone.now(),
#     }
#     return render(request, 'main/explore.html', context)





def explore(request):
    q = request.GET.get('q', '').strip()

    posts = (
        Post.objects
        .select_related('uploader', 'location')
        .annotate(
            like_count=Count('likes', distinct=True),
            comment_count=Count('comments', distinct=True)
        )
    )

    if q:
        posts = posts.filter(
            Q(location__name__icontains=q) |
            Q(location__city__icontains=q) |
            Q(title__icontains=q) |
            Q(description__icontains=q)
        )

    posts = posts.order_by('-created_at')

    trending = (
        Post.objects
        .annotate(
            like_count=Count('likes', distinct=True),
            comment_count=Count('comments', distinct=True),
            score=ExpressionWrapper(
                F('like_count') * 2 + F('comment_count'),
                output_field=IntegerField()
            )
        )
        .order_by('-score', '-created_at')[:6]
    )

    return render(request, 'main/explore.html', {
        'posts': posts,
        'trending': trending,
        'query': q
    })




# -----------------------------
# Post create / detail
# -----------------------------
@login_required
def post_create(request):
    """
    Create a new Post (image/video + location).
    Make sure the form in template uses enctype="multipart/form-data".
    """
    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            p = form.save(commit=False)
            p.uploader = request.user
            p.save()
            messages.success(request, 'Post uploaded successfully.')
            # return redirect('post_detail', pk=p.pk)
            return redirect('profile', username=request.user.username)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = PostForm()

    return render(request, 'main/post_form.html', {'form': form})


def post_detail(request, pk):
    """
    Show a single post with comments and a comment form.
    """
    post = get_object_or_404(Post.objects.select_related('uploader', 'location'), pk=pk)
    comment_form = CommentForm()
    # Preload comments and likes count to reduce DB queries in template
    comments = post.comments.select_related('user').order_by('created_at')
    like_count = post.likes.count()
    context = {
        'post': post,
        'comment_form': comment_form,
        'comments': comments,
        'like_count': like_count,
    }
    return render(request, 'main/post_detail.html', context)


# -----------------------------
# Like / Comment endpoints (AJAX)
# -----------------------------
@login_required
def like_post(request):
    """
    Toggle like/unlike via AJAX POST.
    Expects 'post_id' in POST body.
    Returns JSON: { 'liked': bool, 'count': int }
    """
    if request.method != 'POST':
        return HttpResponseBadRequest('Invalid request method.')

    post_id = request.POST.get('post_id')
    if not post_id:
        return JsonResponse({'error': 'post_id required'}, status=400)

    post = get_object_or_404(Post, id=post_id)

    like, created = Like.objects.get_or_create(user=request.user, post=post)
    if not created:
        # Like existed: remove it (toggle off)
        like.delete()
        liked = False
    else:
        liked = True

    count = post.likes.count()
    return JsonResponse({'liked': liked, 'count': count})


# @login_required
# def add_comment(request):
#     """
#     Add a comment via AJAX POST.
#     Expects 'post_id' and 'text' in POST.
#     Returns JSON with comment details for client rendering.
#     """
#     if request.method != 'POST':
#         return HttpResponseBadRequest('Invalid request method.')

#     post_id = request.POST.get('post_id')
#     text = request.POST.get('text', '').strip()

#     if not post_id or not text:
#         return JsonResponse({'error': 'post_id and text are required.'}, status=400)

#     post = get_object_or_404(Post, id=post_id)
#     comment = Comment.objects.create(user=request.user, post=post, text=text)

#     return JsonResponse({
#         'user': request.user.username,
#         'text': comment.text,
#         'created': comment.created_at.strftime('%Y-%m-%d %H:%M'),
#         'post_id': post_id
#     })






import json
from django.views.decorators.csrf import csrf_exempt

# @login_required
# def add_comment(request):
#     """
#     Add a comment via AJAX POST (supports JSON).
#     """
#     if request.method != 'POST':
#         return HttpResponseBadRequest('Invalid request method.')

#     # If JSON body → load it
#     if request.headers.get("Content-Type") == "application/json":
#         data = json.loads(request.body)
#         post_id = data.get("post_id")
#         text = data.get("comment", "").strip()
#     else:
#         # Form-data fallback
#         post_id = request.POST.get("post_id")
#         text = request.POST.get("comment", "").strip()

#     if not post_id or not text:
#         return JsonResponse({"error": "post_id and comment are required."}, status=400)

#     post = get_object_or_404(Post, id=post_id)

#     comment = Comment.objects.create(
#         user=request.user,
#         post=post,
#         text=text
#     )

#     return JsonResponse({
#         "user": request.user.username,
#         "comment": comment.text,
#         "created": comment.created_at.strftime("%d %b %Y %H:%M")
#     })





from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404
import json
from .models import Post, Comment  # Adjust import based on your app

# @login_required
# def add_comment(request):
#     """
#     Add a comment via AJAX POST (supports JSON and form-data).
#     Returns JSON with new comment info and updated comment count.
#     """
#     if request.method != "POST":
#         return HttpResponseBadRequest("Invalid request method.")

#     # Parse data from JSON or form-data
#     if request.headers.get("Content-Type") == "application/json":
#         try:
#             data = json.loads(request.body)
#         except json.JSONDecodeError:
#             return JsonResponse({"error": "Invalid JSON."}, status=400)
#         post_id = data.get("post_id")
#         text = data.get("comment", "").strip()
#     else:
#         post_id = request.POST.get("post_id")
#         text = request.POST.get("comment", "").strip()

#     # Validate inputs
#     if not post_id or not text:
#         return JsonResponse({"error": "post_id and comment are required."}, status=400)

#     # Get the post
#     post = get_object_or_404(Post, id=post_id)

#     # Create the comment
#     comment = Comment.objects.create(
#         user=request.user,
#         post=post,
#         text=text
#     )

#     # Get updated comment count
#     comment_count = post.comments.count()

#     # Prepare response
#     response_data = {
#         "success": True,
#         "user": request.user.username,
#         "comment": comment.text,
#         "created": comment.created_at.strftime("%d %b %Y %H:%M"),
#         "comment_count": comment_count
#     }

#     return JsonResponse(response_data)







@login_required
def add_comment(request):
    """
    Add a comment via AJAX POST (supports JSON and form-data).
    Returns JSON with new comment info + updated comment count.
    """
    if request.method != "POST":
        return HttpResponseBadRequest("Invalid request method.")

    # --- Handle JSON or Form Data ---
    if request.META.get("CONTENT_TYPE", "").startswith("application/json"):
        try:
            data = json.loads(request.body.decode("utf-8"))
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON."}, status=400)

        post_id = data.get("post_id")
        text = data.get("comment", "").strip()

    else:
        post_id = request.POST.get("post_id")
        text = request.POST.get("comment", "").strip()

    # Validation
    if not post_id or not text:
        return JsonResponse({"error": "post_id and comment are required."}, status=400)

    post = get_object_or_404(Post, id=post_id)

    # Create comment
    comment = Comment.objects.create(
        user=request.user,
        post=post,
        text=text
    )

    # Updated live comment count
    comment_count = post.comments.count()

    # Response sent to frontend
    return JsonResponse({
        "success": True,
        "user": request.user.username,
        "comment": comment.text,
        "created": comment.created_at.strftime("%d %b %Y %H:%M"),
        "comment_count": comment_count
    })




# -----------------------------
# User profile & auth views
# -----------------------------
# def profile(request, username):
#     """
#     Show a user's profile and their posts.
#     """
#     owner = get_object_or_404(User, username=username)
#     posts = owner.posts.select_related('location').order_by('-created_at')
#     profile = PhotographerProfile.objects.filter(user=owner).first()
#     return render(request, 'main/profile.html', {'owner': owner, 'posts': posts, 'profile': profile})




# main/views.py (replace profile view)
from django.db.models import Count

def profile(request, username):
    """
    Show a user's profile and their posts.
    Annotate each post with like/comment counts so template can show them.
    """
    owner = get_object_or_404(User, username=username)

    posts = (
        owner.posts
        .select_related('location')
        .annotate(
            likes_count=Count('likes', distinct=True),
            comments_count=Count('comments', distinct=True)
        )
        .order_by('-created_at')
    )

    profile = PhotographerProfile.objects.filter(user=owner).first()
    return render(request, 'main/profile.html', {'owner': owner, 'posts': posts, 'profile': profile})



def signup(request):
    """
    Simple signup using SignUpForm (UserCreationForm extension).
    On success, logs in the user and redirects to explore.
    """
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Optionally create PhotographerProfile automatically via signals (recommended)
            login(request, user)
            messages.success(request, f'Welcome, {user.username}!')
            return redirect('explore')
        else:
            messages.error(request, 'Please fix the errors below.')
    else:
        form = SignUpForm()

    return render(request, 'main/signup.html', {'form': form})


def user_login(request):
    """
    Simple login view. For production, prefer Django's auth views.
    """
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        pwd = request.POST.get('password', '')
        user = authenticate(username=username, password=pwd)
        if user:
            login(request, user)
            return redirect('explore')
        else:
            messages.error(request, 'Invalid credentials, please try again.')
    return render(request, 'main/login.html')


def user_logout(request):
    """
    Logout the user and redirect to login page.
    """
    auth_logout(request)
    return redirect('login')





from django.contrib.auth.decorators import login_required

@login_required
def edit_profile(request):
    profile = PhotographerProfile.objects.get_or_create(user=request.user)[0]

    if request.method == "POST":
        profile.bio = request.POST.get("bio")
        profile.contact = request.POST.get("contact")
        profile.portfolio_link = request.POST.get("portfolio_link")

        if 'profile_pic' in request.FILES:
            profile.profile_pic = request.FILES['profile_pic']

        profile.save()
        return redirect('profile', username=request.user.username)

    return render(request, 'main/edit_profile.html', {"profile": profile})






from django.http import JsonResponse

# def get_comments(request, post_id):
#     post = get_object_or_404(Post, id=post_id)
#     comments = post.comments.select_related('user').order_by('created_at')

#     return JsonResponse({
#         "comments": [
#             {
#                 "user": c.user.username,
#                 "text": c.text,
#                 "created": c.created_at.strftime("%d %b %Y %H:%M")
#             }
#             for c in comments
#         ]
#     })











def get_comments(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    comments = post.comments.select_related('user').order_by('created_at')
    like_count = post.likes.count()  # <-- fetch like count from DB
    comment_count = comments.count()


    return JsonResponse({
        "like_count": like_count,
        "comment_count": comment_count,
        "comments": [
            {
                "user": c.user.username,
                "text": c.text,
                "created": c.created_at.strftime("%d %b %Y %H:%M"),
                "profile_pic_url": c.user.photographerprofile.profile_pic.url if hasattr(c.user, 'photographerprofile') and c.user.photographerprofile.profile_pic else None
            }
            for c in comments
        ]
    })







from django.shortcuts import render, redirect, get_object_or_404
from django.core.mail import send_mail
from django.contrib import messages
from django.conf import settings
from .models import PhotographerProfile  # Assuming your profile model is named Profile

# def book_photoshoot(request, profile_id):
#     profile = get_object_or_404(PhotographerProfile, id=profile_id)

#     if request.method == 'POST':
#         date = request.POST.get('date')
#         event_type = request.POST.get('event_type')
#         message_text = request.POST.get('message')

#         # Compose email
#         subject = f"New Photoshoot Booking from {request.user.username}"
#         message_body = f"""
#         You have received a new booking request:

#         Client: {request.user.username}
#         Email: {request.user.email}
#         Date: {date}
#         Event Type: {event_type}
#         Message: {message_text}
#         """

#         recipient_list = [profile.user.email]  # Assuming profile has OneToOneField to User
#         send_mail(subject, message_body, settings.DEFAULT_FROM_EMAIL, recipient_list)

#         messages.success(request, "Your booking request has been sent successfully!")
#         return redirect('profile', username=profile.user.username)

  


#     return redirect('profile', username=profile.user.username)







from django.core.mail import send_mail
from django.conf import settings
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from .models import PhotographerProfile

def book_photoshoot(request, profile_id):
    profile = get_object_or_404(PhotographerProfile, id=profile_id)

    if request.method == 'POST':
        date = request.POST.get('date')
        event_type = request.POST.get('event_type')
        message_text = request.POST.get('message')

        # fallback if user email is empty
        sender_email = request.user.email or settings.EMAIL_HOST_USER

        subject = f"New Photoshoot Booking from {request.user.username}"

        message_body = f"""
        You have received a new booking request:

        Client: {request.user.username}
        Email: {sender_email}
        Date: {date}
        Event Type: {event_type}

        Message:
        {message_text}
        """

        recipient_list = [profile.user.email]

        # ALWAYS send from your Gmail
        send_mail(
            subject,
            message_body,
            settings.EMAIL_HOST_USER,   # FIXED
            recipient_list,
            fail_silently=False
        )

        messages.success(request, "Your booking request has been sent successfully!")
        return redirect('profile', username=profile.user.username)

    return redirect('profile', username=profile.user.username)









# from django.http import JsonResponse

# @login_required
# def delete_post(request, pk):
#     post = get_object_or_404(Post, id=pk)

#     if post.user != request.user:
#         return JsonResponse({"status": "error", "message": "Not allowed"}, status=403)

#     post.delete()
#     return JsonResponse({"status": "success"})









from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import Post

@login_required
def delete_post(request, pk):
    post = get_object_or_404(Post, id=pk)
    
    # Check uploader instead of user
    if post.uploader != request.user:
        return redirect('profile', username=request.user.username)
    
    post.delete()
    return redirect('profile', username=request.user.username)

