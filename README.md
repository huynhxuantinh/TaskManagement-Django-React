# Task Management

Hệ thống quản lý dự án nội bộ, giao việc và theo dõi tiến độ dành cho ba vai trò: quản trị viên, quản lý và nhân viên.

## Công nghệ

- Frontend: React 19, TypeScript, Vite, Tailwind CSS
- Backend: Python 3.14, Django 5.2 LTS, Django REST Framework
- Cơ sở dữ liệu: PostgreSQL 18
- Xác thực: JWT, refresh token HttpOnly, CSRF và Argon2
- Triển khai: Docker Compose, Nginx, HTTPS

## Chức năng

- Đăng nhập, đăng ký, hồ sơ cá nhân và ảnh đại diện
- Quản lý người dùng và phân quyền
- Quản lý dự án, thành viên và tiến độ
- Giao việc, lọc công việc và cập nhật trạng thái
- Thông báo và tùy chọn nhận thông báo
- Dashboard, báo cáo khối lượng và trao đổi báo cáo

## Chạy bằng Docker

```bash
docker compose -f infra/compose.dev.yaml up --build -d
docker compose -f infra/compose.dev.yaml exec backend python manage.py seed_demo
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
