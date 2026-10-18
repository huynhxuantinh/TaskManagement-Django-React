# Functional parity checklist

Quy ước:

- **Preserve**: giữ hành vi nghiệp vụ.
- **Repair**: giữ mục tiêu nhưng sửa hành vi lỗi/không an toàn.
- **Drop**: loại khỏi phạm vi Task Management.

## Authentication và tài khoản

| Chức năng hiện tại | Quyết định | Acceptance criteria mới |
|---|---|---|
| Login bằng email/password, lưu MVC session | Repair | JWT access + refresh cookie; logout revoke được token |
| Register mặc định Employee | Preserve | Role lấy theo code `EMPLOYEE`, không hard-code DB ID |
| BCrypt.Net password | Repair | Hash cũ đăng nhập được một lần và tự rehash Argon2 |
| Update profile chỉ đổi Session, không cập nhật DB | Repair | `full_name` lưu DB và phản ánh sau reload |
| Upload avatar không kiểm tra file | Repair | MIME/size/name/path được kiểm tra; URL lưu DB |
| Notification preferences | Preserve | Upsert idempotent; unique `(user, type)` |
| ChangePassword là mock | Repair | Xác minh mật khẩu cũ, đổi hash, revoke refresh sessions |
| Deactivate chỉ clear Session | Repair | Soft deactivate DB, revoke token, chặn login |

## Team và phân quyền

| Chức năng hiện tại | Quyết định | Acceptance criteria mới |
|---|---|---|
| Admin/Manager/Employee | Preserve | Code ổn định, permission từ JWT |
| UpdateRole hard-code ID `1/2/3` | Repair | Lookup role bằng code; chỉ Admin được đổi |
| Team list công khai cho mọi session | Repair | Admin thấy toàn bộ; Manager chỉ thấy người trong project scope |
| Invite tạo account với `Starbucks@123` | Repair | Invite token một lần hoặc Admin tạo user với reset-password flow; không password cố định |
| CheckIn chỉ hiển thị thông báo giả | Drop | Ngoài phạm vi quản lý dự án/công việc |

## Projects và members

| Chức năng hiện tại | Quyết định | Acceptance criteria mới |
|---|---|---|
| Project CRUD | Preserve | Soft delete, date validation, scoped list/detail |
| Creator tự được thêm làm member | Preserve | Transaction đảm bảo creator-member invariant |
| Manager sửa project nếu chỉ là member | Repair | Chỉ managing Manager/creator hoặc Admin |
| Add member theo ID/email | Preserve | Chống trùng, project scope, audit được actor |
| Remove member không kiểm tra quyền | Repair | Chỉ Admin/managing Manager; bảo vệ creator và active assignment |
| Search/filter project ở UI | Preserve | Server-side search/filter + pagination |

## Tasks và notifications

| Chức năng hiện tại | Quyết định | Acceptance criteria mới |
|---|---|---|
| Task CRUD, priority, deadline, status | Preserve | Validation và authorization server-side |
| Employee thấy mọi task thuộc project tham gia | Repair | List mặc định chỉ task được giao; không đọc task ngoài scope |
| Manager/Employee đều có thể create/update nếu là member | Repair | Employee không create/edit/delete; chỉ đổi status task được giao |
| Status dùng số ID | Repair | API và business logic dùng code, không hard-code `StatusId == 3` |
| Assignee phải là project member | Preserve | Enforce trong transaction và test conflict |
| Notification khi giao/status task | Preserve | Tạo atomically, có type và owner scope |
| Frontend có thể POST notification tùy ý | Drop | Chỉ domain service/Admin command tạo notification |
| Search/filter task | Preserve | Server-side theo project, assignee, status, priority, deadline |

## Dashboard, reports và giao diện

| Chức năng hiện tại | Quyết định | Acceptance criteria mới |
|---|---|---|
| Dashboard count/recent tasks | Preserve | Dữ liệu scoped theo JWT role |
| Workload report hard-code completed status ID | Repair | Dùng status code `COMPLETED` |
| Project progress/distribution | Preserve | Kết quả đối chiếu fixture và không chia cho 0 |
| Top contributors | Preserve | Chỉ project scoped |
| Report messages | Preserve | Sender từ JWT; chỉ sender/receiver đọc theo policy |
| Starbucks branding | Drop | Design system trung tính cho quản lý phần mềm nội bộ |
| Razor MVC UI | Replace | React responsive, accessible, có loading/error/empty state |

## Definition of parity complete

- Mọi dòng `Preserve/Repair` có backend test và UI/E2E tương ứng.
- Ba hành trình Admin, Manager, Employee chạy xanh trên PostgreSQL seed data.
- Gọi API trực tiếp vẫn trả `403/404` đúng khi UI đã ẩn action.
- Chức năng `Drop` không còn route/menu trong React và được ghi trong README migration.
- Count/hash/FK/media checksum sau import khớp manifest hoặc có exception được duyệt.
