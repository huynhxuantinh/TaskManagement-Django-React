import time
from datetime import date

from django.core.management.base import BaseCommand, CommandError
from django.db import close_old_connections

from apps.tasks.services import send_deadline_notifications


class Command(BaseCommand):
    help = "Gửi nhắc hạn công việc; có thể chạy một lần hoặc chạy định kỳ."

    def add_arguments(self, parser):
        parser.add_argument("--date", help="Ngày đối chiếu dạng YYYY-MM-DD.")
        parser.add_argument("--loop", action="store_true", help="Chạy liên tục.")
        parser.add_argument("--interval", type=int, default=3600, help="Chu kỳ giây.")

    def handle(self, *args, **options):
        if options["interval"] <= 0:
            raise CommandError("Chu kỳ phải lớn hơn 0 giây.")
        reference_date = self._parse_date(options.get("date"))
        while True:
            close_old_connections()
            processed = send_deadline_notifications(reference_date)
            self.stdout.write(
                self.style.SUCCESS(f"Đã kiểm tra {processed} công việc cần nhắc hạn.")
            )
            if not options["loop"]:
                break
            time.sleep(options["interval"])

    @staticmethod
    def _parse_date(value):
        if not value:
            return None
        try:
            return date.fromisoformat(value)
        except ValueError as error:
            raise CommandError("Ngày phải có định dạng YYYY-MM-DD.") from error
