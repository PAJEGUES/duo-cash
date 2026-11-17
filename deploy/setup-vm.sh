#!/usr/bin/env bash
# Prepara uma VM Debian 12 nova (ex.: GCP e2-micro) para rodar o DuoCash.
# Pode ser executado várias vezes: cada passo verifica se já foi feito.
#
#   sudo bash deploy/setup-vm.sh
set -euo pipefail

if [[ $EUID -ne 0 ]]; then
  echo "Execute com sudo: sudo bash $0" >&2
  exit 1
fi

DEPLOY_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_USER="${SUDO_USER:-}"

log() { printf '\n==> %s\n' "$*"; }

# --- 1. Docker Engine + plugin compose (repositório oficial) -----------------
if ! command -v docker >/dev/null 2>&1 || ! docker compose version >/dev/null 2>&1; then
  log "Instalando Docker"
  apt-get update -y
  apt-get install -y ca-certificates curl gnupg openssl
  install -m 0755 -d /etc/apt/keyrings
  if [[ ! -f /etc/apt/keyrings/docker.asc ]]; then
    curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc
    chmod a+r /etc/apt/keyrings/docker.asc
  fi
  # shellcheck disable=SC1091
  . /etc/os-release
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian ${VERSION_CODENAME} stable" \
    > /etc/apt/sources.list.d/docker.list
  apt-get update -y
  apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
else
  log "Docker já instalado: $(docker --version)"
fi
systemctl enable --now docker

if [[ -n "$TARGET_USER" ]] && ! id -nG "$TARGET_USER" | grep -qw docker; then
  usermod -aG docker "$TARGET_USER"
  log "Usuário $TARGET_USER adicionado ao grupo docker (vale no próximo login)"
fi

# --- 2. Swap de 1 GB (a e2-micro tem só 1 GB de RAM) --------------------------
if ! swapon --show | grep -q '/swapfile'; then
  log "Criando swap de 1 GB"
  if [[ ! -f /swapfile ]]; then
    fallocate -l 1G /swapfile || dd if=/dev/zero of=/swapfile bs=1M count=1024
    chmod 600 /swapfile
    mkswap /swapfile
  fi
  swapon /swapfile
else
  log "Swap já ativo"
fi
grep -q '^/swapfile ' /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab
if [[ ! -f /etc/sysctl.d/99-duocash.conf ]]; then
  echo 'vm.swappiness=10' > /etc/sysctl.d/99-duocash.conf
  sysctl -p /etc/sysctl.d/99-duocash.conf >/dev/null
fi

# --- 3. Arquivo .env ------------------------------------------------------------
ENV_FILE="$DEPLOY_DIR/.env"
if [[ ! -f "$ENV_FILE" ]]; then
  log "Criando $ENV_FILE a partir do .env.example"
  cp "$DEPLOY_DIR/.env.example" "$ENV_FILE"
fi
chmod 600 "$ENV_FILE"
if [[ -n "$TARGET_USER" ]]; then chown "$TARGET_USER" "$ENV_FILE"; fi

set_if_empty() {  # set_if_empty CHAVE VALOR -> só preenche se estiver vazio
  local key="$1" value="$2"
  if grep -qE "^${key}=$" "$ENV_FILE"; then
    sed -i "s|^${key}=$|${key}=${value}|" "$ENV_FILE"
    echo "  $key gerado"
  elif ! grep -qE "^${key}=" "$ENV_FILE"; then
    echo "${key}=${value}" >> "$ENV_FILE"
    echo "  $key gerado"
  fi
}

set_if_empty POSTGRES_PASSWORD "$(openssl rand -hex 24)"
set_if_empty SECRET_KEY "$(openssl rand -hex 48)"

# Sugere DOMAIN/PUBLIC_BASE_URL com sslip.io usando o IP externo da VM no GCP.
EXTERNAL_IP="$(curl -fs -m 3 -H 'Metadata-Flavor: Google' \
  'http://metadata.google.internal/computeMetadata/v1/instance/network-interfaces/0/access-configs/0/external-ip' || true)"
if [[ -n "$EXTERNAL_IP" ]]; then
  SSLIP="${EXTERNAL_IP//./-}.sslip.io"
  set_if_empty DOMAIN "$SSLIP"
  set_if_empty PUBLIC_BASE_URL "https://$SSLIP"
fi

# --- 4. Próximos passos ---------------------------------------------------------
MISSING="$(grep -E '^(DOMAIN|PUBLIC_BASE_URL|GOOGLE_CLIENT_IDS)=$' "$ENV_FILE" | cut -d= -f1 | tr '\n' ' ' || true)"

cat <<EOF

==========================================================================
 VM pronta.
==========================================================================
 1. Libere as portas 80 e 443 no firewall do GCP (tags http-server e
    https-server na VM) e use um IP externo estático.
 2. Revise $ENV_FILE ${MISSING:+(falta preencher: $MISSING)}
      DOMAIN=<ip-com-tracos>.sslip.io   PUBLIC_BASE_URL=https://<mesmo domínio>
      GOOGLE_CLIENT_IDS=<client Web>,<client Android>
 3. Suba tudo:
      cd $DEPLOY_DIR && docker compose up -d --build
 4. Confira:
      docker compose ps
      curl https://\$DOMAIN/api/v1/health
 Logs: docker compose logs -f api
==========================================================================
EOF
