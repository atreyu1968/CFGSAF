#!/usr/bin/env bash
set -Eeuo pipefail
IFS=$'\n\t'

# GRH0652 · Instalador de producción para Ubuntu
# Uso rápido:
#   curl -fsSL https://raw.githubusercontent.com/atreyu1968/CFGSAF/main/grh0652/install-ubuntu.sh | sudo bash
#
# Instalación no interactiva:
#   sudo bash install-ubuntu.sh --domain grh.midominio.es --private-banks /root/GRH0652_PRIVATE_BANKS_v1.zip \
#     --cloudflare-mode token --tunnel-token 'eyJ...' --non-interactive

REPO_URL="https://github.com/atreyu1968/CFGSAF.git"
RAW_INSTALLER="https://raw.githubusercontent.com/atreyu1968/CFGSAF/main/grh0652/install-ubuntu.sh"
REPO_REF="main"
INSTALL_DIR="/opt/grh0652"
WEB_PORT="8080"
DOMAIN=""
PRIVATE_BANKS=""
TEACHER_TOKEN=""
SETUP_TOKEN=""
ADMIN_USER=""
ADMIN_PASSWORD=""
ADMIN_NAME=""
ADMIN_EMAIL=""
TUNNEL_TOKEN=""
CLOUDFLARE_MODE=""
NON_INTERACTIVE=0
REUSE_PRIVATE_BANKS=0
SKIP_EXTERNAL_CHECK=0
BACKUP_RETENTION_DAYS=14
TMP_DIR=""

log(){ printf '\n\033[1;36m[GRH0652]\033[0m %s\n' "$*"; }
ok(){ printf '\033[1;32m[OK]\033[0m %s\n' "$*"; }
warn(){ printf '\033[1;33m[AVISO]\033[0m %s\n' "$*" >&2; }
die(){ printf '\033[1;31m[ERROR]\033[0m %s\n' "$*" >&2; exit 1; }
cleanup(){ [[ -n "${TMP_DIR:-}" && -d "$TMP_DIR" ]] && rm -rf "$TMP_DIR"; }
trap cleanup EXIT
trap 'die "Falló la instalación en la línea $LINENO. Revise el mensaje anterior."' ERR

usage(){
  cat <<'EOF'
GRH0652 · Instalador automático Ubuntu

Opciones:
  --domain HOST             Dominio público, por ejemplo grh.ejemplo.es
  --private-banks RUTA     ZIP o directorio con los 12 bancos privados
  --reuse-private-banks    Reutiliza /opt/grh0652/private-banks si ya es válido
  --teacher-token TOKEN    Token de recuperación; si se omite se genera uno seguro
  --admin-user USUARIO      Usuario administrador inicial si no existe ninguno
  --admin-password CLAVE    Contraseña administrador (mín. 12 caracteres; no se guarda)
  --admin-name NOMBRE       Nombre visible del administrador
  --admin-email EMAIL       Correo del administrador (opcional)
  --cloudflare-mode MODO   token | existing | skip
  --tunnel-token TOKEN     Token de un túnel Cloudflare gestionado remotamente
  --web-port PUERTO        Puerto local al que apuntará el túnel (por defecto 8080)
  --repo-ref REF            Rama/etiqueta Git que desplegar (por defecto main)
  --install-dir RUTA       Directorio privado (por defecto /opt/grh0652)
  --retention DIAS         Retención de backups diarios (por defecto 14)
  --skip-external-check    No comprueba https://DOMINIO/health al finalizar
  --non-interactive        No pregunta; exige los argumentos necesarios
  -h, --help               Ayuda

Cloudflare:
  - mode=token instala una instancia systemd propia usando --token-file.
  - mode=existing no toca su túnel actual; este debe enviar el dominio a
    http://localhost:PUERTO.
  - mode=skip deja Cloudflare completamente fuera del instalador.
EOF
}

while (($#)); do
  case "$1" in
    --domain) DOMAIN="${2:-}"; shift 2;;
    --private-banks) PRIVATE_BANKS="${2:-}"; shift 2;;
    --reuse-private-banks) REUSE_PRIVATE_BANKS=1; shift;;
    --teacher-token) TEACHER_TOKEN="${2:-}"; shift 2;;
    --admin-user) ADMIN_USER="${2:-}"; shift 2;;
    --admin-password) ADMIN_PASSWORD="${2:-}"; shift 2;;
    --admin-name) ADMIN_NAME="${2:-}"; shift 2;;
    --admin-email) ADMIN_EMAIL="${2:-}"; shift 2;;
    --cloudflare-mode) CLOUDFLARE_MODE="${2:-}"; shift 2;;
    --tunnel-token) TUNNEL_TOKEN="${2:-}"; shift 2;;
    --web-port) WEB_PORT="${2:-}"; shift 2;;
    --repo-ref) REPO_REF="${2:-}"; shift 2;;
    --install-dir) INSTALL_DIR="${2:-}"; shift 2;;
    --retention) BACKUP_RETENTION_DAYS="${2:-}"; shift 2;;
    --skip-external-check) SKIP_EXTERNAL_CHECK=1; shift;;
    --non-interactive) NON_INTERACTIVE=1; shift;;
    -h|--help) usage; exit 0;;
    *) die "Opción desconocida: $1";;
  esac
done

[[ "${EUID}" -eq 0 ]] || die "Ejecute el instalador como root: sudo bash install-ubuntu.sh"
[[ -r /etc/os-release ]] || die "No se puede identificar el sistema operativo."
. /etc/os-release
[[ "${ID:-}" == "ubuntu" ]] || die "Este instalador está diseñado para Ubuntu. Sistema detectado: ${PRETTY_NAME:-desconocido}"
[[ "$INSTALL_DIR" == /* && "$INSTALL_DIR" != "/" ]] || die "--install-dir debe ser una ruta absoluta segura."
[[ "$WEB_PORT" =~ ^[0-9]+$ ]] && ((WEB_PORT>=1 && WEB_PORT<=65535)) || die "Puerto inválido: $WEB_PORT"
[[ "$BACKUP_RETENTION_DAYS" =~ ^[0-9]+$ ]] && ((BACKUP_RETENTION_DAYS>=1)) || die "Retención inválida."

CONFIG_DIR="/etc/grh0652"
INSTALL_CONF="$CONFIG_DIR/install.conf"
# En una reinstalación interactiva podemos recuperar el dominio anterior sin
# permitir que install.conf sobrescriba opciones expresas de la línea de órdenes.
if [[ -z "$DOMAIN" && -f "$INSTALL_CONF" ]]; then
  previous_domain="$(sed -n "s/^DOMAIN_ARG='\\(.*\\)'$/\\1/p" "$INSTALL_CONF" | head -n1)"
  [[ -n "$previous_domain" ]] && DOMAIN="$previous_domain"
fi

prompt(){
  local var="$1" label="$2" default="${3:-}" value=""
  if ((NON_INTERACTIVE)); then
    [[ -n "$default" ]] || return 1
    printf -v "$var" '%s' "$default"
    return 0
  fi
  if [[ -n "$default" ]]; then
    read -r -p "$label [$default]: " value </dev/tty || true
    value="${value:-$default}"
  else
    read -r -p "$label: " value </dev/tty || true
  fi
  printf -v "$var" '%s' "$value"
}

prompt_secret(){
  local var="$1" label="$2" value=""
  if ((NON_INTERACTIVE)); then return 1; fi
  read -r -s -p "$label: " value </dev/tty || true
  printf '\n' >/dev/tty
  printf -v "$var" '%s' "$value"
}

password_ok(){
  local p="$1" classes=0
  [[ "${#p}" -ge 12 ]] || return 1
  [[ "$p" =~ [a-z] ]] && ((classes+=1))
  [[ "$p" =~ [A-Z] ]] && ((classes+=1))
  [[ "$p" =~ [0-9] ]] && ((classes+=1))
  [[ "$p" =~ [^a-zA-Z0-9] ]] && ((classes+=1))
  ((classes>=3))
}

collect_admin_credentials(){
  local saved_non_interactive="$NON_INTERACTIVE"
  # Excepción deliberada: incluso una actualización lanzada con --non-interactive
  # debe pedir credenciales si descubre que no existe ningún administrador.
  # Esto permite que versiones antiguas de grh0652-update, que añadían
  # --non-interactive, migren de forma segura al nuevo sistema de cuentas.
  if ((NON_INTERACTIVE)) && { [[ -z "$ADMIN_USER" ]] || [[ -z "$ADMIN_PASSWORD" ]]; }; then
    if [[ -r /dev/tty ]]; then
      warn "No existe administrador: se abre el asistente obligatorio de credenciales aunque la actualización fuese no interactiva."
      NON_INTERACTIVE=0
    else
      die "No existe administrador y no hay terminal interactivo. Repita con --admin-user USUARIO --admin-password CLAVE [--admin-name NOMBRE --admin-email EMAIL]."
    fi
  fi
  if [[ -z "$ADMIN_USER" ]]; then prompt ADMIN_USER "Usuario administrador" "admin"; fi
  [[ "$ADMIN_USER" =~ ^[A-Za-z0-9._-]{3,64}$ ]] || die "Usuario administrador inválido. Use 3-64 caracteres: letras, números, punto, guion o guion bajo."
  if [[ -z "$ADMIN_NAME" && "$NON_INTERACTIVE" -eq 0 ]]; then prompt ADMIN_NAME "Nombre visible del administrador" "Administrador GRH0652"; fi
  ADMIN_NAME="${ADMIN_NAME:-Administrador GRH0652}"
  if [[ -z "$ADMIN_EMAIL" && "$NON_INTERACTIVE" -eq 0 ]]; then prompt ADMIN_EMAIL "Correo del administrador (opcional)" ""; fi
  if [[ -z "$ADMIN_PASSWORD" ]]; then
    while true; do
      local p1="" p2=""
      prompt_secret p1 "Contraseña del administrador"
      if ! password_ok "$p1"; then warn "La contraseña debe tener al menos 12 caracteres y combinar 3 de estos grupos: mayúsculas, minúsculas, números y símbolos."; continue; fi
      prompt_secret p2 "Repita la contraseña"
      [[ "$p1" == "$p2" ]] || { warn "Las contraseñas no coinciden."; continue; }
      ADMIN_PASSWORD="$p1"; break
    done
  fi
  password_ok "$ADMIN_PASSWORD" || die "La contraseña de administrador no cumple la política mínima."
  NON_INTERACTIVE="$saved_non_interactive"
}

if [[ -z "$DOMAIN" ]]; then prompt DOMAIN "Dominio público (sin https://)" || die "Falta --domain"; fi
DOMAIN="${DOMAIN#https://}"; DOMAIN="${DOMAIN#http://}"; DOMAIN="${DOMAIN%%/*}"
[[ "$DOMAIN" =~ ^[A-Za-z0-9.-]+$ && "$DOMAIN" == *.* ]] || die "Dominio inválido: $DOMAIN"

if [[ -z "$CLOUDFLARE_MODE" ]]; then
  if ((NON_INTERACTIVE)); then
    CLOUDFLARE_MODE="existing"
  else
    printf '\nCloudflare Tunnel:\n  1) instalar/gestionar esta app con token\n  2) usar un túnel cloudflared ya existente\n  3) no configurar Cloudflare\n' >/dev/tty
    read -r -p "Elija [1]: " cf_choice </dev/tty || true
    case "${cf_choice:-1}" in 1) CLOUDFLARE_MODE="token";; 2) CLOUDFLARE_MODE="existing";; 3) CLOUDFLARE_MODE="skip";; *) die "Opción Cloudflare inválida";; esac
  fi
fi
case "$CLOUDFLARE_MODE" in token|existing|skip) :;; *) die "--cloudflare-mode debe ser token, existing o skip";; esac

if [[ "$CLOUDFLARE_MODE" == "token" && -z "$TUNNEL_TOKEN" ]]; then
  [[ -f "$CONFIG_DIR/cloudflared.token" ]] && TUNNEL_TOKEN="$(tr -d '\r\n' < "$CONFIG_DIR/cloudflared.token")"
  if [[ -z "$TUNNEL_TOKEN" ]]; then prompt_secret TUNNEL_TOKEN "Token del túnel Cloudflare (eyJ...)" || die "Falta --tunnel-token"; fi
fi

TMP_DIR="$(mktemp -d -t grh0652-install.XXXXXX)"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" 2>/dev/null && pwd || true)"
if [[ -f "$SCRIPT_DIR/server/app.py" && -f "$SCRIPT_DIR/index.html" ]]; then
  SRC="$SCRIPT_DIR"
  log "Usando los archivos GRH0652 del repositorio local."
else
  log "Descargando el repositorio $REPO_REF..."
  apt-get update -qq
  DEBIAN_FRONTEND=noninteractive apt-get install -y -qq ca-certificates curl git >/dev/null
  git clone --depth 1 --branch "$REPO_REF" "$REPO_URL" "$TMP_DIR/repo" >/dev/null
  SRC="$TMP_DIR/repo/grh0652"
fi
[[ -f "$SRC/server/app.py" && -f "$SRC/server/validate_private_banks.py" ]] || die "La fuente GRH0652 está incompleta."

log "Instalando utilidades base..."
apt-get update -qq
DEBIAN_FRONTEND=noninteractive apt-get install -y -qq ca-certificates curl git unzip openssl python3 >/dev/null

install_docker(){
  if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
    ok "Docker + Compose ya disponibles."
    systemctl enable --now docker >/dev/null 2>&1 || true
    return
  fi
  log "Instalando Docker Engine y Docker Compose desde el repositorio oficial..."
  apt-get remove -y docker.io docker-compose docker-compose-v2 docker-doc docker-buildx podman-docker containerd runc >/dev/null 2>&1 || true
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
  chmod a+r /etc/apt/keyrings/docker.asc
  cat >/etc/apt/sources.list.d/docker.sources <<EOF
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: ${UBUNTU_CODENAME:-$VERSION_CODENAME}
Components: stable
Architectures: $(dpkg --print-architecture)
Signed-By: /etc/apt/keyrings/docker.asc
EOF
  apt-get update -qq
  DEBIAN_FRONTEND=noninteractive apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin >/dev/null
  systemctl enable --now docker >/dev/null
  docker compose version >/dev/null
}
install_docker

mkdir -p "$INSTALL_DIR"/{data,private-banks,backups,web}
chmod 700 "$INSTALL_DIR" "$INSTALL_DIR/data" "$INSTALL_DIR/private-banks" "$INSTALL_DIR/backups"

# Copia de seguridad automática antes de una actualización.
if [[ -f "$INSTALL_DIR/.env" ]] && curl -fsS --max-time 3 "http://127.0.0.1:$WEB_PORT/health" >/dev/null 2>&1; then
  OLD_TOKEN="$(sed -n 's/^GRH_TEACHER_TOKEN=//p' "$INSTALL_DIR/.env" | head -n1)"
  if [[ -n "$OLD_TOKEN" ]]; then
    PRE="$INSTALL_DIR/backups/pre-update-$(date +%Y%m%d-%H%M%S).db"
    if curl -fsS --max-time 30 -H "X-Teacher-Token: $OLD_TOKEN" "http://127.0.0.1:$WEB_PORT/api/teacher/backup" -o "$PRE"; then
      chmod 600 "$PRE"; ok "Backup previo guardado en $PRE"
    else
      rm -f "$PRE"; warn "No se pudo crear backup previo por API; la instalación continuará sin tocar $INSTALL_DIR/data."
    fi
  fi
fi

log "Desplegando backend y web pública..."
rm -rf "$INSTALL_DIR/server.new" "$INSTALL_DIR/web.new"
cp -a "$SRC/server" "$INSTALL_DIR/server.new"
mkdir -p "$INSTALL_DIR/web.new"
for f in index.html course.html player.html teacher.html admin.html banks.html lti-admin.html lti-entry.html ut1.html; do
  [[ -f "$SRC/$f" ]] && cp -a "$SRC/$f" "$INSTALL_DIR/web.new/"
done
cp -a "$SRC/assets" "$SRC/scorm" "$INSTALL_DIR/web.new/"
rm -rf "$INSTALL_DIR/server"
mv "$INSTALL_DIR/server.new" "$INSTALL_DIR/server"
rm -rf "$INSTALL_DIR/web"
mv "$INSTALL_DIR/web.new" "$INSTALL_DIR/web"
find "$INSTALL_DIR/web" -type f -exec chmod 644 {} +
find "$INSTALL_DIR/web" -type d -exec chmod 755 {} +

# Bancos privados: se exigen en una primera instalación.
if [[ -n "$PRIVATE_BANKS" ]]; then
  [[ -e "$PRIVATE_BANKS" ]] || die "No existe --private-banks: $PRIVATE_BANKS"
  BANK_TMP="$TMP_DIR/banks"
  mkdir -p "$BANK_TMP"
  if [[ -d "$PRIVATE_BANKS" ]]; then
    find "$PRIVATE_BANKS" -type f -name '*.json' -maxdepth 2 -exec cp -a {} "$BANK_TMP/" \;
  else
    unzip -q "$PRIVATE_BANKS" -d "$TMP_DIR/banks-unzip"
    while IFS= read -r -d '' f; do cp -a "$f" "$BANK_TMP/$(basename "$f")"; done < <(find "$TMP_DIR/banks-unzip" -type f -name '*.json' -print0)
  fi
  count="$(find "$BANK_TMP" -maxdepth 1 -type f -name '*.json' | wc -l)"
  [[ "$count" -eq 12 ]] || die "El paquete privado debe contener exactamente 12 JSON; encontrados: $count"
  rm -f "$INSTALL_DIR/private-banks/"*.json
  cp -a "$BANK_TMP/"*.json "$INSTALL_DIR/private-banks/"
  chmod 600 "$INSTALL_DIR/private-banks/"*.json
elif ((REUSE_PRIVATE_BANKS)); then
  :
elif [[ "$(find "$INSTALL_DIR/private-banks" -maxdepth 1 -type f -name '*.json' | wc -l)" -eq 12 ]]; then
  ok "Reutilizando los 12 bancos privados ya instalados."
else
  if ((NON_INTERACTIVE)); then
    die "Primera instalación: indique --private-banks /ruta/GRH0652_PRIVATE_BANKS_v1.zip"
  fi
  prompt PRIVATE_BANKS "Ruta al ZIP privado GRH0652_PRIVATE_BANKS_v1.zip" || die "Se necesitan los bancos privados."
  [[ -f "$PRIVATE_BANKS" ]] || die "No existe: $PRIVATE_BANKS"
  unzip -q "$PRIVATE_BANKS" -d "$TMP_DIR/banks-unzip"
  mapfile -d '' bank_files < <(find "$TMP_DIR/banks-unzip" -type f -name '*.json' -print0)
  [[ "${#bank_files[@]}" -eq 12 ]] || die "El ZIP debe contener exactamente 12 JSON privados."
  rm -f "$INSTALL_DIR/private-banks/"*.json
  for f in "${bank_files[@]}"; do cp -a "$f" "$INSTALL_DIR/private-banks/$(basename "$f")"; done
  chmod 600 "$INSTALL_DIR/private-banks/"*.json
fi

log "Validando bancos privados..."
python3 "$INSTALL_DIR/server/validate_private_banks.py" "$INSTALL_DIR/private-banks"

if [[ -z "$TEACHER_TOKEN" && -f "$INSTALL_DIR/.env" ]]; then
  TEACHER_TOKEN="$(sed -n 's/^GRH_TEACHER_TOKEN=//p' "$INSTALL_DIR/.env" | head -n1)"
fi
if [[ -z "$SETUP_TOKEN" && -f "$INSTALL_DIR/.env" ]]; then
  SETUP_TOKEN="$(sed -n 's/^GRH_SETUP_TOKEN=//p' "$INSTALL_DIR/.env" | head -n1)"
fi
[[ -n "$TEACHER_TOKEN" ]] || TEACHER_TOKEN="$(openssl rand -hex 32)"
[[ -n "$SETUP_TOKEN" ]] || SETUP_TOKEN="$(openssl rand -hex 32)"
[[ "${#TEACHER_TOKEN}" -ge 32 ]] || die "El token de recuperación debe tener al menos 32 caracteres."
[[ "${#SETUP_TOKEN}" -ge 32 ]] || die "El token de instalación debe tener al menos 32 caracteres."

cat >"$INSTALL_DIR/.env" <<EOF
GRH_TEACHER_TOKEN=$TEACHER_TOKEN
GRH_SETUP_TOKEN=$SETUP_TOKEN
GRH_ALLOWED_ORIGINS=https://$DOMAIN
GRH_PUBLIC_URL=https://$DOMAIN
EOF
chmod 600 "$INSTALL_DIR/.env"

cat >"$INSTALL_DIR/nginx.conf" <<'EOF'
server {
    listen 80 default_server;
    server_name _;
    root /usr/share/nginx/html;
    index index.html;
    charset utf-8;
    client_max_body_size 256m;

    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Content-Security-Policy "frame-ancestors 'self' https://*.gobiernodecanarias.org https://*.canariaseducacion.es https://*.gobcan.es" always;

    location = /health {
        proxy_pass http://grh-api:8080/health;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto $http_x_forwarded_proto;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_read_timeout 30s;
    }

    location /api/ {
        proxy_pass http://grh-api:8080;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-Proto $http_x_forwarded_proto;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_read_timeout 300s;
        proxy_send_timeout 300s;
    }

    location ~* \.html$ {
        try_files $uri =404;
        add_header Cache-Control "no-store";
    }

    location / {
        try_files $uri $uri/ =404;
    }

    location ~ /\. {
        deny all;
    }
}
EOF

cat >"$INSTALL_DIR/docker-compose.prod.yml" <<EOF
services:
  grh-api:
    build: ./server
    container_name: grh0652-api
    restart: unless-stopped
    env_file:
      - .env
    environment:
      GRH_DB: /data/grh0652.db
      GRH_PRIVATE_BANK_DIR: /private-banks
    volumes:
      - ./data:/data
      - ./private-banks:/private-banks:ro
    networks:
      - grh0652
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"

  web:
    image: nginx:stable-alpine
    container_name: grh0652-web
    restart: unless-stopped
    depends_on:
      - grh-api
    ports:
      - "127.0.0.1:$WEB_PORT:80"
    volumes:
      - ./web:/usr/share/nginx/html:ro
      - ./nginx.conf:/etc/nginx/conf.d/default.conf:ro
    networks:
      - grh0652
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"

networks:
  grh0652:
    name: grh0652
EOF

log "Construyendo y arrancando GRH0652..."
cd "$INSTALL_DIR"
docker compose -f docker-compose.prod.yml up -d --build --remove-orphans

log "Esperando al backend..."
healthy=0
for _ in $(seq 1 45); do
  if curl -fsS --max-time 3 "http://127.0.0.1:$WEB_PORT/health" | grep -q '"ok":true'; then healthy=1; break; fi
  sleep 2
done
if ((healthy==0)); then
  docker compose -f docker-compose.prod.yml ps >&2 || true
  docker compose -f docker-compose.prod.yml logs --tail=120 >&2 || true
  die "El servicio local no superó /health."
fi
ok "Servicio local operativo en http://127.0.0.1:$WEB_PORT"

log "Comprobando la cuenta administradora..."
SETUP_STATUS="$TMP_DIR/setup-status.json"
curl -fsS --max-time 10 "http://127.0.0.1:$WEB_PORT/api/setup/status" -o "$SETUP_STATUS"
NEEDS_ADMIN="$(python3 - "$SETUP_STATUS" <<'PY'
import json,sys
d=json.load(open(sys.argv[1],encoding="utf-8"))
print("1" if d.get("needs_admin") else "0")
PY
)"
if [[ "$NEEDS_ADMIN" == "1" ]]; then
  warn "No existe ningún administrador activo. La instalación/actualización no continuará sin crear uno."
  collect_admin_credentials
  ADMIN_JSON="$TMP_DIR/admin-create.json"
  ADMIN_USER="$ADMIN_USER" ADMIN_PASSWORD="$ADMIN_PASSWORD" ADMIN_NAME="$ADMIN_NAME" ADMIN_EMAIL="$ADMIN_EMAIL" python3 - "$ADMIN_JSON" <<'PY'
import json,os,sys
payload={
 "username":os.environ["ADMIN_USER"],
 "password":os.environ["ADMIN_PASSWORD"],
 "display_name":os.environ.get("ADMIN_NAME","Administrador GRH0652"),
 "email":os.environ.get("ADMIN_EMAIL",""),
}
with open(sys.argv[1],"w",encoding="utf-8") as f:json.dump(payload,f,ensure_ascii=False)
PY
  ADMIN_RESPONSE="$TMP_DIR/admin-response.json"
  HTTP_CODE="$(curl -sS -o "$ADMIN_RESPONSE" -w '%{http_code}' --max-time 15 \
    -H "Content-Type: application/json" \
    -H "X-Setup-Token: $SETUP_TOKEN" \
    --data-binary "@$ADMIN_JSON" \
    "http://127.0.0.1:$WEB_PORT/api/setup/admin")"
  if [[ "$HTTP_CODE" != "200" ]]; then
    cat "$ADMIN_RESPONSE" >&2 || true
    die "No se pudo crear el administrador (HTTP $HTTP_CODE)."
  fi
  ok "Administrador '$ADMIN_USER' creado correctamente."
  unset ADMIN_PASSWORD
else
  ADMIN_COUNT="$(python3 - "$SETUP_STATUS" <<'PY'
import json,sys
d=json.load(open(sys.argv[1],encoding="utf-8"))
print(d.get("active_admins",0))
PY
)"
  ok "Administrador existente detectado ($ADMIN_COUNT activo/s). No se modifica ninguna credencial."
fi

log "Comprobando bancos cargados en el backend..."
for course in GRH0652_UT1 GRH0652_UT2 GRH0652_UT3 GRH0652_UT4; do
  rd="$TMP_DIR/$course.json"
  curl -fsS -H "X-Teacher-Token: $TEACHER_TOKEN" "http://127.0.0.1:$WEB_PORT/api/teacher/readiness/$course" -o "$rd"
  python3 - "$rd" "$course" <<'PY'
import json,sys
p,course=sys.argv[1:]
d=json.load(open(p,encoding="utf-8"))
c=d.get("checks",{})
bad=[k for k in ("portfolio_keys","exam_bank","recovery_bank","origins") if not c.get(k,{}).get("ok")]
if bad:
    print(json.dumps(d,ensure_ascii=False,indent=2),file=sys.stderr)
    raise SystemExit(f"{course}: preflight de infraestructura no superado: {', '.join(bad)}")
print(f"{course}: bancos y CORS OK; alumnos={c.get('students',{}).get('count',0)}")
PY
done

install_cloudflared(){
  command -v cloudflared >/dev/null 2>&1 && return
  log "Instalando cloudflared desde el repositorio oficial..."
  install -d -m 0755 /usr/share/keyrings
  curl -fsSL https://pkg.cloudflare.com/cloudflare-main.gpg -o /usr/share/keyrings/cloudflare-main.gpg
  echo "deb [signed-by=/usr/share/keyrings/cloudflare-main.gpg] https://pkg.cloudflare.com/cloudflared any main" > /etc/apt/sources.list.d/cloudflared.list
  apt-get update -qq
  DEBIAN_FRONTEND=noninteractive apt-get install -y -qq cloudflared >/dev/null
}

mkdir -p "$CONFIG_DIR"; chmod 700 "$CONFIG_DIR"
if [[ "$CLOUDFLARE_MODE" == "token" ]]; then
  install_cloudflared
  printf '%s' "$TUNNEL_TOKEN" >"$CONFIG_DIR/cloudflared.token"
  chmod 600 "$CONFIG_DIR/cloudflared.token"
  cat >/etc/systemd/system/cloudflared-grh0652.service <<EOF
[Unit]
Description=Cloudflare Tunnel para GRH0652
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
ExecStart=$(command -v cloudflared) tunnel --no-autoupdate run --token-file $CONFIG_DIR/cloudflared.token
Restart=always
RestartSec=5s

[Install]
WantedBy=multi-user.target
EOF
  systemctl daemon-reload
  systemctl enable --now cloudflared-grh0652.service
  sleep 2
  systemctl is-active --quiet cloudflared-grh0652.service || {
    journalctl -u cloudflared-grh0652.service -n 80 --no-pager >&2 || true
    die "cloudflared-grh0652 no ha arrancado correctamente."
  }
  ok "Cloudflare Tunnel ejecutándose como cloudflared-grh0652.service"
elif [[ "$CLOUDFLARE_MODE" == "existing" ]]; then
  if systemctl is-active --quiet cloudflared 2>/dev/null || systemctl is-active --quiet cloudflared-grh0652 2>/dev/null; then
    ok "Se conservará el túnel Cloudflare existente."
  else
    warn "No se detecta un servicio cloudflared activo. El origen local está preparado en http://localhost:$WEB_PORT."
  fi
fi

# Configuración persistente para actualizaciones.
cat >"$INSTALL_CONF" <<EOF
DOMAIN_ARG='$DOMAIN'
WEB_PORT='$WEB_PORT'
INSTALL_DIR='$INSTALL_DIR'
REPO_REF='$REPO_REF'
BACKUP_RETENTION_DAYS='$BACKUP_RETENTION_DAYS'
EOF
chmod 600 "$INSTALL_CONF"

cat >/usr/local/sbin/grh0652-backup <<EOF
#!/usr/bin/env bash
set -Eeuo pipefail
INSTALL_DIR='$INSTALL_DIR'
WEB_PORT='$WEB_PORT'
TOKEN="\$(sed -n 's/^GRH_TEACHER_TOKEN=//p' "\$INSTALL_DIR/.env" | head -n1)"
mkdir -p "\$INSTALL_DIR/backups"
OUT="\$INSTALL_DIR/backups/grh0652-\$(date +%Y%m%d-%H%M%S).db"
curl -fsS -H "X-Teacher-Token: \$TOKEN" "http://127.0.0.1:\$WEB_PORT/api/teacher/backup" -o "\$OUT"
chmod 600 "\$OUT"
find "\$INSTALL_DIR/backups" -type f -name 'grh0652-*.db' -mtime +$BACKUP_RETENTION_DAYS -delete
echo "\$OUT"
EOF
chmod 700 /usr/local/sbin/grh0652-backup

cat >/usr/local/sbin/grh0652-status <<EOF
#!/usr/bin/env bash
set -u
echo "=== GRH0652 ==="
cd '$INSTALL_DIR' && docker compose -f docker-compose.prod.yml ps
echo
curl -fsS "http://127.0.0.1:$WEB_PORT/health" && echo
echo
systemctl --no-pager --full status cloudflared-grh0652.service 2>/dev/null | sed -n '1,8p' || true
EOF
chmod 755 /usr/local/sbin/grh0652-status

cat >/usr/local/sbin/grh0652-update <<EOF
#!/usr/bin/env bash
set -Eeuo pipefail
curl -fsSL '$RAW_INSTALLER' | sudo bash -s -- \
  --domain '$DOMAIN' \
  --web-port '$WEB_PORT' \
  --repo-ref '$REPO_REF' \
  --install-dir '$INSTALL_DIR' \
  --retention '$BACKUP_RETENTION_DAYS' \
  --reuse-private-banks \
  --cloudflare-mode existing
EOF
chmod 755 /usr/local/sbin/grh0652-update

cat >/etc/systemd/system/grh0652-backup.service <<EOF
[Unit]
Description=Backup diario GRH0652
After=docker.service
[Service]
Type=oneshot
ExecStart=/usr/local/sbin/grh0652-backup
EOF
cat >/etc/systemd/system/grh0652-backup.timer <<'EOF'
[Unit]
Description=Programación de backup diario GRH0652
[Timer]
OnCalendar=*-*-* 03:30:00
RandomizedDelaySec=15m
Persistent=true
[Install]
WantedBy=timers.target
EOF
systemctl daemon-reload
systemctl enable --now grh0652-backup.timer >/dev/null

CREDS="/root/GRH0652_CREDENTIALS.txt"
cat >"$CREDS" <<EOF
GRH0652
Dominio: https://$DOMAIN
Panel de administración: https://$DOMAIN/admin.html
Panel docente: https://$DOMAIN/teacher.html
Usuario administrador: ${ADMIN_USER:-existente}
Contraseña administrador: NO SE GUARDA EN ESTE ARCHIVO
Token de recuperación (solo root): $TEACHER_TOKEN
Origen local Cloudflare: http://localhost:$WEB_PORT
Directorio: $INSTALL_DIR

Comandos:
  grh0652-status
  grh0652-backup
  grh0652-update
  cd $INSTALL_DIR && docker compose -f docker-compose.prod.yml logs -f
EOF
chmod 600 "$CREDS"

external_ok=0
if [[ "$CLOUDFLARE_MODE" != "skip" && "$SKIP_EXTERNAL_CHECK" -eq 0 ]]; then
  log "Comprobando el dominio público..."
  for _ in $(seq 1 20); do
    if curl -fsS --max-time 8 "https://$DOMAIN/health" | grep -q '"ok":true'; then external_ok=1; break; fi
    sleep 3
  done
  if ((external_ok)); then
    ok "Dominio público operativo: https://$DOMAIN"
  else
    warn "La aplicación local funciona, pero https://$DOMAIN/health aún no responde."
    warn "En Cloudflare > Networking > Tunnels > su túnel > Public Hostnames,"
    warn "configure $DOMAIN para enviar HTTP a http://localhost:$WEB_PORT."
  fi
fi

# Backup inicial tras instalación.
if /usr/local/sbin/grh0652-backup >/dev/null; then ok "Backup inicial creado."; else warn "No se pudo crear el backup inicial."; fi

printf '\n\033[1;32m============================================================\n'
printf ' GRH0652 INSTALADO CORRECTAMENTE\n'
printf '============================================================\033[0m\n'
printf ' Aula:          https://%s/\n' "$DOMAIN"
printf ' Administración: https://%s/admin.html\n' "$DOMAIN"
printf ' Panel docente:  https://%s/teacher.html\n' "$DOMAIN"
printf ' API:            mismo dominio (/api)\n'
printf ' Origen túnel:  http://localhost:%s\n' "$WEB_PORT"
printf ' Credenciales:  %s (solo root)\n' "$CREDS"
printf ' Estado:        sudo grh0652-status\n'
printf ' Backup:        sudo grh0652-backup\n'
printf ' Actualización: sudo grh0652-update\n'
printf '\nEl token de recuperación se ha guardado con permisos 600 en %s. La contraseña del administrador no se almacena.\n' "$CREDS"
if ((external_ok==0)) && [[ "$CLOUDFLARE_MODE" != "skip" ]]; then
  printf '\nPENDIENTE CLOUDFLARE: el Public Hostname %s debe apuntar a http://localhost:%s.\n' "$DOMAIN" "$WEB_PORT"
fi
