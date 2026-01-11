import re
import signal
import time
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import close_old_connections
from django.db.models import F
from django.utils import timezone

from core.models import (
    ConversationProcessingState,
    RoomDailySummaryCount,
    RoomSummary,
    SubscriberRoom,
    TodoList,
)
from core.services.llm import LLMService
from core.services.matrix import MatrixService, RoomService


class Command(BaseCommand):
    help = "Long-running worker that handles subscriber requests"

    running = True
    FRIDAY_USER_ID = "@friday:matrix.tirta.me"
    SUMMARY_COOLDOWN_MINUTES = 15

    # Command patterns
    COMMANDS = {
        "help": r"^help$",
        "rooms": r"^rooms$",
        "summary_all": r"^summary\s+all$",
        "summary_room": r"^summary\s+(\S+)$",
        "todo_all": r"^todo\s+all$",
        "todo_room": r"^todo\s+(\S+)$",
    }

    def handle(self, *args, **options):
        signal.signal(signal.SIGTERM, self.stop)
        signal.signal(signal.SIGINT, self.stop)

        self.stdout.write("Worker started")

        # Initialize services
        self.matrix_service = MatrixService()
        self.matrix_service.login()
        self.stdout.write("Logged in to Matrix")

        self.room_service = RoomService()
        self.llm_service = LLMService()

        while self.running:
            try:
                close_old_connections()
                self.run_once()
            except Exception as e:
                self.stderr.write(f"Error: {str(e)}")

            time.sleep(5)

        self.stdout.write("Worker stopped")

    def stop(self, *args):
        self.running = False

    def run_once(self):
        # Get all active subscribers with matrix_room_id
        subscribers = self.matrix_service.get_active_subscribers()

        if not subscribers:
            self.stdout.write("No active subscribers found")
            return

        for subscriber in subscribers:
            try:
                self.process_subscriber(subscriber)
            except Exception as e:
                self.stderr.write(
                    f"Failed to process subscriber {subscriber.id}: {str(e)}"
                )

    def process_subscriber(self, subscriber):
        # Get last message from subscriber's matrix room
        last_message = self.matrix_service.get_last_message(
            room_id=subscriber.matrix_room_id
        )

        if not last_message:
            return

        # If last message is from Friday, skip (already responded)
        if last_message.get("sender") == self.FRIDAY_USER_ID:
            return

        message_body = last_message.get("body", "").lower().strip()

        # Parse and route command
        command, args = self.parse_command(message_body)

        if not command:
            # Check if it looks like a command attempt
            if self.looks_like_command(message_body):
                self.handle_unknown_command(subscriber)
            return

        self.stdout.write(f"Command '{command}' from subscriber {subscriber.id}")

        # Route to appropriate handler
        if command == "help":
            self.handle_help(subscriber)
        elif command == "rooms":
            self.handle_rooms(subscriber)
        elif command == "summary_all":
            self.handle_summary_all(subscriber)
        elif command == "summary_room":
            self.handle_summary_room(subscriber, args)
        elif command == "todo_all":
            self.handle_todo_all(subscriber)
        elif command == "todo_room":
            self.handle_todo_room(subscriber, args)

    def parse_command(self, message_body):
        """Parse message and return (command_name, args) or (None, None)."""
        for cmd_name, pattern in self.COMMANDS.items():
            match = re.match(pattern, message_body, re.IGNORECASE)
            if match:
                args = match.groups() if match.groups() else None
                return cmd_name, args
        return None, None

    def looks_like_command(self, message_body):
        """Check if message looks like a command attempt."""
        command_prefixes = ["help", "rooms", "room", "summary", "todo", "task", "tasks"]
        first_word = message_body.split()[0] if message_body.split() else ""
        return first_word in command_prefixes

    def handle_unknown_command(self, subscriber):
        """Handle unrecognized command with helpful response."""
        self.matrix_service.send_message(
            room_id=subscriber.matrix_room_id,
            body="Sorry, I didn't recognize that command. Type 'help' to see what I can do.",
        )

    def handle_help(self, subscriber):
        """Show available commands."""
        help_text = """Available commands:

• help - Show this help message
• rooms - List your monitored rooms
• summary all - Get summaries for all rooms
• summary {room_code} - Get summary for a specific room
• todo all - Show all pending tasks
• todo {room_code} - Show tasks for a specific room"""

        self.matrix_service.send_message(
            room_id=subscriber.matrix_room_id,
            body=help_text,
        )

    def handle_rooms(self, subscriber):
        """List subscriber's rooms."""
        rooms = SubscriberRoom.objects.filter(
            subscriber=subscriber,
            is_active=True,
        )

        if not rooms.exists():
            self.matrix_service.send_message(
                room_id=subscriber.matrix_room_id,
                body="You don't have any monitored rooms yet.",
            )
            return

        lines = ["Your monitored rooms:\n"]
        for room in rooms:
            name = room.room_name or room.room_id
            lines.append(f"• {room.room_code} - {name}")

        self.matrix_service.send_message(
            room_id=subscriber.matrix_room_id,
            body="\n".join(lines),
        )

    def handle_summary_all(self, subscriber):
        """Handle summary all command (existing behavior)."""
        subscriber_rooms = SubscriberRoom.objects.filter(
            subscriber=subscriber,
            is_active=True,
        )

        if not subscriber_rooms.exists():
            self.matrix_service.send_message(
                room_id=subscriber.matrix_room_id,
                body="You don't have any monitored rooms.",
            )
            return

        # Check cooldown
        if not self.check_summary_cooldown(subscriber):
            return

        self.process_summaries(subscriber, subscriber_rooms)

    def handle_summary_room(self, subscriber, args):
        """Handle summary for a specific room."""
        room_code = args[0] if args else None

        if not room_code:
            self.matrix_service.send_message(
                room_id=subscriber.matrix_room_id,
                body="Please specify a room code. Use 'rooms' to see your room codes.",
            )
            return

        room = SubscriberRoom.objects.filter(
            subscriber=subscriber,
            room_code__iexact=room_code,
            is_active=True,
        ).first()

        if not room:
            self.matrix_service.send_message(
                room_id=subscriber.matrix_room_id,
                body=f"Room '{room_code}' not found. Use 'rooms' to see your room codes.",
            )
            return

        # Check cooldown
        if not self.check_summary_cooldown(subscriber):
            return

        self.process_summaries(subscriber, [room])

    def handle_todo_all(self, subscriber):
        """Show all pending todos for subscriber."""
        todos = TodoList.objects.filter(
            room__subscriber=subscriber,
            status=TodoList.STATUS_PENDING,
        ).select_related("room").order_by("-created_at")[:20]

        if not todos.exists():
            self.matrix_service.send_message(
                room_id=subscriber.matrix_room_id,
                body="No pending tasks. You're all caught up!",
            )
            return

        lines = ["Your pending tasks:\n"]
        for todo in todos:
            room_name = todo.room.room_code if todo.room else "General"
            lines.append(f"• [{room_name}] {todo.description}")

        self.matrix_service.send_message(
            room_id=subscriber.matrix_room_id,
            body="\n".join(lines),
        )

    def handle_todo_room(self, subscriber, args):
        """Show todos for a specific room."""
        room_code = args[0] if args else None

        if not room_code:
            self.matrix_service.send_message(
                room_id=subscriber.matrix_room_id,
                body="Please specify a room code. Use 'rooms' to see your room codes.",
            )
            return

        room = SubscriberRoom.objects.filter(
            subscriber=subscriber,
            room_code__iexact=room_code,
            is_active=True,
        ).first()

        if not room:
            self.matrix_service.send_message(
                room_id=subscriber.matrix_room_id,
                body=f"Room '{room_code}' not found. Use 'rooms' to see your room codes.",
            )
            return

        todos = TodoList.objects.filter(
            room=room,
            status=TodoList.STATUS_PENDING,
        ).order_by("-created_at")[:20]

        room_name = room.room_name or room.room_code

        if not todos.exists():
            self.matrix_service.send_message(
                room_id=subscriber.matrix_room_id,
                body=f"No pending tasks for {room_name}.",
            )
            return

        lines = [f"Pending tasks for {room_name}:\n"]
        for todo in todos:
            lines.append(f"• {todo.description}")

        self.matrix_service.send_message(
            room_id=subscriber.matrix_room_id,
            body="\n".join(lines),
        )

    def check_summary_cooldown(self, subscriber) -> bool:
        """Check if subscriber is within cooldown period. Returns True if OK to proceed."""
        last_summary = RoomSummary.objects.filter(
            room__subscriber=subscriber,
            sent_at__isnull=False,
        ).order_by("-sent_at").first()

        if last_summary:
            time_since_last = timezone.now() - last_summary.sent_at
            if time_since_last < timedelta(minutes=self.SUMMARY_COOLDOWN_MINUTES):
                remaining = self.SUMMARY_COOLDOWN_MINUTES - int(time_since_last.total_seconds() / 60)
                self.matrix_service.send_message(
                    room_id=subscriber.matrix_room_id,
                    body=f"Please wait {remaining} more minutes for the next summary.",
                )
                return False
        return True

    def process_summaries(self, subscriber, subscriber_rooms):
        access_token = self.matrix_service.get_access_token()
        today = timezone.now().date()
        summaries_sent = 0

        for room in subscriber_rooms:
            try:
                # Get or create processing state
                state, _ = ConversationProcessingState.objects.get_or_create(
                    room=room,
                    defaults={"status": ConversationProcessingState.STATUS_IDLE},
                )

                # Build context for summary
                context = self.llm_service.build_llm_context_for_summary(
                    state=state,
                    room_service=self.room_service,
                    access_token=access_token,
                )

                if not context:
                    continue

                # Process with LLM
                summary = self.llm_service.process_room(state=state, context=context)

                # Increment daily count
                question_count = self.get_and_increment_daily_count(room, today)

                # Format and send
                formatted_message = self.llm_service.format_summary_message(
                    summary, question_count
                )
                self.matrix_service.send_message(
                    room_id=subscriber.matrix_room_id,
                    body=formatted_message,
                )

                # Mark as sent
                summary.sent_at = timezone.now()
                summary.save(update_fields=["sent_at"])

                summaries_sent += 1
                self.stdout.write(
                    self.style.SUCCESS(f"Sent summary for room {room.id}")
                )

            except Exception as e:
                self.stderr.write(f"Failed to summarize room {room.id}: {str(e)}")

        if summaries_sent == 0:
            self.matrix_service.send_message(
                room_id=subscriber.matrix_room_id,
                body="Tidak ada pesan baru untuk diringkas.",
            )

    def get_and_increment_daily_count(self, room, today) -> int:
        """Get current count, increment it, and return the new count."""
        daily_count, _ = RoomDailySummaryCount.objects.get_or_create(
            room=room,
            date=today,
            defaults={"count": 0},
        )
        RoomDailySummaryCount.objects.filter(pk=daily_count.pk).update(
            count=F("count") + 1
        )
        daily_count.refresh_from_db()
        return daily_count.count
