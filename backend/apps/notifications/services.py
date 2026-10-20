from .models import Notification, Preference


def create_notification(
    user,
    notification_type,
    message,
    default_priority=False,
    dedupe_key=None,
):
    configured_priority = Preference.objects.filter(
        user=user, type=notification_type
    ).values_list("is_priority", flat=True).first()
    values = {
        "user": user,
        "type": notification_type,
        "message": message,
        "is_priority": (
            default_priority
            if configured_priority is None
            else configured_priority
        ),
    }
    if dedupe_key:
        return Notification.objects.get_or_create(
            dedupe_key=dedupe_key,
            defaults=values,
        )[0]
    return Notification.objects.create(**values)
