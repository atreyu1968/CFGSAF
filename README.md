# CFGSAF · Gestión de Recursos Humanos

Repositorio de la aplicación didáctica **GRH0652 · Gestión de Recursos Humanos** para CFGS de Administración y Finanzas.

La aplicación integra los cuatro resultados de aprendizaje del módulo, teoría, infografías, práctica guiada, Portafolio evaluable, examen seguro, recuperación por criterios, revisión docente/IA, exportación a Additio y persistencia en servidor.

## Instalación automática en Ubuntu

El repositorio incluye un instalador de producción pensado para dejar la aplicación funcionando con una sola ejecución en un servidor Ubuntu.

### Requisitos

- Ubuntu 22.04, 24.04 o 26.04.
- Acceso `sudo` o `root`.
- Un dominio gestionado mediante Cloudflare.
- El archivo privado `GRH0652_PRIVATE_BANKS_v1.zip` copiado previamente al servidor.
- Si el instalador va a ejecutar su propia instancia de Cloudflare Tunnel, el token del túnel.

> **Importante:** los bancos privados contienen preguntas y claves de corrección. No deben subirse nunca a GitHub ni colocarse en una ruta pública.

### Instalación interactiva

Copie primero el ZIP privado al servidor, por ejemplo:

```text
/root/GRH0652_PRIVATE_BANKS_v1.zip
```

Después ejecute:

```bash
curl -fsSL https://raw.githubusercontent.com/atreyu1968/CFGSAF/main/grh0652/install-ubuntu.sh | sudo bash
```

El instalador solicitará:

1. el dominio público, por ejemplo `grh.midominio.es`;
2. el modo de Cloudflare Tunnel;
3. el token del túnel, únicamente si se elige instalación mediante token;
4. la ruta del ZIP privado.

### Instalación no interactiva

Si ya conoce todos los parámetros:

```bash
curl -fsSL https://raw.githubusercontent.com/atreyu1968/CFGSAF/main/grh0652/install-ubuntu.sh | \
sudo bash -s -- \
  --domain grh.midominio.es \
  --private-banks /root/GRH0652_PRIVATE_BANKS_v1.zip \
  --cloudflare-mode existing \
  --non-interactive
```

Si desea que el instalador ejecute una instancia propia del túnel:

```bash
curl -fsSL https://raw.githubusercontent.com/atreyu1968/CFGSAF/main/grh0652/install-ubuntu.sh | \
sudo bash -s -- \
  --domain grh.midominio.es \
  --private-banks /root/GRH0652_PRIVATE_BANKS_v1.zip \
  --cloudflare-mode token \
  --tunnel-token 'TOKEN_DEL_TUNEL' \
  --non-interactive
```

## Qué instala automáticamente

El instalador:

- instala o valida Docker Engine y Docker Compose;
- despliega FastAPI y SQLite;
- despliega Nginx en un contenedor independiente;
- mantiene web pública y datos privados en directorios separados;
- instala los cuatro RA y sus SCORM;
- valida y monta los 12 bancos privados;
- genera una clave docente segura;
- configura CORS para el dominio elegido;
- utiliza el mismo dominio para web y API;
- deja FastAPI sin exposición directa a Internet;
- configura Cloudflare Tunnel cuando se proporciona token;
- crea backups automáticos diarios;
- crea un backup antes de cada actualización;
- instala comandos de mantenimiento;
- comprueba `/health` y el preflight de UT1–UT4.

## Cloudflare Tunnel

El origen local por defecto es:

```text
http://localhost:8080
```

Si ya existe un túnel de Cloudflare en el servidor, utilice:

```text
--cloudflare-mode existing
```

y configure el **Public Hostname** correspondiente para apuntar a:

```text
http://localhost:8080
```

Si utiliza:

```text
--cloudflare-mode token
```

el instalador crea el servicio:

```text
cloudflared-grh0652.service
```

y almacena el token en un archivo accesible únicamente por `root`.

## Después de instalar

El instalador deja las credenciales docentes en:

```text
/root/GRH0652_CREDENTIALS.txt
```

con permisos restringidos.

Comandos principales:

```bash
sudo grh0652-status
sudo grh0652-backup
sudo grh0652-update
```

Para consultar los logs:

```bash
cd /opt/grh0652
sudo docker compose -f docker-compose.prod.yml logs -f
```

## Estructura de producción

```text
/opt/grh0652/
├── web/            # contenido público
├── server/         # backend FastAPI
├── private-banks/  # bancos privados
├── data/           # SQLite persistente
└── backups/        # copias de seguridad

/etc/grh0652/       # configuración local y Cloudflare
```

Los archivos `.env`, SQLite, bancos privados, código del backend y backups **no se sirven por HTTP**.

## Actualizaciones

Para actualizar a la versión actual de `main`:

```bash
sudo grh0652-update
```

El actualizador conserva la base de datos y los bancos privados y trata de crear primero una copia `pre-update`.

## Documentación

- [Documentación general de GRH0652](grh0652/README.md)
- [Instalación automática completa en Ubuntu](grh0652/INSTALL_UBUNTU.md)
- [Auditoría técnica y criterios de cierre](grh0652/AUDIT.md)
- [Trazabilidad](grh0652/TRACEABILITY.md)

## Seguridad

- Los alumnos acceden con token personal.
- La identidad del alumno se valida en servidor.
- Las claves de Portafolio están vinculadas a la versión pública mediante `public_hash`.
- Los exámenes se generan en servidor.
- Los bancos privados no se versionan.
- El backend usa almacenamiento SQLite persistente y copias verificables.
- El panel docente dispone de preflight de producción.
