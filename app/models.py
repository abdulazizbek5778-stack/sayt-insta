from django.conf import settings
from django.core.validators import FileExtensionValidator
from django.db import models
from django.utils import timezone


class Profile(models.Model):
	user = models.OneToOneField(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name='profile',
	)
	bio = models.CharField(max_length=160, blank=True)
	phone = models.CharField(max_length=32, blank=True)
	avatar_url = models.URLField(blank=True)
	avatar = models.FileField(
		upload_to='avatars/',
		blank=True,
		validators=[FileExtensionValidator(['jpg', 'jpeg', 'png', 'gif', 'webp'])],
	)

	def __str__(self):
		return f'{self.user.username} profile'


class Post(models.Model):
	user = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name='posts',
		verbose_name='Muallif',
	)
	title = models.CharField(max_length=255, verbose_name='Sarlavha')
	desc = models.TextField(blank=True, verbose_name='Izoh')
	img = models.FileField(
		upload_to='posts/images/',
		blank=True,
		null=True,
		validators=[FileExtensionValidator(['jpg', 'jpeg', 'png', 'gif', 'webp'])],
		verbose_name='Rasm',
	)
	video = models.FileField(
		upload_to='posts/videos/',
		blank=True,
		null=True,
		validators=[FileExtensionValidator(['mp4', 'mov', 'avi', 'webm', 'mkv'])],
		verbose_name='Video',
	)
	created_at = models.DateTimeField(auto_now_add=True, verbose_name='Yaratilgan vaqti')
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ['-created_at']
		verbose_name = 'Post'
		verbose_name_plural = 'Postlar'

	def __str__(self):
		return self.title


class PostLike(models.Model):
	post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='likes')
	user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='post_likes')
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		unique_together = ('post', 'user')
		ordering = ['-created_at']

	def __str__(self):
		return f'{self.user.username} likes {self.post.title}'


class PostComment(models.Model):
	post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
	user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='post_comments')
	body = models.TextField(max_length=500)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['created_at']

	def __str__(self):
		return f'{self.user.username}: {self.body[:30]}'


class UserFollow(models.Model):
	user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='followers')
	follower = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='following')
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		unique_together = ('user', 'follower')
		ordering = ['-created_at']

	def __str__(self):
		return f'{self.follower.username} follows {self.user.username}'


class ChatPresence(models.Model):
	user = models.OneToOneField(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name='chat_presence',
	)
	last_seen = models.DateTimeField()


class ChatMessage(models.Model):
	sender = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name='sent_chat_messages',
	)
	recipient = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name='received_chat_messages',
	)
	body = models.CharField(max_length=1000)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['created_at', 'id']
		constraints = [
			models.CheckConstraint(
				condition=~models.Q(sender=models.F('recipient')),
				name='chat_message_users_differ',
			),
		]

	def __str__(self):
		return f'{self.sender} → {self.recipient}: {self.body[:30]}'


class Story(models.Model):
	user = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name='stories',
	)
	media = models.FileField(
		upload_to='stories/',
		blank=True,
		null=True,
		validators=[FileExtensionValidator(['jpg', 'jpeg', 'png', 'gif', 'webp', 'mp4', 'mov', 'webm'])],
	)
	media_type = models.CharField(
		max_length=20,
		choices=[('image', 'Image'), ('video', 'Video')],
		default='image',
	)
	caption = models.CharField(max_length=220, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)
	expires_at = models.DateTimeField()
	is_deleted = models.BooleanField(default=False)

	class Meta:
		ordering = ['-created_at']

	@property
	def is_expired(self):
		return self.expires_at <= timezone.now()

	def __str__(self):
		return f'{self.user.username} story ({self.media_type})'


class StoryView(models.Model):
	story = models.ForeignKey(Story, on_delete=models.CASCADE, related_name='views')
	user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='story_views')
	viewed_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		unique_together = ('story', 'user')
		ordering = ['-viewed_at']

	def __str__(self):
		return f'{self.user.username} viewed {self.story_id}'
