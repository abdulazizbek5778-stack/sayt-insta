import json
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import ObjectDoesNotExist
from django.core.paginator import Paginator
from django.db.models import Case, IntegerField, Q, When
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_GET, require_http_methods

from .forms import PostForm, ProfileForm, RegisterForm, StoryForm
from .models import ChatMessage, ChatPresence, Post, PostComment, PostLike, Profile, Story, StoryView, UserFollow


def _redirect_to_next(request, fallback='home'):
	next_url = request.POST.get('next', '')
	if next_url and url_has_allowed_host_and_scheme(
		next_url,
		allowed_hosts={request.get_host()},
		require_https=request.is_secure(),
	):
		return redirect(next_url)
	return redirect(fallback)


def home(request):
	liked_post_ids = set()
	followed_user_ids = set()
	stories = Story.objects.select_related('user', 'user__profile').filter(expires_at__gt=timezone.now(), is_deleted=False)
	seen_story_ids = set()
	if request.user.is_authenticated:
		liked_post_ids = set(PostLike.objects.filter(user=request.user).values_list('post_id', flat=True))
		followed_user_ids = set(UserFollow.objects.filter(follower=request.user).values_list('user_id', flat=True))
		seen_story_ids = set(StoryView.objects.filter(user=request.user).values_list('story_id', flat=True))
		stories = stories.filter(user_id__in=followed_user_ids | {request.user.pk})
	posts = Post.objects.select_related('user', 'user__profile').prefetch_related(
		'comments__user',
		'comments__user__profile',
		'likes',
		'comments',
	)
	if followed_user_ids:
		posts = posts.order_by(
			Case(
				When(user_id__in=followed_user_ids, then=0),
				default=1,
				output_field=IntegerField(),
			),
			'-created_at',
		)
	total_posts = posts.count()
	page = Paginator(posts, 10).get_page(request.GET.get('page'))
	return render(request, 'app/home.html', {
		'posts': page,
		'page_obj': page,
		'total_posts': total_posts,
		'liked_post_ids': list(liked_post_ids),
		'followed_user_ids': list(followed_user_ids),
		'stories': stories[:20],
		'selected_story_ids': list(seen_story_ids),
		'story_form': StoryForm(),
	})


@require_GET
def search(request):
	query = request.GET.get('q', '').strip()
	if len(query) > 100:
		return JsonResponse({'error': 'Qidiruv 100 belgidan oshmasligi kerak.'}, status=400)
	results = []
	if query:
		users = User.objects.filter(
			Q(username__icontains=query)
			| Q(first_name__icontains=query)
			| Q(last_name__icontains=query)
		).order_by('username')[:5]
		results.extend({
			'type': 'user',
			'title': user.get_full_name().strip() or user.username,
			'meta': f'@{user.username}',
			'url': reverse('user_profile', kwargs={'username': user.username}),
		} for user in users)

		posts = Post.objects.filter(
			Q(title__icontains=query)
			| Q(desc__icontains=query)
			| Q(user__username__icontains=query)
		).select_related('user').order_by('-created_at')[:5]
		results.extend({
			'type': 'post',
			'title': post.title,
			'meta': f'Post · @{post.user.username}',
			'url': f"{reverse('user_profile', kwargs={'username': post.user.username})}#post-{post.pk}",
		} for post in posts)
	return JsonResponse({'results': results})


def chat_page(request):
	total_users = User.objects.count()
	online_count = 0
	if request.user.is_authenticated:
		now = timezone.now()
		ChatPresence.objects.update_or_create(user=request.user, defaults={'last_seen': now})
		online_count = ChatPresence.objects.filter(last_seen__gte=now - timedelta(seconds=60)).count()
	return render(request, 'app/chat.html', {
		'total_users': total_users,
		'online_count': online_count,
	})


@login_required
@require_GET
def chat_contacts(request):
	now = timezone.now()
	ChatPresence.objects.update_or_create(user=request.user, defaults={'last_seen': now})
	users = User.objects.exclude(pk=request.user.pk).select_related('profile', 'chat_presence').order_by('username')[:100]
	contacts = []
	for user in users:
		try:
			profile = user.profile
			avatar_url = profile.avatar.url if profile.avatar else profile.avatar_url
		except ObjectDoesNotExist:
			avatar_url = ''
		presence = getattr(user, 'chat_presence', None)
		contacts.append({
			'id': user.pk,
			'username': user.username,
			'name': user.get_full_name().strip() or user.username,
			'avatar_url': avatar_url,
			'is_online': bool(presence and presence.last_seen >= now - timedelta(seconds=60)),
		})
	return JsonResponse({'contacts': contacts})


@login_required
@require_http_methods(['GET', 'POST'])
def chat_messages(request, user_id):
	recipient = get_object_or_404(User, pk=user_id)
	if recipient == request.user:
		return JsonResponse({'error': 'O‘zingizga xabar yubora olmaysiz.'}, status=400)

	conversation = ChatMessage.objects.filter(
		sender_id=request.user.pk,
		recipient_id=recipient.pk,
	) | ChatMessage.objects.filter(
		sender_id=recipient.pk,
		recipient_id=request.user.pk,
	)

	if request.method == 'GET':
		after = request.GET.get('after')
		if after is not None:
			try:
				after_id = int(after)
			except ValueError:
				return JsonResponse({'error': 'Xabar belgisi noto‘g‘ri.'}, status=400)
			messages_qs = conversation.filter(pk__gt=after_id).order_by('pk')[:100]
		else:
			messages_qs = conversation.order_by('-pk')[:50]
			messages_qs = reversed(list(messages_qs))
		return JsonResponse({
			'messages': [
				{
					'id': message.pk,
					'sender_id': message.sender_id,
					'body': message.body,
					'created_at': message.created_at.isoformat(),
				}
				for message in messages_qs
			],
		})

	try:
		payload = json.loads(request.body)
	except json.JSONDecodeError:
		return JsonResponse({'error': 'Xabar formati noto‘g‘ri.'}, status=400)
	body = payload.get('body', '').strip() if isinstance(payload, dict) and isinstance(payload.get('body', ''), str) else ''
	if not body:
		return JsonResponse({'error': 'Xabar matnini kiriting.'}, status=400)
	if len(body) > 1000:
		return JsonResponse({'error': 'Xabar 1000 belgidan oshmasligi kerak.'}, status=400)

	message = ChatMessage.objects.create(sender=request.user, recipient=recipient, body=body)
	return JsonResponse({
		'message': {
			'id': message.pk,
			'sender_id': message.sender_id,
			'body': message.body,
			'created_at': message.created_at.isoformat(),
		},
	}, status=201)


@login_required
@require_http_methods(['POST'])
def create_story(request):
	form = StoryForm(request.POST, request.FILES)
	if form.is_valid():
		story = form.save(commit=False)
		story.user = request.user
		story.expires_at = timezone.now() + timedelta(hours=24)
		story.media_type = 'video' if getattr(story.media, 'name', '').lower().endswith(('.mp4', '.mov', '.webm', '.avi', '.mkv')) else 'image'
		story.save()
		messages.success(request, 'Story yaratildi.')
		return redirect('story_viewer', story_id=story.pk)
	messages.error(request, 'Story yuklashda xatolik yuz berdi.')
	return redirect('home')


@login_required
@require_http_methods(['POST'])
def delete_story(request, pk):
	story = get_object_or_404(Story, pk=pk, user=request.user)
	story.is_deleted = True
	story.save(update_fields=['is_deleted'])
	messages.success(request, 'Story o\'chirildi.')
	return redirect('home')


@login_required
@require_GET
def story_viewer(request, story_id):
	now = timezone.now()
	followed_user_ids = UserFollow.objects.filter(
		follower=request.user,
	).values_list('user_id', flat=True)
	available_stories = Story.objects.filter(
		is_deleted=False,
	).filter(
		Q(expires_at__gt=now, user_id__in=followed_user_ids)
		| Q(expires_at__gt=now, user=request.user)
		| Q(expires_at__lte=now, user=request.user)
	).select_related('user', 'user__profile')
	story = get_object_or_404(available_stories, pk=story_id)
	is_archived_story = story.expires_at <= now
	if not is_archived_story:
		StoryView.objects.get_or_create(story=story, user=request.user)
	story_items = available_stories.order_by('-created_at')
	story_list = list(story_items)
	story_index = story_list.index(story) if story in story_list else 0
	prev_story_id = story_list[story_index - 1].id if story_index > 0 else None
	next_story_id = story_list[story_index + 1].id if story_index + 1 < len(story_list) else None
	return render(request, 'app/story_viewer.html', {
		'story': story,
		'story_list': story_list,
		'story_index': story_index,
		'prev_story_id': prev_story_id,
		'next_story_id': next_story_id,
		'is_archived_story': is_archived_story,
	})


def pricing(request):
	plans = [
		{
			'name': 'Boshlang’ich',
			'price': '0',
			'currency': 'so\'m',
			'badge': 'Bepul',
			'features': [
				'Asosiy profil',
				'1 ta post yaratish',
				'Umumiy lenta ko\'rishi',
				'Basic izohlar',
			],
			'featured': False,
		},
		{
			'name': 'Standart',
			'price': '149000',
			'currency': 'so\'m',
			'badge': 'Eng ommabop',
			'features': [
				'Cheksiz postlar',
				'Premium media yuklash',
				'Kuzatuvchilik va analitika',
				'Oldindan ko\'rilgan statistikalar',
			],
			'featured': True,
		},
		{
			'name': 'Premium',
			'price': '299000',
			'currency': 'so\'m',
			'badge': 'Biznes',
			'features': [
				'Barcha standart imkoniyatlar',
				'Prioritet ko\'rsatish',
				'Katta auditoriya',
				'Maxsus yordamlash va konsultatsiya',
			],
			'featured': False,
		},
	]
	return render(request, 'app/pricing.html', {'plans': plans})


def profile(request, username=None):
	if username is None:
		if not request.user.is_authenticated:
			return redirect_to_login(request.get_full_path(), login_url=reverse('login'))
		profile_user = request.user
	else:
		profile_user = get_object_or_404(User, username=username)

	user_profile, _ = Profile.objects.get_or_create(user=profile_user)
	is_owner = request.user.is_authenticated and profile_user.pk == request.user.pk
	post_form = PostForm()
	if is_owner and request.method == 'POST':
		post_form = PostForm(request.POST, request.FILES)
		if post_form.is_valid():
			new_post = post_form.save(commit=False)
			new_post.user = request.user
			new_post.save()
			messages.success(request, 'Post muvaffaqiyatli ulashildi! ✨')
			return redirect('profile')
		messages.error(request, 'Postni yuklashda xatolik yuz berdi. Formani tekshiring.')

	user_posts = Post.objects.filter(user=profile_user).select_related('user').order_by('-created_at')
	context = {
		'profile_user': profile_user,
		'username': profile_user.username,
		'email': profile_user.email if is_owner else '',
		'phone': user_profile.phone if is_owner else '',
		'bio': user_profile.bio or 'Yangi sahifamga xush kelibsiz! ✨',
		'avatar_url': user_profile.avatar.url if user_profile.avatar else user_profile.avatar_url,
		'is_owner': is_owner,
		'is_following': (
			request.user.is_authenticated
			and UserFollow.objects.filter(user=profile_user, follower=request.user).exists()
		),
		'post_form': post_form,
		'user_posts': user_posts,
		'posts_count': user_posts.count(),
		'followers_count': profile_user.followers.count(),
		'following_count': profile_user.following.count(),
	}
	return render(request, 'app/profile.html', context)


@require_GET
def user_connections(request, username, connection_type):
	profile_user = get_object_or_404(User, username=username)
	if connection_type == 'followers':
		relations = UserFollow.objects.filter(user=profile_user).select_related('follower').order_by('-created_at')
		title = 'Kuzatuvchilar'
		connection_user_field = 'follower'
	elif connection_type == 'following':
		relations = UserFollow.objects.filter(follower=profile_user).select_related('user').order_by('-created_at')
		title = 'Kuzatilayotganlar'
		connection_user_field = 'user'
	else:
		raise Http404

	page = Paginator(relations, 20).get_page(request.GET.get('page'))
	return render(request, 'app/profile_connections.html', {
		'profile_user': profile_user,
		'title': title,
		'connections': [getattr(relation, connection_user_field) for relation in page],
		'page_obj': page,
	})


@login_required
def delete_post(request, pk):
	post = get_object_or_404(Post, pk=pk, user=request.user)
	if request.method == 'POST':
		post.delete()
		messages.success(request, 'Post o‘chirildi.')
	return redirect('profile')


@login_required
@require_http_methods(['POST'])
def toggle_like(request, pk):
	post = get_object_or_404(Post, pk=pk)
	like, created = PostLike.objects.get_or_create(post=post, user=request.user)
	if not created:
		like.delete()
		messages.info(request, 'Yoqdi olib tashlandi.')
		liked = False
	else:
		messages.success(request, 'Postga yoqdi belgisi qo‘shildi.')
		liked = True
	count = post.likes.count()
	if request.headers.get('x-requested-with') == 'XMLHttpRequest':
		return JsonResponse({'liked': liked, 'likes_count': count, 'status': 'ok'})
	return _redirect_to_next(request)


def serialize_comment(comment, current_user=None, post_author_id=None):
	avatar_url = ''
	try:
		profile = getattr(comment.user, 'profile', None)
		if profile:
			avatar_url = profile.avatar.url if profile.avatar else (profile.avatar_url or '')
	except Exception:
		avatar_url = ''

	is_current_user = bool(
		current_user and current_user.is_authenticated and comment.user_id == current_user.id
	)
	is_post_author = bool(post_author_id and comment.user_id == post_author_id)
	can_delete = bool(
		current_user and current_user.is_authenticated and (
			comment.user_id == current_user.id or (post_author_id and current_user.id == post_author_id)
		)
	)

	created_dt = comment.created_at
	if timezone.is_aware(created_dt):
		local_time = timezone.localtime(created_dt)
	else:
		local_time = created_dt

	return {
		'id': comment.id,
		'user_id': comment.user.id,
		'username': comment.user.username,
		'full_name': comment.user.get_full_name().strip() or comment.user.username,
		'avatar_url': avatar_url,
		'body': comment.body,
		'created_at': comment.created_at.isoformat(),
		'created_time': local_time.strftime('%H:%M'),
		'is_current_user': is_current_user,
		'is_post_author': is_post_author,
		'can_delete': can_delete,
	}


@require_GET
def get_comments(request, pk):
	post = get_object_or_404(Post, pk=pk)
	comments_qs = post.comments.select_related('user', 'user__profile').order_by('created_at', 'id')

	after = request.GET.get('after')
	if after is not None:
		try:
			after_id = int(after)
			comments_qs = comments_qs.filter(pk__gt=after_id)
		except ValueError:
			return JsonResponse({'status': 'error', 'message': 'Noto‘g‘ri parametr.'}, status=400)

	comments_data = [
		serialize_comment(comment, current_user=request.user, post_author_id=post.user_id)
		for comment in comments_qs
	]

	return JsonResponse({
		'status': 'ok',
		'comments': comments_data,
		'comments_count': post.comments.count(),
	})


@login_required
@require_http_methods(['POST'])
def add_comment(request, pk):
	post = get_object_or_404(Post, pk=pk)
	body = ''
	if request.content_type == 'application/json':
		try:
			payload = json.loads(request.body)
			body = payload.get('body', '').strip() if isinstance(payload, dict) else ''
		except json.JSONDecodeError:
			body = ''
	else:
		body = (request.POST.get('body') or '').strip()

	is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.content_type == 'application/json'

	if body:
		comment = PostComment.objects.create(post=post, user=request.user, body=body[:500])
		messages.success(request, 'Izoh qo‘shildi.')
		if is_ajax:
			return JsonResponse({
				'status': 'ok',
				'comment': serialize_comment(comment, current_user=request.user, post_author_id=post.user_id),
				'comments_count': post.comments.count(),
			})
	else:
		messages.error(request, 'Izoh matni bo‘sh bo‘lishi mumkin emas.')
		if is_ajax:
			return JsonResponse({'status': 'error', 'message': 'Izoh bo‘sh bo‘lishi mumkin emas.'}, status=400)

	return _redirect_to_next(request)


@login_required
@require_http_methods(['POST'])
def delete_comment(request, pk):
	comment = get_object_or_404(PostComment, pk=pk)
	post = comment.post

	if comment.user_id != request.user.id and post.user_id != request.user.id:
		if request.headers.get('x-requested-with') == 'XMLHttpRequest':
			return JsonResponse({'status': 'error', 'message': 'O‘chirish huquqingiz yo‘q.'}, status=403)
		messages.error(request, 'Bu izohni o‘chirish huquqingiz yo‘q.')
		return redirect('home')

	comment.delete()
	if request.headers.get('x-requested-with') == 'XMLHttpRequest':
		return JsonResponse({
			'status': 'ok',
			'deleted_id': pk,
			'comments_count': post.comments.count(),
		})

	messages.success(request, 'Izoh o‘chirildi.')
	return _redirect_to_next(request)


@login_required
@require_http_methods(['POST'])
def toggle_follow(request, username):
	target_user = get_object_or_404(User, username=username)
	if request.user == target_user:
		messages.info(request, 'O‘zingizni kuzatib bo‘lmaydi.')
		if request.headers.get('x-requested-with') == 'XMLHttpRequest':
			return JsonResponse({'status': 'error', 'message': 'O‘zingizni kuzatib bo‘lmaydi.'}, status=400)
		return _redirect_to_next(request)
	follow, created = UserFollow.objects.get_or_create(user=target_user, follower=request.user)
	if not created:
		follow.delete()
		messages.info(request, f'{target_user.username} kuzatuvchilardan olib tashlandi.')
		following = False
	else:
		messages.success(request, f'{target_user.username} kuzatilmoqda.')
		following = True
	if request.headers.get('x-requested-with') == 'XMLHttpRequest':
		return JsonResponse({'status': 'ok', 'following': following, 'followers_count': target_user.followers.count()})
	return _redirect_to_next(request)


def register(request):
	if request.user.is_authenticated:
		return redirect('profile')

	form = RegisterForm(request.POST or None)
	if request.method == 'POST' and form.is_valid():
		user = form.save()
		Profile.objects.create(
			user=user,
			phone=form.cleaned_data['phone'],
			bio=form.cleaned_data['bio'],
			avatar=form.cleaned_data['avatar'],
		)
		login(request, user, backend='django.contrib.auth.backends.ModelBackend')
		messages.success(request, 'Profilingiz tayyor! Xush kelibsiz.')
		return redirect('profile')

	return render(request, 'app/register.html', {'form': form})


@login_required
def edit_profile(request):
	user_profile, _ = Profile.objects.get_or_create(user=request.user)
	form = ProfileForm(request.POST or None, request.FILES or None, instance=user_profile)
	if request.method == 'POST' and form.is_valid():
		form.save()
		messages.success(request, 'Profilingiz yangilandi.')
		return redirect('profile')
	return render(request, 'app/edit_profile.html', {'form': form, 'profile': user_profile})
