# Task Management

Hệ thống quản lý dự án nội bộ, giao việc và theo dõi tiến độ dành cho ba vai trò: quản trị viên, quản lý và nhân viên.

## Công nghệ

- Frontend: React 19, TypeScript, Vite, Tailwind CSS
- Backend: Python 3.14, Django 5.2 LTS, Django REST Framework
- Cơ sở dữ liệu: PostgreSQL 18
- Xác thực: JWT, refresh token HttpOnly, CSRF và Argon2
- Triển khai: Docker Compose, Nginx, HTTPS

## Chức năng

- Đăng nhập, quản lý tài khoản nội bộ, hồ sơ cá nhân và ảnh đại diện
- Quản lý người dùng và phân quyền
- Quản lý dự án, thành viên và tiến độ
- Giao việc, lọc công việc, cập nhật trạng thái và lịch sử thay đổi có người thực hiện
- Thông báo, tùy chọn ưu tiên và nhắc hạn tự động trước 1 ngày/đã quá hạn
- Dashboard, báo cáo khối lượng và trao đổi báo cáo

## Chạy bằng Docker

```bash
docker compose -f infra/compose.dev.yaml up --build -d
docker compose -f infra/compose.dev.yaml exec backend python manage.py seed_demo
```

Service `scheduler` kiểm tra hạn công việc mỗi giờ. Có thể chạy thủ công một lần bằng:

```bash
docker compose -f infra/compose.dev.yaml exec backend python manage.py send_deadline_notifications
```

Truy cập:

- Ứng dụng React: <http://localhost:5174>
- Tài liệu API: <http://localhost:8010/api/docs/>
- Health check: <http://localhost:8010/health/>

Tài khoản phát triển:

| Vai trò | Tên đăng nhập | Mật khẩu |
|---|---|---|
| Quản trị viên | `admin` | `123` |
| Quản lý | `qltask` | `123` |
| Nhân viên | `user` | `123` |

## Cấu trúc

```text
backend/   Django REST API, migrations và test
frontend/  React SPA, component test và Playwright E2E
infra/     Docker Compose, Nginx và script PostgreSQL
```

## Kiểm thử

```bash
backend/.venv/Scripts/python.exe -m pytest backend
npm --prefix frontend run lint
npm --prefix frontend run test -- --run
npm --prefix frontend run build
```

## Dữ liệu mẫu

Lệnh `seed_demo` có thể chạy nhiều lần mà không nhân bản dữ liệu. Bộ dữ liệu gồm 3 tài khoản, 4 dự án, 10 thành viên dự án, 12 công việc, thông báo, tùy chọn và báo cáo mẫu bằng tiếng Việt.

Không sử dụng mật khẩu mẫu trong môi trường thật.

Đăng ký công khai mặc định bị tắt và luôn bị khóa trong production. Quản trị viên tạo tài khoản nội bộ tại màn hình quản lý người dùng.
