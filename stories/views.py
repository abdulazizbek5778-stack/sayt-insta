from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from app.forms import StoryForm
from app.models import Story, StoryView, UserFollow


def index(request):
	now = timezone.now()
	stories = Story.objects.select_related('user', 'user__profile').filter(
		expires_at__gt=now,
		is_deleted=False,
	)
	seen_story_ids = set()
	if request.user.is_authenticated:
		followed_user_ids = UserFollow.objects.filter(
			follower=request.user,
		).values_list('user_id', flat=True)
		stories = stories.filter(Q(user=request.user) | Q(user_id__in=followed_user_ids))
		seen_story_ids = set(
			StoryView.objects.filter(user=request.user).values_list('story_id', flat=True)
		)
	return render(request, 'stories/index.html', {
		'stories': stories[:100],
		'seen_story_ids': seen_story_ids,
		'is_archive': False,
	})


@login_required
def archive(request):
	stories = Story.objects.select_related('user', 'user__profile').filter(
		user=request.user,
		expires_at__lte=timezone.now(),
		is_deleted=False,
	)
	return render(request, 'stories/index.html', {
		'stories': stories[:100],
		'seen_story_ids': set(),
		'is_archive': True,
	})


@login_required
@require_http_methods(['POST'])
def create(request):
	form = StoryForm(request.POST, request.FILES)
	if not form.is_valid():
		messages.error(request, 'Story yuklanmadi. Rasm yoki video tanlang (30 MB gacha).')
		return redirect('stories:index')

	story = form.save(commit=False)
	story.user = request.user
	story.expires_at = timezone.now() + timedelta(hours=24)
	story.media_type = (
		'video'
		if getattr(story.media, 'name', '').lower().endswith(('.mp4', '.mov', '.webm'))
		else 'image'
	)
	story.save()
	messages.success(request, 'Story joylandi.')
	return redirect('story_viewer', story_id=story.pk)
