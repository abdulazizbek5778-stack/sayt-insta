from django import forms
from django.contrib.auth import password_validation
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.utils.html import format_html

from .models import Post, Profile, Story


def validate_avatar(avatar):
    if not avatar:
        return avatar
    if avatar.size > 5 * 1024 * 1024:
        raise forms.ValidationError('Rasm hajmi 5 MB dan oshmasin.')

    header = avatar.read(12)
    avatar.seek(0)
    valid_image = (
        header.startswith(b'\xff\xd8\xff')
        or header.startswith(b'\x89PNG\r\n\x1a\n')
        or header.startswith((b'GIF87a', b'GIF89a'))
        or (header.startswith(b'RIFF') and header[8:12] == b'WEBP')
    )
    if not valid_image:
        raise forms.ValidationError('JPG, PNG, GIF yoki WEBP rasm yuklang.')
    return avatar

class RegisterForm(UserCreationForm):
    email = forms.EmailField(
        label='Email manzili',
        error_messages={
            'required': 'Email manzilini kiriting.',
            'invalid': 'Email manzili noto‘g‘ri.',
        },
    )
    phone = forms.CharField(label='Telefon raqami', max_length=32, required=False)
    bio = forms.CharField(
        label="Qisqacha ma'lumot",
        max_length=160,
        required=False,
        widget=forms.Textarea(attrs={'rows': 10, 'cols': 40}),
    )
    avatar = forms.FileField(label='Profil rasmi', required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].label = 'Foydalanuvchi nomi'
        self.fields['username'].help_text = (
            '150 ta belgigacha. Harflar, raqamlar va @/./+/-/_ belgilaridan foydalaning.'
        )
        self.fields['password1'].label = 'Parol'
        self.fields['password1'].help_text = format_html(
            '<ul><li>{}</li><li>{}</li><li>{}</li><li>{}</li></ul>',
            'Parol boshqa shaxsiy ma’lumotlaringizga juda o‘xshamasin.',
            'Parol kamida 8 ta belgidan iborat bo‘lsin.',
            'Ommabop parollardan foydalanmang.',
            'Parol faqat raqamlardan iborat bo‘lmasin.',
        )
        self.fields['password2'].label = 'Parolni tasdiqlash'
        self.fields['password2'].help_text = 'Tasdiqlash uchun yuqoridagi parolni qayta kiriting.'

    def clean_password2(self):
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')
        if password1 and password2 and password1 != password2:
            self.add_error('password2', 'Ikkala parol bir xil bo‘lishi kerak.')
        return password2

    def validate_password_for_user(self, user, password_field_name='password1'):
        password = self.cleaned_data.get(password_field_name)
        if password:
            try:
                password_validation.validate_password(password, user)
            except forms.ValidationError as error:
                self.add_error(password_field_name, error)

    def clean_avatar(self):
        return validate_avatar(self.cleaned_data.get('avatar'))

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'email')


class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ('bio', 'phone', 'avatar')
        labels = {
            'bio': "Qisqacha ma'lumot",
            'phone': 'Telefon raqami',
            'avatar': 'Profil rasmi',
        }
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 3}),
        }

    def clean_avatar(self):
        return validate_avatar(self.cleaned_data.get('avatar'))


class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ('title', 'desc', 'img', 'video')
        labels = {
            'title': 'Title',
            'desc': 'Desc',
            'img': 'Img',
            'video': 'Video',
        }
        widgets = {
            'title': forms.TextInput(attrs={
                'placeholder': 'Sarlavha kiriting',
                'class': 'form-input',
                'required': True,
            }),
            'desc': forms.Textarea(attrs={
                'placeholder': 'Izoh kiriting',
                'class': 'form-textarea',
                'rows': 4,
            }),
            'img': forms.FileInput(attrs={
                'class': 'form-file-input',
                'accept': 'image/*',
            }),
            'video': forms.FileInput(attrs={
                'class': 'form-file-input',
                'accept': 'video/*',
            }),
        }

    def clean_img(self):
        img = self.cleaned_data.get('img')
        if img and img.size > 15 * 1024 * 1024:
            raise forms.ValidationError("Rasm hajmi 15 MB dan oshmasligi kerak.")
        return img

    def clean_video(self):
        video = self.cleaned_data.get('video')
        if video and video.size > 100 * 1024 * 1024:
            raise forms.ValidationError("Video hajmi 100 MB dan oshmasligi kerak.")
        return video


class StoryForm(forms.ModelForm):
    class Meta:
        model = Story
        fields = ('media', 'caption')
        labels = {
            'media': 'Story media',
            'caption': 'Caption',
        }
        widgets = {
            'media': forms.FileInput(attrs={
                'accept': 'image/*,video/*',
                'class': 'story-file-input',
            }),
            'caption': forms.TextInput(attrs={
                'placeholder': 'Story haqida qisqacha matn...',
                'class': 'story-caption-input',
                'maxlength': 220,
            }),
        }

    def clean_media(self):
        media = self.cleaned_data.get('media')
        if not media:
            raise forms.ValidationError('Story uchun media fayl kiriting.')
        if media.size > 30 * 1024 * 1024:
            raise forms.ValidationError('Story hajmi 30 MB dan oshmasligi kerak.')
        return media