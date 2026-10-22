from datetime import timedelta
from tempfile import TemporaryDirectory

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from app.models import Profile, Story, UserFollow


class StoriesAppTests(TestCase):
	def test_stories_page_has_navigation_and_upload_action(self):
		user = User.objects.create_user(username='story_page_user', password='safe-pass')
		Profile.objects.create(user=user)
		self.client.force_login(user)

		response = self.client.get(reverse('stories:index'))

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Story joylash')
		self.assertContains(response, 'story-upload-input')
		self.assertContains(response, 'Faol story 24 soatdan so‘ng arxivga o‘tadi')

	def test_stories_page_only_shows_own_and_followed_users(self):
		owner = User.objects.create_user(username='story_owner')
		followed = User.objects.create_user(username='story_followed')
		other = User.objects.create_user(username='story_other')
		viewer = User.objects.create_user(username='story_viewer')
		for user in (owner, followed, other, viewer):
			Profile.objects.create(user=user)
		UserFollow.objects.create(user=followed, follower=viewer)
		UserFollow.objects.create(user=owner, follower=viewer)
		expires_at = timezone.now() + timedelta(hours=1)
		Story.objects.create(user=owner, expires_at=expires_at)
		Story.objects.create(user=followed, expires_at=expires_at)
		Story.objects.create(user=other, expires_at=expires_at)
		self.client.force_login(viewer)

		response = self.client.get(reverse('stories:index'))

		self.assertContains(response, 'story_owner')
		self.assertContains(response, 'story_followed')
		self.assertNotContains(response, 'story_other')

	def test_expired_story_moves_to_private_archive(self):
		owner = User.objects.create_user(username='archive_owner', password='safe-pass')
		other = User.objects.create_user(username='archive_other', password='safe-pass')
		Profile.objects.create(user=owner)
		Profile.objects.create(user=other)
		expired_story = Story.objects.create(
			user=owner,
			expires_at=timezone.now() - timedelta(minutes=1),
			caption='Arxivdagi xotira',
		)
		self.client.force_login(owner)

		active_response = self.client.get(reverse('stories:index'))
		archive_response = self.client.get(reverse('stories:archive'))

		self.assertNotContains(active_response, 'Arxivdagi xotira')
		self.assertContains(archive_response, 'Arxivdagi xotira')
		self.assertContains(archive_response, 'Storylar arxivda o‘chirilmaguncha saqlanadi')
		self.assertTrue(Story.objects.filter(pk=expired_story.pk).exists())

		self.client.force_login(other)
		private_archive_response = self.client.get(reverse('stories:archive'))
		self.assertNotContains(private_archive_response, 'Arxivdagi xotira')

	def test_owner_can_reopen_story_from_archive_after_24_hours(self):
		owner = User.objects.create_user(username='archive_viewer', password='safe-pass')
		Profile.objects.create(user=owner)
		story = Story.objects.create(
			user=owner,
			expires_at=timezone.now() - timedelta(minutes=1),
			caption='Eski story',
		)
		self.client.force_login(owner)

		response = self.client.get(reverse('story_viewer', kwargs={'story_id': story.pk}))

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Arxivdagi story')
		self.assertContains(response, 'Eski story')
		self.assertContains(response, reverse('stories:archive'))

	def test_create_story_saves_upload_and_opens_viewer(self):
		user = User.objects.create_user(username='story_uploader', password='safe-pass')
		Profile.objects.create(user=user)
		self.client.force_login(user)

		with TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
			response = self.client.post(reverse('stories:create'), {
				'media': SimpleUploadedFile('moment.jpg', b'image-bytes', content_type='image/jpeg'),
				'caption': 'Bugungi lahza',
			})
			story = Story.objects.get(user=user)

		self.assertRedirects(
			response,
			reverse('story_viewer', kwargs={'story_id': story.pk}),
			fetch_redirect_response=False,
		)
		self.assertEqual(story.caption, 'Bugungi lahza')
		self.assertEqual(story.media_type, 'image')
		self.assertGreater(story.expires_at, timezone.now())

	def test_guest_is_asked_to_log_in_before_creating_story(self):
		response = self.client.post(reverse('stories:create'))

		self.assertRedirects(
			response,
			f"{reverse('login')}?next={reverse('stories:create')}",
			fetch_redirect_response=False,
		)
