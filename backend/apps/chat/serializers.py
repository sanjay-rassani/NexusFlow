"""
Chat serializers.

MessageSerializer        — full message payload sent over REST and WebSocket.
ChatRoomSerializer       — list view (room summary + last message + unread count).
ChatRoomDetailSerializer — room detail with paginated recent messages.
"""

from rest_framework import serializers

from apps.users.serializers import UserProfileSerializer

from .models import ChatRoom, Message


class MessageSerializer(serializers.ModelSerializer):
    sender = UserProfileSerializer(read_only=True)
    is_own = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = [
            "id",
            "sender",
            "is_own",
            "content",
            "is_read",
            "read_at",
            "created_at",
        ]
        read_only_fields = fields

    def get_is_own(self, obj) -> bool:
        """Flag whether the requesting user is the message sender."""
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            return obj.sender_id == request.user.pk
        return False


class MessageCreateSerializer(serializers.Serializer):
    """Used by REST endpoint to validate incoming message content."""
    content = serializers.CharField(min_length=1, max_length=4096, trim_whitespace=True)


class ChatRoomSerializer(serializers.ModelSerializer):
    """Compact representation for room listing."""

    order_id = serializers.UUIDField(source="order.id", read_only=True)
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    participant_ids = serializers.SerializerMethodField()

    class Meta:
        model = ChatRoom
        fields = [
            "id",
            "order_id",
            "participant_ids",
            "last_message",
            "unread_count",
            "created_at",
        ]
        read_only_fields = fields

    def get_last_message(self, obj):
        msg = obj.messages.order_by("-created_at").first()
        if not msg:
            return None
        return {
            "id": str(msg.id),
            "sender_email": msg.sender.email,
            "content": msg.content[:100],
            "created_at": msg.created_at.isoformat(),
        }

    def get_unread_count(self, obj) -> int:
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return 0
        return obj.messages.filter(is_read=False).exclude(sender=request.user).count()

    def get_participant_ids(self, obj):
        return [str(uid) for uid in obj.participants.values_list("id", flat=True)]


class ChatRoomDetailSerializer(ChatRoomSerializer):
    """Room detail — includes the 50 most recent messages."""

    recent_messages = serializers.SerializerMethodField()

    class Meta(ChatRoomSerializer.Meta):
        fields = ChatRoomSerializer.Meta.fields + ["recent_messages"]

    def get_recent_messages(self, obj):
        messages = obj.messages.select_related("sender").order_by("-created_at")[:50]
        return MessageSerializer(
            reversed(list(messages)),
            many=True,
            context=self.context,
        ).data
