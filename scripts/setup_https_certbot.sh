#!/usr/bin/env bash
# Obtain Let's Encrypt certs for SENTINEL X (run on the cloud VM after DNS points here).
# Usage: DOMAIN=example.com EMAIL=you@example.com ./scripts/setup_https_certbot.sh
set -euo pipefail

DOMAIN="${DOMAIN:-}"
EMAIL="${EMAIL:-}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ -z "$DOMAIN" || -z "$EMAIL" ]]; then
  echo "Usage: DOMAIN=your.domain EMAIL=you@email.com $0"
  exit 1
fi

echo "Starting temporary HTTP challenge helper..."
docker compose -f docker-compose.prod.yml --env-file .env.cloud up -d nginx

docker run --rm -it \
  -v sentinel_x_prod_certbot_www:/var/www/certbot \
  -v sentinel_x_prod_certbot_certs:/etc/letsencrypt \
  -p 80:80 \
  certbot/certbot certonly --webroot -w /var/www/certbot \
  -d "$DOMAIN" --email "$EMAIL" --agree-tos --no-eff-email || \
docker run --rm -it \
  -v sentinel_x_prod_certbot_certs:/etc/letsencrypt \
  -p 80:80 \
  certbot/certbot certonly --standalone \
  -d "$DOMAIN" --email "$EMAIL" --agree-tos --no-eff-email

echo "Copying certs into nginx certs volume layout..."
docker run --rm \
  -v sentinel_x_prod_certbot_certs:/etc/letsencrypt \
  -v sentinel_x_prod_certbot_certs:/out \
  alpine sh -c "cp -L /etc/letsencrypt/live/${DOMAIN}/fullchain.pem /out/fullchain.pem; cp -L /etc/letsencrypt/live/${DOMAIN}/privkey.pem /out/privkey.pem"

echo "Next: uncomment the TLS server block in docker/nginx/nginx.prod.conf,"
echo "set FRONTEND_ORIGIN=https://${DOMAIN} in .env.cloud, then ./update-cloud.sh"
