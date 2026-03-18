# Deploy on Timeweb (Ubuntu + Nginx + Daphne)

## 1. Server packages
```bash
sudo apt update
sudo apt install -y python3-venv python3-pip git nginx redis-server postgresql postgresql-contrib
```

## 2. PostgreSQL
```bash
sudo -u postgres psql
```
```sql
CREATE DATABASE maxschool_prod;
CREATE USER maxschool_user WITH PASSWORD 'CHANGE_ME_STRONG_PASSWORD';
ALTER ROLE maxschool_user SET client_encoding TO 'utf8';
ALTER ROLE maxschool_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE maxschool_user SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE maxschool_prod TO maxschool_user;
\q
```

## 3. Project setup
```bash
cd /opt
sudo git clone <YOUR_PRIVATE_REPO_URL> maxschool
sudo chown -R $USER:$USER /opt/maxschool
cd /opt/maxschool
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## 4. Environment
```bash
cp .env.prod.example .env
nano .env
```

Minimum required values:
- `DJANGO_SECRET_KEY`
- `DJANGO_ALLOWED_HOSTS`
- `DJANGO_CSRF_TRUSTED_ORIGINS`
- `DATABASE_URL`
- `DJANGO_EMAIL_HOST_PASSWORD`
- `JAAAS_*`
- `REDIS_URL`

## 5. Django commands
```bash
source /opt/maxschool/.venv/bin/activate
python maxschool/manage.py migrate
python maxschool/manage.py collectstatic --noinput
python maxschool/manage.py check --deploy
python maxschool/manage.py createsuperuser
```

## 6. Daphne systemd service
Create `/etc/systemd/system/maxschool-daphne.service`:

```ini
[Unit]
Description=MaxSchool Daphne ASGI server
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/opt/maxschool/maxschool
EnvironmentFile=/opt/maxschool/.env
ExecStart=/opt/maxschool/.venv/bin/daphne -b 127.0.0.1 -p 8001 maxschool.asgi:application
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now maxschool-daphne
sudo systemctl status maxschool-daphne
```

## 7. Nginx
Create `/etc/nginx/sites-available/maxschool`:

```nginx
server {
    listen 80;
    server_name smarturok.ru www.smarturok.ru;

    client_max_body_size 25M;

    location /static/ {
        alias /opt/maxschool/maxschool/staticfiles/;
    }

    location /media/ {
        alias /opt/maxschool/maxschool/media/;
    }

    location / {
        proxy_pass http://127.0.0.1:8001;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/maxschool /etc/nginx/sites-enabled/maxschool
sudo nginx -t
sudo systemctl reload nginx
```

## 8. SSL (Let's Encrypt)
```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d smarturok.ru -d www.smarturok.ru
```

## 9. Update release
```bash
cd /opt/maxschool
git pull
source .venv/bin/activate
pip install -r requirements.txt
python maxschool/manage.py migrate
python maxschool/manage.py collectstatic --noinput
sudo systemctl restart maxschool-daphne
sudo systemctl reload nginx
```
