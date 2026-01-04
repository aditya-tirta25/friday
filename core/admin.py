from django.contrib import admin

from core.models import Room, RoomCheckLog


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ('room_id', 'name', 'creator', 'member_count', 'is_checked', 'last_checked_at', 'created_at')
    list_filter = ('is_checked', 'created_at', 'last_checked_at')
    search_fields = ('room_id', 'name', 'creator')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-created_at',)


@admin.register(RoomCheckLog)
class RoomCheckLogAdmin(admin.ModelAdmin):
    list_display = ('room', 'checked_at', 'summary')
    list_filter = ('checked_at',)
    search_fields = ('room__room_id', 'room__name', 'summary')
    readonly_fields = ('checked_at',)
    ordering = ('-checked_at',)
