#!/bin/bash
# Карта мест занятий на своём домене: https://map.cooleso.ru/
#
# Сервер зеркалирует опубликованный релиз с GitHub Pages
# (https://crymoar.github.io/cooleso/map/): страница, схема, data/metro.json, data/places.csv.
# Данные по-прежнему правятся в репозитории (map/data/places.csv) и выходят релизом;
# сервер забирает новую версию сам, раз в 10 минут.
#
# Запуск (от root): bash setup.sh
# Скрипт можно запускать повторно: он ничего не ломает и доделывает недостающее
# (например, выпускает HTTPS-сертификат, когда заработает DNS-запись map → IP сервера).
set -euo pipefail

DOMAIN=${DOMAIN:-map.cooleso.ru}
SRC=${MAP_SRC:-https://crymoar.github.io/cooleso/map/}
WWW=/var/www/$DOMAIN

[ "$(id -u)" = 0 ] || { echo "Запустите от root"; exit 1; }

echo "== 1. nginx и certbot"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq nginx certbot python3-certbot-nginx >/dev/null

echo "== 2. скрипт обновления /usr/local/bin/map-update"
cat > /usr/local/bin/map-update <<EOF
#!/bin/bash
# Забирает опубликованную карту с GitHub Pages и, если что-то изменилось, подменяет её на сайте.
set -euo pipefail
SRC="$SRC"
WWW="$WWW"
EOF
cat >> /usr/local/bin/map-update <<'EOF'
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
mkdir -p "$TMP/data"
for f in index.html metro-scheme.svg data/metro.json data/places.csv; do
  curl -fsSR --retry 3 --max-time 60 -o "$TMP/$f" "$SRC$f"
done
# проверка, что пришло не что-то битое
grep -q 'name="app-version"' "$TMP/index.html"
python3 -c 'import json,sys;json.load(open(sys.argv[1]))' "$TMP/data/metro.json"
[ -s "$TMP/data/places.csv" ] && [ -s "$TMP/metro-scheme.svg" ]
if [ -e "$WWW/current" ] && diff -rq "$TMP" "$WWW/current/" >/dev/null; then exit 0; fi
NEW="$WWW/releases/$(date +%Y%m%d-%H%M%S)"
mkdir -p "$WWW/releases"
cp -a "$TMP" "$NEW"; chmod -R a+rX "$NEW"
ln -sfn "$NEW" "$WWW/current.tmp" && mv -Tf "$WWW/current.tmp" "$WWW/current"
ls -1dt "$WWW"/releases/* | tail -n +6 | xargs -r rm -rf   # храним 5 последних версий
echo "карта обновлена: $(grep -o 'name="app-version" content="[^"]*"' "$NEW/index.html")"
EOF
chmod +x /usr/local/bin/map-update
mkdir -p "$WWW"
/usr/local/bin/map-update

echo "== 3. автообновление раз в 10 минут (systemd timer map-update)"
cat > /etc/systemd/system/map-update.service <<'EOF'
[Unit]
Description=Обновить карту мест занятий с GitHub Pages
After=network-online.target
Wants=network-online.target
[Service]
Type=oneshot
ExecStart=/usr/local/bin/map-update
EOF
cat > /etc/systemd/system/map-update.timer <<'EOF'
[Unit]
Description=Обновлять карту мест занятий раз в 10 минут
[Timer]
OnBootSec=2min
OnUnitActiveSec=10min
[Install]
WantedBy=timers.target
EOF
systemctl daemon-reload
systemctl enable --now map-update.timer >/dev/null

echo "== 4. сайт nginx $DOMAIN"
if [ ! -f /etc/nginx/sites-available/$DOMAIN ]; then
cat > /etc/nginx/sites-available/$DOMAIN <<EOF
server {
    listen 80;
    listen [::]:80;
    server_name $DOMAIN;
    root $WWW/current;
    index index.html;
    charset utf-8;

    gzip on;
    gzip_types text/css application/javascript application/json image/svg+xml text/csv text/plain;

    # старый путь с GitHub Pages: /map/... → /...
    location ~ ^/map(/.*)?\$ { return 301 \$scheme://\$host\$1\$is_args\$args; }

    # страница и данные всегда свежие, схема кэшируется на час
    location = /index.html { add_header Cache-Control "no-cache"; }
    location /data/        { add_header Cache-Control "no-cache"; }
    location = /metro-scheme.svg { add_header Cache-Control "public, max-age=3600"; }
    location / { try_files \$uri \$uri/ =404; }
}
EOF
fi
ln -sf /etc/nginx/sites-available/$DOMAIN /etc/nginx/sites-enabled/$DOMAIN
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl enable --now nginx >/dev/null
systemctl reload nginx

echo "== 5. HTTPS"
if [ -d /etc/letsencrypt/live/$DOMAIN ]; then
  echo "сертификат уже есть"
elif getent hosts "$DOMAIN" >/dev/null; then
  certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos --register-unsafely-without-email --redirect
else
  echo "!! $DOMAIN пока не резолвится. Добавьте в DNS на Тильде A-запись: map → IP этого сервера,"
  echo "   подождите 5–30 минут и запустите этот скрипт ещё раз — он выпустит сертификат."
fi

echo "== готово"
systemctl list-timers map-update.timer --no-pager | head -2
curl -s -o /dev/null -w "http://localhost/ с Host: $DOMAIN → %{http_code}\n" -H "Host: $DOMAIN" http://127.0.0.1/
