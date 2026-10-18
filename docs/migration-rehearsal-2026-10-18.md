# Biên bản migration rehearsal — 2026-10-18

## Phạm vi

- Nguồn: SQL Server `TaskManagementFinalDB`, kết nối `ApplicationIntent=ReadOnly`.
- Đích: PostgreSQL 18 trên volume dev mới hoàn toàn.
- Timestamp nguồn được hiểu là `Asia/Saigon` và chuyển sang UTC.
- Export payload/media được mã hóa AES-256-GCM; khóa chỉ tồn tại trong tiến trình rehearsal.

## Kết quả đối soát

| Bảng | Số dòng | SHA-256 canonical |
|---|---:|---|
| roles | 3 | `e3bfa00ebce56bac60dc4ba2bf3360c8bcead786a4fe63302d9ed7ef10fa3079` |
| users | 44 | `3a9ebf13c5f91a5edee2e38afd81e638c0da23d30652bb918ad5534a0144d7d0` |
| projects | 2 | `a9f129fdfdebf56b7658bf3210f5b09bf83349e36de04126297c1c242e9d5719` |
| project_members | 12 | `316dbe7a3f5012885b0584742fceedeecc21fb73a4cb83638dbcc3f55c5a3a93` |
| task_statuses | 4 | `89880433500a4fbd6060fba165018032a1ae3022052cfc7cca99d996d2240960` |
| tasks | 6 | `89d3b4d03f7448f6baa6779003017fd901b4601bfbf21e513b7834118b3f5fda` |
| notifications | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| preferences | 4 | `3dac075ebac83aad6f3c7ef7a66e812f1466ee49028a98771ff076de2f4b05b0` |
| reports | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |

- Email trùng: 0.
- Preference trùng: 0.
- Bản ghi mồ côi: 0.
- Media: 1 avatar, checksum `fe76d28c1f050c4972d5d918e1e7842f00bf0e0bd4c412d655ecc11a37d63dac` khớp sau import.
- Manifest của exporter độc lập khớp hoàn toàn với rehearsal ban đầu.
- Dry-run thành công; import lần 1 và lần 2 đều `manifest_verified=true`, không tăng số dòng.
- Hash dữ liệu PostgreSQL sau import khớp toàn bộ manifest nguồn.
- FK hợp lệ do import transaction hoàn tất; mọi sequence PostgreSQL đều lớn hơn hoặc bằng PK lớn nhất.

## Kiểm thử

- `makemigrations --check --dry-run`: không có thay đổi.
- `manage.py check`: không có lỗi.
- Backend: 11 test đạt, coverage 85.08%.
- Exporter: 3 test đạt; restore/build không còn cảnh báo package vulnerability.

Bundle rehearsal chứa dữ liệu thật đã được xóa sau khi đối soát; chỉ giữ biên bản không chứa PII này trong Git.
