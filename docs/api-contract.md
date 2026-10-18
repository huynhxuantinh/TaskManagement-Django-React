# API contract v1

Trạng thái: draft đã chốt cho giai đoạn migration

Base URL: `/api/v1`

Media type: `application/json` trừ endpoint upload avatar.

## Quy ước chung

Phản hồi thành công:

```json
{
  "success": true,
  "message": "Task retrieved",
  "data": {}
}
```

Phản hồi lỗi:

```json
{
  "success": false,
  "message": "Validation failed",
  "data": null,
  "errors": {
    "title": ["This field is required."]
  }
}
```

- `400`: request hoặc business rule không hợp lệ.
- `401`: chưa đăng nhập hoặc token hết hạn/không hợp lệ.
- `403`: đã đăng nhập nhưng ngoài quyền hoặc ngoài resource scope.
- `404`: resource không tồn tại, đã soft-delete hoặc bị scope loại bỏ.
- `409`: email/member/resource bị trùng hoặc xung đột trạng thái.
- List endpoint dùng `page`, `page_size`, `search`, `ordering` và filter riêng.
- Audit timestamps trả ISO-8601 UTC, ví dụ `2026-10-18T08:30:00Z`.
- `start_date`, `end_date`, `deadline` là ngày nghiệp vụ `YYYY-MM-DD`, không mang timezone.
- Role/status/type dùng code ổn định, không dùng PK để quyết định nghiệp vụ.
- Danh tính và role chỉ lấy từ JWT; không nhận `requestorId`, `userId` hay `role` để cấp quyền.

## Auth và session

| Method | Endpoint | Quyền | Nội dung |
|---|---|---|---|
| POST | `/auth/register/` | Public theo policy | Tạo Employee; có thể tắt public registration ở production |
| POST | `/auth/login/` | Public | Trả access token; đặt refresh cookie HttpOnly |
| POST | `/auth/refresh/` | Refresh cookie + CSRF | Rotate refresh token, trả access token mới |
| POST | `/auth/logout/` | Authenticated + CSRF | Blacklist refresh token và xóa cookie |
| GET | `/auth/me/` | Authenticated | User, role, avatar và permissions tóm tắt |
| POST | `/auth/change-password/` | Authenticated | Xác minh mật khẩu hiện tại rồi đổi mật khẩu |
| POST | `/auth/deactivate/` | Authenticated | Soft deactivate tài khoản hiện tại theo policy |

Access token chỉ giữ trong memory của React. Refresh cookie dùng `HttpOnly`, `Secure` ở production, `SameSite=Lax`, rotation và reuse detection.

## Users và preferences

| Method | Endpoint | Quyền | Nội dung |
|---|---|---|---|
| GET | `/users/` | Admin | List/filter/search người dùng |
| GET | `/users/{id}/` | Admin hoặc self | Chi tiết không trả password hash |
| PATCH | `/users/{id}/` | Admin hoặc self | Self chỉ đổi `full_name`; Admin theo policy |
| PATCH | `/users/{id}/role/` | Admin | Body `{ "role": "MANAGER" }` |
| POST | `/users/{id}/avatar/` | Admin hoặc self | Multipart; kiểm tra MIME/kích thước |
| GET | `/users/{id}/preferences/` | Admin hoặc self | Notification preferences |
| PUT | `/users/{id}/preferences/` | Admin hoặc self | Upsert theo notification type |

User response tối thiểu: `id`, `full_name`, `email`, `role`, `avatar_url`, `is_active`, `created_at`. Không serialize entity/navigation object trực tiếp.

## Projects và members

| Method | Endpoint | Quyền | Nội dung |
|---|---|---|---|
| GET | `/projects/` | Authenticated, scoped | Admin: tất cả; Manager/Employee: project tham gia |
| POST | `/projects/` | Admin, Manager | Creator lấy từ JWT và tự thành member |
| GET | `/projects/{id}/` | Project scoped | Chi tiết, member count, progress |
| PATCH | `/projects/{id}/` | Admin hoặc managing Manager | Sửa metadata/date |
| DELETE | `/projects/{id}/` | Admin hoặc managing Manager | Soft delete |
| GET | `/projects/{id}/members/` | Project scoped | Danh sách thành viên |
| POST | `/projects/{id}/members/` | Admin hoặc managing Manager | Body chứa `user_id` hoặc invite token flow |
| DELETE | `/projects/{id}/members/{user_id}/` | Admin hoặc managing Manager | Không được xóa creator khi chưa chuyển owner |

Project fields: `id`, `name`, `description`, `start_date`, `end_date`, `creator`, `member_count`, `progress`, `created_at`; start/end là date-only như UI hiện tại.

## Task metadata và tasks

| Method | Endpoint | Quyền | Nội dung |
|---|---|---|---|
| GET | `/metadata/task-statuses/` | Authenticated | `TODO`, `IN_PROGRESS`, `COMPLETED`, `ON_HOLD` |
| GET | `/tasks/` | Authenticated, scoped | Filter project/assignee/status/priority/deadline |
| POST | `/tasks/` | Admin hoặc managing Manager | Assignee phải là project member |
| GET | `/tasks/{id}/` | Task/project scoped | Chi tiết task |
| PATCH | `/tasks/{id}/` | Admin hoặc managing Manager | Sửa nội dung/giao việc/deadline |
| PATCH | `/tasks/{id}/status/` | Admin, managing Manager, assignee | Body dùng status code |
| DELETE | `/tasks/{id}/` | Admin hoặc managing Manager | Soft delete |

Employee chỉ thấy task được giao trong list mặc định và chỉ đổi trạng thái task của mình. Đây là thay đổi có chủ đích so với API cũ trả mọi task của project mà Employee tham gia.

Task fields: `id`, `title`, `description`, `project`, `assignee`, `status`, `priority`, `deadline`, `is_overdue`, `created_at`; deadline là date-only như UI hiện tại.

## Notifications

| Method | Endpoint | Quyền | Nội dung |
|---|---|---|---|
| GET | `/notifications/` | Authenticated | Chỉ notification của chính user |
| PATCH | `/notifications/{id}/read/` | Owner | Đánh dấu đã đọc |
| POST | `/notifications/read-all/` | Authenticated | Đánh dấu tất cả của user |

Không mở endpoint tạo notification tùy ý cho frontend. Notification được tạo nội bộ từ task/project service hoặc Admin-only command.

## Dashboard và reports

| Method | Endpoint | Quyền | Nội dung |
|---|---|---|---|
| GET | `/dashboard/summary/` | Authenticated, scoped | Project/task counts, overdue, distribution, recent tasks |
| GET | `/reports/workload/` | Admin, Manager scoped | Workload nhân viên |
| GET | `/reports/projects/{id}/` | Project scoped | Progress và task distribution |
| GET | `/reports/projects/{id}/top-contributors/` | Project scoped | Top contributors |
| POST | `/reports/messages/` | Project member | Sender lấy từ JWT |
| GET | `/reports/messages/` | Authenticated | Chỉ message gửi/nhận thuộc scope |
| PATCH | `/reports/messages/{id}/read/` | Receiver | Đánh dấu đã đọc |

## Authorization gate

Mỗi endpoint resource phải có test cho:

- anonymous;
- self/owner/assignee;
- cùng role nhưng khác project;
- role khác;
- object đã soft-delete;
- object không tồn tại.

Queryset phải được scope trước `retrieve/update/destroy`; không fetch object toàn cục rồi mới kiểm tra để tránh IDOR và lộ sự tồn tại của resource.
