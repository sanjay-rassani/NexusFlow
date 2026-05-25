from django.contrib import admin

from .models import ChatRoom, Message


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    readonly_fields = ("id", "sender", "content", "is_read", "read_at", "created_at")
    can_delete = False
    show_change_link = True
    ordering = ("-created_at",)
    max_num = 20


@admin.register(ChatRoom)
class ChatRoomAdmin(admin.ModelAdmin):
    list_display = ("id", "order", "participant_count", "message_count", "created_at")
    readonly_fields = ("id", "created_at")
    filter_horizontal = ("participants",)
    inlines = [MessageInline]

    @admin.display(description="Participants")
    def participant_count(self, obj):
        return obj.participants.count()

    @admin.display(description="Messages")
    def message_count(self, obj):
        return obj.messages.count()


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("id", "room", "sender", "content_preview", "is_read", "created_at")
    list_filter = ("is_read", "created_at")
    search_fields = ("sender__email", "content")
    readonly_fields = ("id", "room", "sender", "content", "is_read", "read_at", "created_at")

    @admin.display(description="Content")
    def content_preview(self, obj):
        return obj.content[:60] + ("…" if len(obj.content) > 60 else "")
