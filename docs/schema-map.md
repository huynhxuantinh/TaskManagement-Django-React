# SQL Server → PostgreSQL schema map

## Baseline ngày 2026-10-18

| Entity | Số bản ghi |
|---|---:|
| Roles | 3 |
| Users | 44 |
| Projects | 2 |
| ProjectMembers | 12 |
| TaskStatuses | 4 |
| Tasks | 6 |
| Notifications | 0 |
| UserNotificationPreferences | 4 |
| Reports | 0 |

Kết quả kiểm tra: 0 email trùng không phân biệt hoa thường, 0 preference trùng và 0 orphan FK trong các bảng được kiểm tra.

Legacy Role IDs hiện là `4/5/6`; TaskStatus IDs là `5/6/7/8`. Code ASP.NET vẫn có chỗ hard-code role `1/2/3` và completed status `3`, vì vậy migration tuyệt đối không dựa vào các ID này.

## Mapping chính

### Roles → `accounts_role`

| SQL Server | PostgreSQL | Quy tắc |
|---|---|---|
| `RoleId` | `legacy_id` | Giữ để audit, không dùng cho permission |
| `RoleName` | `code`, `name` | `ADMIN`, `MANAGER`, `EMPLOYEE`; code unique |

### Users → custom `accounts_user`

| SQL Server | PostgreSQL | Quy tắc |
|---|---|---|
| `UserId` | `id` | Giữ PK khi import, reset sequence sau import |
| `FullName` | `full_name` | Bắt buộc, tối đa 100 |
| `Email` | `email` | Normalize lowercase; unique không phân biệt hoa thường |
| `PasswordHash` | `password` | Adapter BCrypt legacy; rehash Argon2 sau login |
| `RoleId` | `role_id` | Map qua RoleName/code, không map bằng ID cứng |
| `IsDeleted` | `is_active` | `is_active = !IsDeleted` |
| `CreatedAt` | `created_at` | Giả định legacy `Asia/Saigon`, chuyển UTC |
| `AvatarUrl` | `avatar` | Copy media + SHA-256; nullable |

Dùng custom User ngay migration đầu; `USERNAME_FIELD = email`. `is_staff/is_superuser` không thay thế domain role; chỉ Admin được map vào Django admin theo policy riêng.

### Projects → `projects_project`

- Giữ `ProjectId` làm `id`, rồi reset sequence.
- `name` max 200, `description` max 500.
- `start_date/end_date`: PostgreSQL `date`; UI legacy chỉ nhập và hiển thị ngày.
- `creator_id` RESTRICT; creator bắt buộc có membership.
- `is_deleted`, `created_at`; index cho creator và active projects.

### ProjectMembers → `projects_projectmember`

- Giữ legacy `Id` làm `id`.
- FK Project/User; unique `(project_id, user_id)`.
- `joined_at` chuyển UTC.
- Không cho xóa creator membership khi chưa transfer ownership.

### TaskStatuses → `tasks_taskstatus`

| Legacy name | Stable code |
|---|---|
| To Do | `TODO` |
| In Progress | `IN_PROGRESS` |
| Completed | `COMPLETED` |
| On Hold | `ON_HOLD` |

Giữ legacy ID ở `legacy_id`; mọi query/report dùng `code`.

### Tasks → `tasks_task`

- Giữ `TaskId` làm `id`; FK Project, optional assignee, TaskStatus.
- `priority` có check constraint `1..3`.
- `deadline` dùng PostgreSQL `date`; UI legacy chỉ nhập và hiển thị ngày.
- `is_deleted`, `created_at`; indexes cho project/status/assignee/deadline/active.
- Assignee phải là active member của project tại tầng service/transaction.

### Notifications → `notifications_notification`

- Type code: `GENERAL`, `TASK_ASSIGNED`, `STATUS_CHANGED`, `PROJECT_ADDED`, `DEADLINE_APPROACHING`.
- FK owner User, message max 255, `is_priority`, `is_read`, `created_at`.
- Index `(user_id, is_read, created_at)`.

### UserNotificationPreferences → `notifications_preference`

- FK User + notification type code; unique `(user_id, type)`.
- `is_priority` giữ nguyên.

### Reports → `reports_reportmessage`

- Giữ `ReportId` làm `id`.
- FK Project/Sender/Receiver; sender/receiver RESTRICT, project CASCADE theo legacy.
- Title max 200, content text, `is_read`, `created_at`.

## Import invariants

- Export chỉ đọc SQL Server và sinh manifest counts + canonical row hashes.
- Import chạy trong transaction, có `--dry-run`, không nhân bản khi chạy lại.
- Sau giữ PK phải reset toàn bộ PostgreSQL sequences.
- Báo lỗi trước import nếu duplicate email/preference, orphan FK hoặc status/role không map được.
- Không commit dump, password hashes hoặc runtime media; lưu dưới `exports/` đã ignore.
- Timezone legacy tạm xác định là `Asia/Saigon`; cần xác nhận trước final import.
