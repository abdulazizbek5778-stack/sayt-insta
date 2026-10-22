import json
from datetime import timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.test import RequestFactory
from django.contrib.sessions.middleware import SessionMiddleware
from django.utils import timezone
from allauth.socialaccount.models import SocialAccount, SocialLogin

from .adapters import GoogleSocialAccountAdapter
from .models import ChatMessage, ChatPresence, Post, Profile, Story, UserFollow


class ProfilePageTests(TestCase):
	def test_guest_is_redirected_to_login_from_own_profile(self):
		response = self.client.get(reverse('profile'))

		self.assertEqual(response.status_code, 302)
		self.assertEqual(response.url, f"{reverse('login')}?next=/profile/")

	def test_public_profile_shows_posts_without_exposing_contact_details(self):
		user = User.objects.create_user(
			username='publicuser',
			email='private@example.com',
			password='UltraSafePass938!!',
		)
		Profile.objects.create(user=user, phone='+998901112233', bio='Ommaviy bio')
		Post.objects.create(user=user, title='Ommaviy post')

		response = self.client.get(reverse('user_profile', kwargs={'username': user.username}))

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Ommaviy post')
		self.assertContains(response, 'Ommaviy bio')
		self.assertNotContains(response, 'private@example.com')
		self.assertNotContains(response, '+998901112233')
		self.assertNotContains(response, 'Yangi post qo‘shish')

	def test_profile_connection_lists_link_to_public_profiles(self):
		target = User.objects.create_user(username='profile_target')
		follower = User.objects.create_user(username='profile_follower')
		following = User.objects.create_user(username='profile_following')
		UserFollow.objects.create(user=target, follower=follower)
		UserFollow.objects.create(user=following, follower=target)

		followers_response = self.client.get(reverse(
			'user_connections',
			kwargs={'username': target.username, 'connection_type': 'followers'},
		))
		following_response = self.client.get(reverse(
			'user_connections',
			kwargs={'username': target.username, 'connection_type': 'following'},
		))

		self.assertContains(followers_response, '@profile_follower')
		self.assertContains(following_response, '@profile_following')

	def test_guest_cannot_record_story_view(self):
		user = User.objects.create_user(username='storyowner', password='UltraSafePass938!!')
		story = Story.objects.create(
			user=user,
			expires_at=timezone.now() + timedelta(hours=1),
		)

		response = self.client.get(reverse('story_viewer', kwargs={'story_id': story.pk}))

		self.assertRedirects(
			response,
			f"{reverse('login')}?next=%2Fstories%2F{story.pk}%2F",
		)

	def test_story_upload_redirects_to_story_viewer(self):
		user = User.objects.create_user(username='storycreator', password='UltraSafePass938!!')
		self.client.force_login(user)
		media = SimpleUploadedFile('story.jpg', b'image-bytes', content_type='image/jpeg')

		response = self.client.post(reverse('create_story'), {
			'media': media,
			'caption': 'Yangi story',
		})

		story = Story.objects.get(user=user)
		self.assertRedirects(
			response,
			reverse('story_viewer', kwargs={'story_id': story.pk}),
			fetch_redirect_response=False,
		)

	def test_registration_page_uses_uzbek_labels(self):
		response = self.client.get(reverse('register'))

		self.assertContains(response, 'Foydalanuvchi nomi</label>')
		self.assertContains(response, 'Email manzili</label>')
		self.assertContains(response, 'Parolni tasdiqlash</label>')
		self.assertContains(response, 'Parol kamida 8 ta belgidan iborat bo‘lsin.')
		self.assertContains(response, 'Google bilan davom etish')
		self.assertNotContains(response, 'Password confirmation')

	def test_google_login_route_is_available(self):
		self.assertEqual(reverse('google_login'), '/accounts/google/login/')

	def test_google_signup_creates_profile_and_uses_google_avatar(self):
		sociallogin = SocialLogin(
			user=User(username='', email='googleuser@example.com', first_name='Google', last_name='User'),
			account=SocialAccount(
				provider='google',
				uid='google-user-123',
				extra_data={'picture': 'https://lh3.googleusercontent.com/avatar'},
			),
		)
		request = RequestFactory().post('/accounts/google/login/callback/')
		SessionMiddleware(lambda request: None).process_request(request)
		request.session.save()

		user = GoogleSocialAccountAdapter().save_user(request, sociallogin)

		profile = Profile.objects.get(user=user)
		self.assertEqual(user.first_name, 'Google')
		self.assertEqual(user.last_name, 'User')
		self.assertEqual(profile.avatar_url, 'https://lh3.googleusercontent.com/avatar')

	def test_google_login_button_waits_for_oauth_credentials(self):
		with override_settings(GOOGLE_OAUTH_ENABLED=False):
			for url in (reverse('login'), reverse('register')):
				response = self.client.get(url)
				self.assertContains(response, 'Google bilan davom etish')
				self.assertContains(response, 'Google Cloud OAuth Client ID va Client Secret')
				self.assertContains(response, '/accounts/google/login/callback/')
				self.assertContains(response, 'disabled')

	def test_google_button_links_to_provider_when_configured(self):
		provider_settings = {
			'google': {
				'APP': {'client_id': 'test-client-id', 'secret': 'test-client-secret', 'key': ''},
				'SCOPE': ['profile', 'email'],
				'AUTH_PARAMS': {'access_type': 'online', 'prompt': 'select_account'},
				'OAUTH_PKCE_ENABLED': True,
			}
		}
		with override_settings(
			GOOGLE_OAUTH_ENABLED=True,
			SOCIALACCOUNT_PROVIDERS=provider_settings,
		):
			response = self.client.get(reverse('login'))

		self.assertContains(response, '/accounts/google/login/')
		self.assertNotContains(response, 'Google orqali kirish uchun OAuth kalitlari kerak.')

	def test_google_button_starts_provider_redirect_on_first_click(self):
		provider_settings = {
			'google': {
				'APP': {'client_id': 'test-client-id', 'secret': 'test-client-secret', 'key': ''},
				'SCOPE': ['profile', 'email'],
				'AUTH_PARAMS': {'access_type': 'online', 'prompt': 'select_account'},
				'OAUTH_PKCE_ENABLED': True,
			}
		}
		with override_settings(
			GOOGLE_OAUTH_ENABLED=True,
			SOCIALACCOUNT_PROVIDERS=provider_settings,
			SOCIALACCOUNT_LOGIN_ON_GET=True,
		):
			response = self.client.get(
				reverse('google_login'),
				HTTP_HOST='localhost',
			)

		self.assertEqual(response.status_code, 302)
		self.assertTrue(response['Location'].startswith('https://accounts.google.com/'))
		self.assertIn('redirect_uri=http%3A%2F%2Flocalhost%2Faccounts%2Fgoogle%2Flogin%2Fcallback%2F', response['Location'])
		self.assertIn('prompt=select_account', response['Location'])
		self.assertIn('code_challenge=', response['Location'])

	def test_homepage_google_button_links_to_provider_when_configured(self):
		provider_settings = {
			'google': {
				'APP': {'client_id': 'test-client-id', 'secret': 'test-client-secret', 'key': ''},
				'SCOPE': ['profile', 'email'],
			}
		}
		with override_settings(
			GOOGLE_OAUTH_ENABLED=True,
			SOCIALACCOUNT_PROVIDERS=provider_settings,
		):
			user = User.objects.create_user(username='publicuser')
			response = self.client.get(reverse('user_profile', kwargs={'username': user.username}))

		self.assertContains(response, '/accounts/google/login/')
		self.assertContains(response, 'Google bilan kirish yoki ro‘yxatdan o‘tish')

	def test_password_validation_errors_are_uzbek(self):
		response = self.client.post(
			reverse('register'),
			{
				'username': 'aziz',
				'email': 'aziz@example.com',
				'phone': '',
				'bio': '',
				'avatar': '',
				'password1': '12345678',
				'password2': '12345678',
			},
		)

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Bu parol juda ommabop. Boshqa parol tanlang.')
		self.assertContains(response, 'Parol faqat raqamlardan iborat bo‘lishi mumkin emas.')
		self.assertNotContains(response, 'This password')
		self.assertLess(
			response.content.index('Bu parol juda ommabop.'.encode()),
			response.content.index('Parolni tasdiqlash'.encode()),
		)

	def test_registration_creates_and_logs_in_profile(self):
		response = self.client.post(
			reverse('register'),
			{
				'username': 'aziz',
				'email': 'aziz@example.com',
				'phone': '+998901234567',
				'bio': 'Salom, bu mening sahifam.',
				'avatar': '',
				'password1': 'UltraSafePass938!!',
				'password2': 'UltraSafePass938!!',
			},
		)

		self.assertRedirects(response, reverse('profile'))
		profile = Profile.objects.get(user__username='aziz')
		self.assertEqual(profile.phone, '+998901234567')
		self.assertEqual(profile.bio, 'Salom, bu mening sahifam.')
		self.assertContains(self.client.get(reverse('profile')), 'Salom, bu mening sahifam.')

	def test_profile_owner_can_upload_avatar(self):
		user = User.objects.create_user(username='avataruser', password='UltraSafePass938!!')
		profile = Profile.objects.create(user=user)
		avatar = SimpleUploadedFile(
			'portrait.png',
			b'\x89PNG\r\n\x1a\nsample-image-data',
			content_type='image/png',
		)
		self.client.force_login(user)

		with TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
			response = self.client.post(
				reverse('edit_profile'),
				{'bio': 'Mening yangi profilim', 'phone': '', 'avatar': avatar},
			)

			self.assertRedirects(response, reverse('profile'))
			profile.refresh_from_db()
			self.assertEqual(profile.bio, 'Mening yangi profilim')
			self.assertTrue(Path(profile.avatar.path).is_file())


class PostFeatureTests(TestCase):
	def setUp(self):
		self.user = User.objects.create_user(username='mutalov_n', password='UltraSafePass938!!')
		self.profile = Profile.objects.create(user=self.user)

	def test_home_page_shows_posts_without_post_form(self):
		from .models import Post
		Post.objects.create(
			user=self.user,
			title='Spiderman Brend New Day',
			desc='Spiderman Brend New Day amajing film',
		)
		response = self.client.get(reverse('home'))
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Spiderman Brend New Day')
		self.assertContains(response, 'Spiderman Brend New Day amajing film')
		self.assertContains(response, 'mutalov_n')
		# Crucial check: Post creation form should NOT be on home page
		self.assertNotContains(response, 'Yangi post qo‘shish')
		self.assertNotContains(response, 'Sarlavha kiriting')

	def test_home_page_handles_posts_by_users_without_profile(self):
		from .models import Post
		other_user = User.objects.create_user(username='profileless_user', password='UltraSafePass938!!')
		Post.objects.create(
			user=other_user,
			title='Profilesiz post',
			desc='Bu profil bo‘lmagan foydalanuvchiga tegishli post.',
		)

		response = self.client.get(reverse('home'))
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Profilesiz post')
		self.assertContains(response, 'profileless_user')

	def test_followed_posts_appear_before_newer_public_posts(self):
		followed_user = User.objects.create_user(username='followed_user')
		public_user = User.objects.create_user(username='public_user')
		followed_post = Post.objects.create(user=followed_user, title='Followed older post')
		Post.objects.create(user=public_user, title='Newer public post')
		UserFollow.objects.create(user=followed_user, follower=self.user)
		self.client.force_login(self.user)

		response = self.client.get(reverse('home'))

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.context['posts'][0].pk, followed_post.pk)

	def test_home_feed_is_paginated(self):
		for index in range(11):
			Post.objects.create(user=self.user, title=f'Pagination post {index}')

		first_page = self.client.get(reverse('home'))
		second_page = self.client.get(reverse('home'), {'page': 2})

		self.assertEqual(first_page.context['posts'].paginator.per_page, 10)
		self.assertEqual(len(first_page.context['posts']), 10)
		self.assertEqual(len(second_page.context['posts']), 1)
		self.assertContains(first_page, 'Lenta sahifalari')

	def test_search_returns_matching_users_and_posts(self):
		user = User.objects.create_user(
			username='searchuser',
			first_name='Aziz',
			password='UltraSafePass938!!',
		)
		Post.objects.create(user=user, title='Searchable sunset')

		response = self.client.get(reverse('search'), {'q': 'search'})

		self.assertEqual(response.status_code, 200)
		results = response.json()['results']
		self.assertTrue(any(item['type'] == 'user' for item in results))
		self.assertTrue(any(item['type'] == 'post' for item in results))
		self.assertTrue(any(item['url'] == reverse('user_profile', kwargs={'username': user.username}) for item in results))

	def test_home_page_has_community_chat_widget(self):
		response = self.client.get(reverse('home'))
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Jamiyat suhbatlari')
		self.assertContains(response, 'Kirish va chatga qo‘shilish')
		self.assertNotContains(response, 'chat-input')

	def test_authenticated_home_page_shows_live_chat(self):
		self.client.force_login(self.user)
		response = self.client.get(reverse('home'))
		self.assertContains(response, 'chat-input')
		self.assertContains(response, 'chat/contacts/')
		self.assertContains(response, 'Yuborish')

	def test_chat_contacts_return_other_users_and_mark_current_user_online(self):
		other_user = User.objects.create_user(username='chat_partner')
		self.client.force_login(self.user)

		response = self.client.get(reverse('chat_contacts'))

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.json()['contacts'][0]['username'], other_user.username)
		self.assertFalse(response.json()['contacts'][0]['is_online'])
		self.assertTrue(ChatPresence.objects.filter(user=self.user).exists())

	def test_chat_messages_are_saved_and_only_returned_to_participants(self):
		other_user = User.objects.create_user(username='chat_partner')
		self.client.force_login(self.user)
		url = reverse('chat_messages', kwargs={'user_id': other_user.pk})

		send_response = self.client.post(
			url,
			data='{"body": "Salom, yaxshimisiz?"}',
			content_type='application/json',
		)

		self.assertEqual(send_response.status_code, 201)
		self.assertEqual(ChatMessage.objects.get().body, 'Salom, yaxshimisiz?')
		self.client.force_login(other_user)
		read_response = self.client.get(reverse('chat_messages', kwargs={'user_id': self.user.pk}))
		self.assertEqual(read_response.status_code, 200)
		self.assertEqual(read_response.json()['messages'][0]['body'], 'Salom, yaxshimisiz?')

		unrelated_user = User.objects.create_user(username='not_in_chat')
		self.client.force_login(unrelated_user)
		private_response = self.client.get(url)
		self.assertEqual(private_response.json()['messages'], [])

	def test_chat_rejects_empty_oversized_and_self_messages(self):
		self.client.force_login(self.user)
		url = reverse('chat_messages', kwargs={'user_id': self.user.pk})
		self.assertEqual(self.client.post(url, data='{"body":"hi"}', content_type='application/json').status_code, 400)

		other_user = User.objects.create_user(username='chat_partner')
		url = reverse('chat_messages', kwargs={'user_id': other_user.pk})
		empty_response = self.client.post(url, data='{"body":"  "}', content_type='application/json')
		oversized_response = self.client.post(
			url,
			data=json.dumps({'body': 'x' * 1001}),
			content_type='application/json',
		)
		self.assertEqual(empty_response.status_code, 400)
		self.assertEqual(oversized_response.status_code, 400)

	def test_chat_page_renders_for_guest_and_user(self):
		# Guest access
		guest_response = self.client.get(reverse('chat'))
		self.assertEqual(guest_response.status_code, 200)
		self.assertContains(guest_response, 'Jonli Chat')
		self.assertContains(guest_response, 'Kirish va suhbatga qo‘shilish')
		self.assertContains(guest_response, 'floating-chat-trigger')

		# Authenticated access
		self.client.force_login(self.user)
		auth_response = self.client.get(reverse('chat'))
		self.assertEqual(auth_response.status_code, 200)
		self.assertContains(auth_response, 'chat-input')
		self.assertContains(auth_response, 'chat-contacts-search')
		self.assertContains(auth_response, 'Yuborish')
		self.assertTrue(ChatPresence.objects.filter(user=self.user).exists())

	def test_profile_page_has_post_creation_form_for_owner(self):
		self.client.force_login(self.user)
		response = self.client.get(reverse('profile'))
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Yangi post qo‘shish')
		self.assertContains(response, 'Sarlavha kiriting')
		self.assertContains(response, 'Izoh kiriting')
		self.assertContains(response, 'Ulashish')

	def test_user_can_create_post_from_profile(self):
		from .models import Post
		self.client.force_login(self.user)
		response = self.client.post(reverse('profile'), {
			'title': 'Mening birinchi postim',
			'desc': 'Bu ajoyib post tavsifi',
		})
		self.assertRedirects(response, reverse('profile'))
		self.assertEqual(Post.objects.filter(user=self.user).count(), 1)
		post = Post.objects.first()
		self.assertEqual(post.title, 'Mening birinchi postim')
		self.assertEqual(post.desc, 'Bu ajoyib post tavsifi')

		# Now check that post appears on home page
		home_resp = self.client.get(reverse('home'))
		self.assertContains(home_resp, 'Mening birinchi postim')
		self.assertContains(home_resp, 'mutalov_n')

	def test_user_can_delete_own_post(self):
		from .models import Post
		post = Post.objects.create(
			user=self.user,
			title='O‘chiriladigan post',
			desc='Tez orada o‘chiriladi',
		)
		self.client.force_login(self.user)
		response = self.client.post(reverse('delete_post', kwargs={'pk': post.pk}))
		self.assertRedirects(response, reverse('profile'))
		self.assertEqual(Post.objects.filter(pk=post.pk).count(), 0)

	def test_user_can_like_comment_and_follow_post_author(self):
		from .models import Post, PostComment, PostLike, UserFollow
		other_user = User.objects.create_user(username='other_user', password='UltraSafePass938!!')
		post = Post.objects.create(user=other_user, title='Social test post', desc='Post for social actions')
		self.client.force_login(self.user)

		like_response = self.client.post(reverse('toggle_like', kwargs={'pk': post.pk}), {'next': reverse('home')})
		self.assertRedirects(like_response, reverse('home'))
		self.assertEqual(PostLike.objects.filter(post=post, user=self.user).count(), 1)

		comment_response = self.client.post(reverse('add_comment', kwargs={'pk': post.pk}), {'body': 'Uziz qiziqarli post!', 'next': reverse('home')})
		self.assertRedirects(comment_response, reverse('home'))
		self.assertEqual(PostComment.objects.filter(post=post, user=self.user).count(), 1)
		self.assertEqual(PostComment.objects.get(post=post).body, 'Uziz qiziqarli post!')

		follow_response = self.client.post(reverse('toggle_follow', kwargs={'username': other_user.username}), {'next': reverse('home')})
		self.assertRedirects(follow_response, reverse('home'))
		self.assertEqual(UserFollow.objects.filter(user=other_user, follower=self.user).count(), 1)

		page = self.client.get(reverse('home'))
		self.assertContains(page, 'Kuzatilmoqda')
		self.assertContains(page, 'Yuborish')

	def test_follow_rejects_get_and_external_redirects(self):
		target = User.objects.create_user(username='redirect_target')
		self.client.force_login(self.user)
		follow_url = reverse('toggle_follow', kwargs={'username': target.username})

		get_response = self.client.get(follow_url)
		post_response = self.client.post(follow_url, {'next': 'https://example.invalid/'})

		self.assertEqual(get_response.status_code, 405)
		self.assertEqual(post_response.status_code, 302)
		self.assertEqual(post_response['Location'], reverse('home'))

	def test_realtime_comment_api_and_deletion(self):
		from .models import Post, PostComment
		other_user = User.objects.create_user(username='commenter', password='UltraSafePass938!!')
		post = Post.objects.create(user=self.user, title='Post with comments', desc='Test comments')
		c1 = PostComment.objects.create(post=post, user=other_user, body='Birinchi izoh!')

		get_resp = self.client.get(reverse('get_comments', kwargs={'pk': post.pk}))
		self.assertEqual(get_resp.status_code, 200)
		data = get_resp.json()
		self.assertEqual(data['status'], 'ok')
		self.assertEqual(len(data['comments']), 1)
		self.assertEqual(data['comments'][0]['body'], 'Birinchi izoh!')

		self.client.force_login(self.user)
		post_resp = self.client.post(
			reverse('add_comment', kwargs={'pk': post.pk}),
			data=json.dumps({'body': 'Mening javobim!'}),
			content_type='application/json',
			HTTP_X_REQUESTED_WITH='XMLHttpRequest',
		)
		self.assertEqual(post_resp.status_code, 200)
		post_data = post_resp.json()
		self.assertEqual(post_data['status'], 'ok')
		self.assertEqual(post_data['comment']['body'], 'Mening javobim!')
		self.assertEqual(post_data['comments_count'], 2)

		get_after = self.client.get(reverse('get_comments', kwargs={'pk': post.pk}), {'after': c1.pk})
		self.assertEqual(len(get_after.json()['comments']), 1)
		self.assertEqual(get_after.json()['comments'][0]['body'], 'Mening javobim!')

		new_comment_id = post_data['comment']['id']
		del_resp = self.client.post(
			reverse('delete_comment', kwargs={'pk': new_comment_id}),
			HTTP_X_REQUESTED_WITH='XMLHttpRequest',
		)
		self.assertEqual(del_resp.status_code, 200)
		self.assertEqual(del_resp.json()['status'], 'ok')
		self.assertEqual(PostComment.objects.filter(pk=new_comment_id).count(), 0)

	def test_pricing_page_has_tariff_cards(self):
		response = self.client.get(reverse('pricing'))
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Boshlang’ich')
		self.assertContains(response, 'Standart')
		self.assertContains(response, 'Premium')
		self.assertContains(response, 'O‘zingizga mos xizmat narxini tanlang')
