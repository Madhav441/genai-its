#!/usr/bin/env bash
set -euo pipefail

SLOT="${1:-}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="${SCRIPT_DIR}/compose.blue-green.yml"
NGINX_DIR="${SCRIPT_DIR}/nginx"

if [[ "${SLOT}" != "blue" && "${SLOT}" != "green" ]]; then
  echo "Usage: bash deploy/switch-slot.sh blue|green"
  exit 2
fi

cp "${NGINX_DIR}/${SLOT}.conf.template" "${NGINX_DIR}/active.conf"

docker compose -f "${COMPOSE_FILE}" exec -T proxy nginx -t
docker compose -f "${COMPOSE_FILE}" exec -T proxy nginx -s reload

for attempt in $(seq 1 30); do
  active_slot="$(curl --fail --silent http://localhost:8080/deployment-slot || true)"
  if [[ "${active_slot}" == "${SLOT}" ]]; then
    echo "Traffic is now routed to ${SLOT}."
    exit 0
  fi
  sleep 2
done

echo "Traffic did not switch to ${SLOT}."
docker compose -f "${COMPOSE_FILE}" logs proxy
exit 1
