# Repository hygiene inventory

Ngày kiểm kê: 2026-10-18

Repository: `D:\download\DALQ\TaskManagement_09`

Branch: `main` (ahead `origin/main` 4 commit khi kiểm kê)

Execution mode: Direct mode; stage theo đường dẫn, không tự push.

## Trạng thái phát hiện

| Nhóm | File đang được Git track |
|---|---:|
| `node_modules/` | 2.384 |
| `bin/` và `obj/` | 413 |
| `.vs/` | 10 |
| `.env` | 0 |
| Media/avatar | 2 |

Ngoài ra có các artifact build chưa track và một avatar runtime chưa track tại
`TaskManagement.API/wwwroot/avatars/42_639279420135787511.jpg`.

API và Web vẫn đang lắng nghe lần lượt tại cổng `5129` và `5200` khi kiểm kê.

## Thay đổi an toàn đã thực hiện

- Thêm `.gitignore` cho Python, Django, Node, React, .NET, IDE, secrets,
  coverage, runtime uploads, exports, backups và logs.
- Không xóa file, không bỏ track file, không dừng dịch vụ và không sửa dữ liệu.
- File đã được Git track vẫn giữ nguyên cho đến khi người dùng xác nhận cleanup.

## Cleanup đã hoàn thành

Sau khi người dùng chấp thuận, commit `4687043` đã:

1. Bỏ track 2.800 file trong `node_modules/`, `bin/`, `obj/` và `.vs/`.
2. Giữ toàn bộ file trên máy; không xóa vật lý.
3. Giữ hai avatar cũ trong Git cho đến khi xác định rõ nguồn dữ liệu.
4. Xác minh solution build 0 lỗi và 2 test seed đều pass.
5. Xác minh không còn artifact thuộc các nhóm trên được Git track.

## Quy tắc cho các bước migration

- Chỉ stage đúng path thuộc bước hiện tại.
- Không commit `.env`, database dump, password hash export, media runtime hoặc log.
- Dữ liệu export phải nằm trong `exports/` và được mã hóa nếu rời máy local.
- Không dùng `git clean`, `git reset --hard` hoặc cleanup đệ quy khi chưa xác minh target.
