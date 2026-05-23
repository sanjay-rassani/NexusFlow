from django.contrib import admin
from .models import ChatRoom, Message


@admin.register(ChatRoom)
class ChatRoomAdmin(admin.ModelAdmin):
    list_display = ["id", "order", "created_at"]
    filter_horizontal = ["participants"]


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ["sender", "room", "is_read", "created_at"]
    list_filter = ["is_read"]
    readonly_fields = ["id", "created_at"]
