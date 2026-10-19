# TaskManagement_09

## Giới thiệu

TaskManagement_09 là hệ thống quản lý công việc và dự án được xây dựng bằng **ASP.NET Core**.

Dự án hỗ trợ quản lý công việc theo nhóm, phân chia nhiệm vụ, theo dõi tiến độ, thống kê báo cáo và hỗ trợ cộng tác hiệu quả trong môi trường làm việc hoặc học tập.

Đây là dự án được xây dựng nhằm rèn luyện kỹ năng phát triển phần mềm full-stack, thiết kế hệ thống và triển khai kiến trúc backend thực tế.

> **Trạng thái migration:** stack mới `React + Django REST Framework + PostgreSQL` trong `frontend/`, `backend/`, `infra/` đã hoàn thành chức năng và E2E. Stack ASP.NET/SQL Server được giữ làm đối chiếu đến bước cutover S11.

Chạy môi trường mới:

```bash
docker compose -f infra/compose.dev.yaml up --build -d
docker compose -f infra/compose.dev.yaml exec backend python manage.py seed_demo
```

- React: `http://localhost:5174`
- Django API: `http://localhost:8010/api/docs/`
- Tài khoản demo: `admin1@task.com / Admin@123`, `manager1@task.com / Manager@123`, `employee1@task.com / Employee@123`

Các hành vi legacy đã loại bỏ: nhận diện Starbucks, frontend tự tạo notification tùy ý và invite bằng mật khẩu cố định.

---

## Chức năng chính

### Quản lý người dùng

* Đăng nhập / Đăng xuất
* Quản lý thông tin cá nhân
* Cập nhật avatar
* Thiết lập tùy chọn người dùng

---

### Quản lý dự án

* Tạo dự án mới
* Chỉnh sửa thông tin dự án
* Theo dõi trạng thái dự án
* Quản lý thành viên tham gia

---

### Quản lý công việc

* Tạo công việc
* Cập nhật trạng thái
* Phân công cho thành viên
* Thiết lập deadline
* Tìm kiếm và lọc công việc

---

### Quản lý nhóm

* Thêm / xóa thành viên
* Phân quyền nhiệm vụ
* Theo dõi hiệu suất làm việc

---

### Hệ thống thông báo

* Thông báo cập nhật công việc
* Theo dõi hoạt động dự án

---

### Báo cáo và thống kê

* Thống kê tiến độ
* Báo cáo hiệu suất
* Tổng quan công việc

---

### Dashboard

Hiển thị:

* Tổng số dự án
* Tổng số công việc
* Công việc đang xử lý
* Công việc hoàn thành
* Tiến độ tổng quan

---

## Kiến trúc hệ thống

Dự án gồm 2 phần chính:

### TaskManagement.API

Backend xử lý:

* Business Logic
* REST API
* Database
* Authentication
* Notification
* Report

---

### TaskManagement.Web

Frontend MVC xử lý:

* Giao diện người dùng
* Dashboard
* Quản lý dự án
* Quản lý công việc
* Tương tác với API

---

## Công nghệ sử dụng

### Backend

* ASP.NET Core Web API
* Entity Framework Core
* SQL Server
* AutoMapper

---

### Frontend

* ASP.NET Core MVC
* Razor View
* Bootstrap
* Tailwind CSS

---

### Kiến trúc áp dụng

* Repository Pattern
* Service Layer
* DTO Mapping
* Middleware Exception Handling

---

### Công cụ

* Visual Studio 2022
* Git
* GitHub

---

## Cấu trúc thư mục

```id="6g5x0l"
TaskManagement_09
│
├── TaskManagement.API
│   ├── Controllers
│   ├── Services
│   ├── Repositories
│   ├── DTOs
│   ├── Middleware
│   ├── Data
│   └── Models
│
├── TaskManagement.Web
│   ├── Controllers
│   ├── Views
│   ├── Services
│   ├── Models
│   └── wwwroot
│
└── TaskManagementSolution.slnx
```

---

## Cơ sở dữ liệu

Sử dụng:

* SQL Server
* Entity Framework Core
* Code First Migration

Các bảng chính:

* User
* Project
* Task
* Notification
* Report
* ProjectMember

---

## Cách chạy dự án

### Clone project

```bash id="wgl1iq"
git clone https://github.com/DIIX-Program/TaskManagement_09.git
```

---

### Restore package

```bash id="6jxv8n"
dotnet restore
```

---

### Cập nhật database

```bash id="pxfygl"
dotnet ef database update
```

---

### Chạy API

```bash id="d4evpt"
dotnet run --project TaskManagement.API
```

---

### Chạy Web

```bash id="v7d0ca"
dotnet run --project TaskManagement.Web
```

---

## Mục tiêu học tập

Dự án được thực hiện nhằm:

* Thực hành ASP.NET Core
* Xây dựng REST API
* Làm việc với Entity Framework Core
* Thiết kế hệ thống quản lý thực tế
* Áp dụng mô hình kiến trúc phần mềm
* Làm quen quy trình Git/GitHub

---

## Hướng phát triển

Trong tương lai có thể mở rộng:

* JWT Authentication
* SignalR Realtime Notification
* Kanban Board
* Upload file đính kèm
* Email Notification
* Role-based Access Control

---

## Tác giả

**DIIX Program**
Sinh viên năm 3 ngành Công nghệ thông tin
Mục tiêu trở thành Software Engineer thông qua việc xây dựng các hệ thống thực tế.
