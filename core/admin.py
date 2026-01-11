from django.contrib import admin

admin.site.site_header = "Lidya Administration"
admin.site.site_title = "Lidya Admin"
admin.site.index_title = "Lidya Administration"

from core.models import (
    GeneralSettings,
    Room,
    RoomCheckLog,
    Subscriber,
    SubscriberRoom,
    Plan,
    Subscription,
    Payment,
    ConversationProcessingState,
    RoomDailySummaryCount,
    RoomSummary,
    TodoList,
)


@admin.register(GeneralSettings)
class GeneralSettingsAdmin(admin.ModelAdmin):
    list_display = ("id", "llm_model")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        from django.shortcuts import redirect
        from django.urls import reverse

        obj, _ = GeneralSettings.objects.get_or_create(pk=1)
        url = reverse("admin:core_generalsettings_change", args=[obj.pk])
        return redirect(url)


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = (
        "room_id",
        "name",
        "creator",
        "member_count",
        "is_checked",
        "last_checked_at",
        "created_at",
    )
    list_filter = ("is_checked", "created_at", "last_checked_at")
    search_fields = ("room_id", "name", "creator")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("-created_at",)


@admin.register(RoomCheckLog)
class RoomCheckLogAdmin(admin.ModelAdmin):
    list_display = ("room", "checked_at", "summary")
    list_filter = ("checked_at",)
    search_fields = ("room__room_id", "room__name", "summary")
    readonly_fields = ("checked_at",)
    ordering = ("-checked_at",)


class SubscriberRoomInline(admin.TabularInline):
    model = SubscriberRoom
    extra = 0
    fields = ("platform", "room_id", "room_code", "room_name", "last_read_at", "is_active")
    readonly_fields = ("last_read_at",)


@admin.register(Subscriber)
class SubscriberAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "full_name",
        "email",
        "phone_number",
        "matrix_room_id",
        "is_active",
        "created_at",
    )
    list_filter = ("is_active", "created_at")
    search_fields = ("full_name", "email", "phone_number", "matrix_room_id")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("-created_at",)
    inlines = [SubscriberRoomInline]


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "price",
        "currency",
        "billing_period",
        "number_of_rooms",
        "daily_summary_quota_per_room",
        "version",
        "is_active",
        "created_at",
    )
    list_filter = ("billing_period", "is_active", "version")
    search_fields = ("name",)
    readonly_fields = ("created_at",)
    ordering = ("-created_at",)


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "subscriber",
        "plan",
        "status",
        "start_at",
        "end_at",
        "auto_renew",
        "created_at",
    )
    list_filter = ("status", "auto_renew", "plan", "created_at")
    search_fields = ("subscriber__full_name", "subscriber__email")
    readonly_fields = ("created_at",)
    ordering = ("-created_at",)


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "subscription",
        "amount",
        "currency",
        "provider",
        "status",
        "paid_at",
        "created_at",
    )
    list_filter = ("status", "provider", "created_at")
    search_fields = ("provider_ref", "subscription__subscriber__email")
    readonly_fields = ("created_at",)
    ordering = ("-created_at",)


@admin.register(ConversationProcessingState)
class ConversationProcessingStateAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "room",
        "status",
        "last_message_synced_at",
        "last_summarized_at",
        "processing_started_at",
        "updated_at",
    )
    list_filter = ("status", "updated_at")
    search_fields = ("room__room_id", "room__room_name")
    readonly_fields = ("updated_at",)
    ordering = ("-updated_at",)


@admin.register(RoomDailySummaryCount)
class RoomDailySummaryCountAdmin(admin.ModelAdmin):
    list_display = ("id", "room", "date", "count", "created_at")
    list_filter = ("date",)
    search_fields = ("room__room_id", "room__room_name")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("-date",)


@admin.register(RoomSummary)
class RoomSummaryAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "room",
        "summary_preview",
        "needs_more_information",
        "message_count",
        "is_sent",
        "sent_at",
        "created_at",
    )
    list_filter = ("needs_more_information", "sent_at", "send_failed_at", "created_at")
    search_fields = ("room__room_id", "room__room_name", "summary", "send_error")
    readonly_fields = ("created_at", "sent_at", "send_failed_at")
    ordering = ("-created_at",)

    def summary_preview(self, obj):
        return obj.summary[:100] + "..." if len(obj.summary) > 100 else obj.summary

    summary_preview.short_description = "Summary"

    def is_sent(self, obj):
        if obj.sent_at:
            return True
        if obj.send_failed_at:
            return False
        return None

    is_sent.boolean = True
    is_sent.short_description = "Sent"


@admin.register(TodoList)
class TodoListAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "room",
        "description_preview",
        "status",
        "created_at",
        "updated_at",
    )
    list_filter = ("status", "created_at", "room__subscriber")
    search_fields = ("description", "notes", "room__room_name")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("-created_at",)

    def description_preview(self, obj):
        return obj.description[:80] + "..." if len(obj.description) > 80 else obj.description

    description_preview.short_description = "Description"
