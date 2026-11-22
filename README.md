# VPS Notes

Ứng dụng ghi chú cá nhân tối giản cho bài triển khai web trên VPS. Backend dùng **Python Flask**, template **Jinja2**, PostgreSQL qua **psycopg 3** và Gunicorn. Mỗi `Note` luôn được truy vấn với `user_id` của phiên đăng nhập hiện tại.

## Tính năng và cấu trúc

- Đăng ký, đăng nhập, đăng xuất; mật khẩu được băm bằng `werkzeug.security`.
- CRUD `Note`: tạo, danh sách, xem chi tiết, sửa và xóa.
- CSRF cơ bản: token ngẫu nhiên trong session, bắt buộc cho mọi request `POST`.
- Giao diện Jinja2 responsive, CSS thuần, không dùng JavaScript framework.
- Mặc định Gunicorn bind tại `127.0.0.1:8000`; Nginx đứng phía trước.

```text
bai2-vps/
├── app/
│   ├── __init__.py       # app factory, cấu hình và CSRF
│   ├── auth.py           # đăng ký/đăng nhập/đăng xuất
│   ├── db.py             # kết nối psycopg theo request
│   ├── notes.py          # CRUD Note, giới hạn theo user hiện tại
│   ├── static/style.css
│   └── templates/        # Jinja2 templates
├── nginx/vps-notes.conf.example
├── systemd/vps-notes.service.example
├── schema.sql
├── wsgi.py
├── requirements.txt
└── .env.example
```

## Chạy local từ đầu

Các lệnh dưới đây dành cho Ubuntu 24.04. Có thể thay `/var/www/vps-notes` bằng thư mục checkout khác khi phát triển.

### 1. Cài gói hệ thống và PostgreSQL

```bash
sudo apt update
sudo apt install -y python3-venv python3-dev libpq-dev build-essential \
  postgresql postgresql-contrib
```

Tạo database và user riêng (thay các giá trị `REPLACE_...`, không dùng nguyên văn trong production):

```bash
sudo -u postgres psql
```

```sql
CREATE USER vps_notes_user WITH PASSWORD 'REPLACE_WITH_LONG_RANDOM_PASSWORD';
CREATE DATABASE vps_notes OWNER vps_notes_user;
\q
```

Password PostgreSQL trong `DATABASE_URL` nên được URL-encode nếu chứa ký tự đặc biệt. Có thể chọn password hex từ `openssl rand -hex 32` để không phải encode.

### 2. Tạo virtualenv và cài dependency

```bash
cd /var/www/vps-notes
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
cp .env.example .env
chmod 600 .env
```

Sửa `.env` và đặt giá trị thật của máy triển khai:

```dotenv
SECRET_KEY=REPLACE_WITH_OUTPUT_OF_openssl_rand_-hex_32
DATABASE_URL=postgresql://vps_notes_user:URL_ENCODED_PASSWORD@127.0.0.1:5432/vps_notes
SESSION_COOKIE_SECURE=false
```

`SECRET_KEY` và password database trong ví dụ chỉ là placeholder, không commit file `.env`. Tạo schema bằng CLI của app:

```bash
set -a
. ./.env
set +a
.venv/bin/flask --app app init-db
```

Hoặc dùng trực tiếp `psql "$DATABASE_URL" -f schema.sql` sau khi export `DATABASE_URL` trong shell. User database phải là owner hoặc có quyền tạo bảng.

### 3. Chạy thử

```bash
.venv/bin/gunicorn --bind 127.0.0.1:8000 wsgi:app
```

Mở `http://127.0.0.1:8000` trên VPS (hoặc dùng SSH tunnel). Khi phát triển, có thể dùng `flask --app app run --host 127.0.0.1 --port 8000`.

## Deploy bằng systemd + Nginx

### 1. Tạo user chạy service và đặt mã nguồn

```bash
sudo adduser --system --group --home /var/www/vps-notes vpsnotes
sudo mkdir -p /var/www/vps-notes
sudo chown -R vpsnotes:vpsnotes /var/www/vps-notes
# Copy/checkout project vào /var/www/vps-notes rồi kiểm tra owner:
sudo chown -R vpsnotes:vpsnotes /var/www/vps-notes
```

Cài virtualenv và dependency bằng user service:

```bash
sudo -u vpsnotes python3 -m venv /var/www/vps-notes/.venv
sudo -u vpsnotes /var/www/vps-notes/.venv/bin/pip install --upgrade pip
sudo -u vpsnotes /var/www/vps-notes/.venv/bin/pip install -r /var/www/vps-notes/requirements.txt
```

Tạo file biến môi trường riêng cho systemd, chỉ root được đọc:

```bash
sudo install -o root -g root -m 600 /dev/null /etc/vps-notes.env
sudoedit /etc/vps-notes.env
```

Nội dung mẫu (thay toàn bộ placeholder):

```dotenv
SECRET_KEY=REPLACE_WITH_LONG_RANDOM_VALUE
DATABASE_URL=postgresql://vps_notes_user:URL_ENCODED_PASSWORD@127.0.0.1:5432/vps_notes
SESSION_COOKIE_SECURE=false
```

Sau khi trỏ domain và bật HTTPS, đổi `SESSION_COOKIE_SECURE=true`. Khởi tạo schema một lần bằng chính user database, ví dụ chạy trong shell quản trị với URL tương ứng:

```bash
export DATABASE_URL='postgresql://vps_notes_user:URL_ENCODED_PASSWORD@127.0.0.1:5432/vps_notes'
sudo -u vpsnotes env DATABASE_URL="$DATABASE_URL" bash -c \
  'cd /var/www/vps-notes && .venv/bin/flask --app app init-db'
unset DATABASE_URL
```

### 2. Bật systemd

```bash
sudo cp /var/www/vps-notes/systemd/vps-notes.service.example \
  /etc/systemd/system/vps-notes.service
sudo systemctl daemon-reload
sudo systemctl enable --now vps-notes
sudo systemctl status vps-notes
journalctl -u vps-notes -f
```

Service chỉ lắng nghe `127.0.0.1:8000`, không mở cổng ứng dụng ra Internet. Nếu đổi đường dẫn cài đặt, sửa `WorkingDirectory` và `ExecStart` trong unit.

### 3. Cấu hình Nginx reverse proxy

```bash
sudo cp /var/www/vps-notes/nginx/vps-notes.conf.example \
  /etc/nginx/sites-available/vps-notes
sudoedit /etc/nginx/sites-available/vps-notes  # đổi server_name thành domain thật
sudo ln -s /etc/nginx/sites-available/vps-notes /etc/nginx/sites-enabled/vps-notes
sudo nginx -t
sudo systemctl reload nginx
```

Sau khi DNS trỏ đúng, nên cấp HTTPS (ví dụ `sudo apt install certbot python3-certbot-nginx` rồi chạy Certbot), kiểm tra tự động gia hạn và bật `SESSION_COOKIE_SECURE=true`. Không dùng domain mẫu `notes.example.com` trên máy thật.

## UFW và SSH

Chỉ cho phép SSH, HTTP và HTTPS; thay `22` bằng cổng SSH riêng nếu đã cấu hình:

```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp comment 'SSH'
sudo ufw allow 80/tcp comment 'HTTP'
sudo ufw allow 443/tcp comment 'HTTPS'
sudo ufw enable
sudo ufw status verbose
```

Trước khi bật UFW, bảo đảm phiên SSH hiện tại và một phiên dự phòng hoạt động. Với SSH production: dùng key thay vì password, tắt đăng nhập root (`PermitRootLogin no`), cân nhắc `PasswordAuthentication no` sau khi kiểm tra key, giới hạn user được SSH và cập nhật hệ thống thường xuyên. Không mở trực tiếp cổng `8000` hoặc PostgreSQL `5432` trên firewall; PostgreSQL chỉ cần listen local nếu app và DB cùng VPS.

## Biến môi trường

- `SECRET_KEY`: chuỗi ngẫu nhiên dài để ký Flask session; bắt buộc thay placeholder trong production.
- `DATABASE_URL`: URL kết nối PostgreSQL của user database riêng.
- `SESSION_COOKIE_SECURE`: `false` cho HTTP local; đặt `true` sau khi Nginx có HTTPS.

Nếu service lỗi, xem `journalctl -u vps-notes`, kiểm tra quyền đọc `/etc/vps-notes.env`, kết nối `DATABASE_URL`, schema và cổng `127.0.0.1:8000`. Không đưa secret thật vào source, Git, README, file `.example` hoặc log.
