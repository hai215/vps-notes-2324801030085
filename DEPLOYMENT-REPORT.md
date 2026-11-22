# Bài cá nhân 2 – Biên bản triển khai

## Thông tin máy

- MSSV: 2324801030085
- VPS: `vps-2324801030085`
- Hệ điều hành: Ubuntu Server 24.04 LTS
- IP nội bộ: `192.168.64.10/24`
- Mạng host-only VMware VMnet1: `192.168.64.0/24`
- Truy cập ứng dụng từ laptop: `http://192.168.64.10`

## Kiến trúc

Laptop Windows → VMware Workstation → Ubuntu VPS → Nginx (80) → Gunicorn/Flask (`127.0.0.1:8000`) → PostgreSQL (`127.0.0.1:5432`).

Ứng dụng là **VPS Notes**: đăng ký, đăng nhập, mật khẩu băm bằng Werkzeug, và CRUD ghi chú. Mỗi ghi chú chỉ được truy cập bởi người dùng sở hữu.

## Dịch vụ đã bật

- `vps-notes.service`: Gunicorn, tự khởi động, bind `127.0.0.1:8000`.
- `postgresql.service`: PostgreSQL, chỉ listen `127.0.0.1:5432`.
- `nginx.service`: reverse proxy cổng 80.
- `.env` thật nằm ngoài Git tại `/etc/vps-notes.env`, quyền 600.
- DB dùng user riêng `vps_notes_user` và database `vps_notes`.

## Tường lửa

UFW đã bật:

```text
Default: deny (incoming), allow (outgoing)
22/tcp  ALLOW IN  192.168.64.0/24
80/tcp  ALLOW IN  192.168.64.0/24
```

Cổng 8000 và 5432 không mở ra mạng ảo.

## Kiểm thử

Đã kiểm thử thành công bằng HTTP:

1. Đăng ký tài khoản.
2. Đăng nhập.
3. Thêm ghi chú.
4. Sửa ghi chú.
5. Xóa ghi chú.
6. Xóa tài khoản kiểm thử sau khi hoàn tất.

Đã tạo snapshot VMware:

```text
Bai2-hoan-thanh-Flask-PostgreSQL-Nginx-UFW
```

## Lệnh minh chứng để chụp ảnh

Chạy trên VPS:

```bash
systemctl is-active vps-notes nginx postgresql
ss -tlnp
sudo ufw status verbose
```

Chạy trên laptop:

```powershell
Test-NetConnection 192.168.64.10 -Port 80
ssh -i "$env:USERPROFILE\.ssh\vps-student_ed25519" student@192.168.64.10
```

Mở trình duyệt laptop tại `http://192.168.64.10`, đăng ký tài khoản thử và quay thao tác thêm–sửa–xóa.

## Ghi chú GitHub

Project không chứa `.env` thật hoặc mật khẩu. Khởi tạo Git cục bộ tại commit `5191b8d`. Cần tạo repository GitHub của sinh viên rồi chạy:

```bash
git remote add origin https://github.com/<tai-khoan>/<repo>.git
git branch -M main
git push -u origin main
```
