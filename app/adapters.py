from urllib.parse import urlparse

from allauth.socialaccount.adapter import DefaultSocialAccountAdapter

from .models import Profile


class GoogleSocialAccountAdapter(DefaultSocialAccountAdapter):
	def save_user(self, request, sociallogin, form=None):
		user = super().save_user(request, sociallogin, form)
		profile, _ = Profile.objects.get_or_create(user=user)

		picture_url = sociallogin.account.extra_data.get('picture', '')
		parsed_picture_url = urlparse(picture_url) if isinstance(picture_url, str) else None
		if (
			not profile.avatar
			and not profile.avatar_url
			and parsed_picture_url
			and parsed_picture_url.scheme == 'https'
			and parsed_picture_url.netloc
			and len(picture_url) <= 200
		):
			profile.avatar_url = picture_url
			profile.save(update_fields=['avatar_url'])

		return user
