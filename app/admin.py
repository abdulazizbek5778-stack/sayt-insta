from django.contrib import admin
from .models import Post, PostComment, PostLike, Profile, UserFollow


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone', 'bio')
    search_fields = ('user__username', 'phone', 'bio')


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'created_at')
    search_fields = ('title', 'desc', 'user__username')
    list_filter = ('created_at',)


@admin.register(PostLike)
class PostLikeAdmin(admin.ModelAdmin):
    list_display = ('post', 'user', 'created_at')
    search_fields = ('post__title', 'user__username')


@admin.register(PostComment)
class PostCommentAdmin(admin.ModelAdmin):
    list_display = ('post', 'user', 'body', 'created_at')
    search_fields = ('post__title', 'user__username', 'body')


@admin.register(UserFollow)
class UserFollowAdmin(admin.ModelAdmin):
    list_display = ('user', 'follower', 'created_at')
    search_fields = ('user__username', 'follower__username')
