# Instalación automática de GRH0652 en Ubuntu

El repositorio incluye `install-ubuntu.sh`, pensado para dejar la aplicación completa en producción con una sola ejecución.

## Creación obligatoria del administrador

Después de arrancar el backend, el instalador consulta:

```text
/api/setup/status
```

Si no existe ningún administrador activo, la instalación **no se considera terminada** hasta crear uno. Esto se aplica tanto a la primera instalación como a las actualizaciones.

En modo interactivo se solicitarán usuario, nombre visible, correo opcional y contraseña dos veces. La contraseña debe tener como mínimo 12 caracteres y combinar al menos tres tipos de caracteres.

En una actualización normal con:

```bash
sudo grh0652-update
```

si ya existe un administrador, sus credenciales se conservan y no se pregunta nada. Si no existe, se abre el asistente obligatorio. Incluso si una versión antigua del comando de actualización invoca el instalador con `--non-interactive`, el nuevo instalador intentará abrir el asistente por `/dev/tty` para evitar dejar el sistema sin administrador.

Para un despliegue completamente desatendido sin terminal, añada:

```bash
--admin-user admin \
--admin-password 'UnaClaveLargaYSegura123!' \
--admin-name 'Administrador GRH0652' \
--admin-email admin@centro.es
```

El panel queda disponible en:

```text
https://TU_DOMINIO/admin.html
```

La contraseña no se guarda en `/root/GRH0652_CREDENTIALS.txt`; ese archivo conserva únicamente información operativa y el token de recuperación reservado a `root`.

## Requisitos previos

- Ubuntu 22.04, 24.04 o 26.04.
- Acceso `sudo/root`.
- Un dominio gestionado en Cloudflare.
- El ZIP privado `GRH0652_PRIVATE_BANKS_v1.zip` copiado al servidor.
- Si el instalador debe arrancar su propia réplica de Cloudflare Tunnel, el token del túnel remoto.

El instalador instala o configura automáticamente Docker Engine, Docker Compose, backend FastAPI, Nginx en contenedor, SQLite persistente, bancos privados, Cloudflare Tunnel, backups diarios y comandos de mantenimiento.

## Instalación interactiva

Copie primero el ZIP privado al servidor, por ejemplo a `/root/GRH0652_PRIVATE_BANKS_v1.zip`, y ejecute:

```bash
curl -fsSL https://raw.githubusercontent.com/atreyu1968/CFGSAF/main/grh0652/install-ubuntu.sh | sudo bash
```

El instalador solicita:
1. dominio público;
2. modo Cloudflare;
3. token del túnel si se elige `token`;
4. ruta del ZIP privado.

La clave docente se genera automáticamente y se guarda solo para root en:

```text
/root/GRH0652_CREDENTIALS.txt
```

## Instalación no interactiva

```bash
curl -fsSL https://raw.githubusercontent.com/atreyu1968/CFGSAF/main/grh0652/install-ubuntu.sh | \
sudo bash -s -- \
  --domain grh.ejemplo.es \
  --private-banks /root/GRH0652_PRIVATE_BANKS_v1.zip \
  --cloudflare-mode token \
  --tunnel-token 'TOKEN_DEL_TUNEL' \
  --non-interactive
```

## Cloudflare Tunnel

El origen local publicado por defecto es:

```text
http://localhost:8080
```

Si el túnel ya existe, use `--cloudflare-mode existing`. El Public Hostname de Cloudflare debe enviar el dominio de GRH0652 a ese origen. Si se usa `--cloudflare-mode token`, el instalador crea una unidad independiente `cloudflared-grh0652.service` y guarda el token en un archivo root-only mediante `--token-file`.

El instalador verifica al final `https://DOMINIO/health` y avisa si el Public Hostname aún no apunta al origen correcto.

## Seguridad

La web pública se copia a un directorio separado. No se sirven por HTTP:
- `.env`;
- SQLite;
- bancos privados;
- código del backend;
- backups.

El backend no expone su puerto directamente al exterior. Nginx es el único punto HTTP local y publica `/api/` hacia el contenedor FastAPI. Cloudflare Tunnel se conecta al listener de loopback.

## Operación

```bash
sudo grh0652-status
sudo grh0652-backup
sudo grh0652-update
```

Los backups automáticos se ejecutan diariamente mediante `grh0652-backup.timer`. Antes de una actualización, el instalador intenta crear además una copia `pre-update`.

Para ver logs:

```bash
cd /opt/grh0652
sudo docker compose -f docker-compose.prod.yml logs -f
```

## Directorios

- `/opt/grh0652/web`: contenido público.
- `/opt/grh0652/server`: backend.
- `/opt/grh0652/private-banks`: 12 bancos privados, modo 600.
- `/opt/grh0652/data`: SQLite persistente.
- `/opt/grh0652/backups`: copias de seguridad.
- `/etc/grh0652`: configuración local y, si procede, token Cloudflare.
