# Deploy del portal en una VM interna — paso a paso

Guía completa para dejar el portal operativo desde cero, en una VM dentro de la
red del cliente (donde corre Neotel). Asume que tenés acceso de red a la red
del cliente y permisos para crear máquinas virtuales ahí.

Tiempo estimado: 30-45 minutos si todo va liso.

---

## 1. Crear la VM

**Sistema operativo:** Ubuntu Server 22.04 LTS (también sirve 24.04 o Debian 12).
Cualquier Linux moderno con kernel 5.x+ y systemd va.

**Tamaño mínimo:**

| Recurso | Mínimo | Recomendado |
|---------|--------|-------------|
| RAM | 4 GB | 8 GB |
| vCPU | 2 | 4 |
| Disco | 20 GB SSD | 50 GB SSD |

**Networking:**

- Asignale una IP **estática** dentro de la red del cliente (ej. `10.0.0.42`).
  Si DHCP, reservala por MAC para que no cambie.
- Confirmá que el servidor de Neotel pueda alcanzar esta IP en los puertos
  `8000` (backend) y `3000` (frontend). Pingueá desde donde puedas verificarlo.
- La VM no necesita IP pública.

**Acceso:**

- Habilitá SSH durante la creación, con tu llave pública.
- Anotá la IP, el usuario inicial (ej. `ubuntu` o el que hayas creado) y
  guardala.

Probá la conexión:

```bash
ssh ubuntu@10.0.0.42
```

---

## 2. Preparar el sistema operativo

Todo lo de acá corre adentro de la VM por SSH.

### 2.1. Actualizar paquetes

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y curl git ufw
```

### 2.2. Firewall (UFW)

```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp                          # SSH
sudo ufw allow from 10.0.0.0/8 to any port 8000 proto tcp   # backend (red interna)
sudo ufw allow from 10.0.0.0/8 to any port 3000 proto tcp   # frontend (red interna)
sudo ufw enable
sudo ufw status
```

Ajustá el `10.0.0.0/8` al rango real de la red del cliente. Si no sabés cuál es,
mirá `ip addr` en la VM y abrí solo ese subnet.

### 2.3. Swap (solo si la VM tiene 4 GB de RAM)

Con 8 GB+ saltealo.

```bash
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

### 2.4. Instalar Docker + Compose

```bash
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
```

**Cerrá la sesión y volvé a entrar** (el cambio de grupo no aplica hasta
re-loguearse). Verificá:

```bash
docker version
docker compose version
```

Ambos comandos tienen que devolver versiones sin pedir sudo.

---

## 3. Clonar el repo

```bash
sudo mkdir -p /opt && sudo chown $USER /opt
cd /opt
git clone <URL_DEL_REPO> whatsapp-portal
cd whatsapp-portal
```

Si el repo es privado y necesita auth, usá HTTPS con un Personal Access Token
o SSH key — lo que tengas configurado.

---

## 4. Configurar `.env`

Crear el archivo `.env` en la raíz del repo:

```bash
nano .env
```

Pegá esto y ajustá los valores marcados:

```ini
# Secrets — generar nuevos para esta VM
SECRET_KEY=__pega_acá_la_salida_de__openssl_rand_-hex_32__
POSTGRES_USER=portal
POSTGRES_PASSWORD=__elegí_password_largo__
POSTGRES_DB=portal
DATABASE_URL=postgresql+asyncpg://portal:__mismo_password_de_arriba__@postgres:5432/portal
REDIS_URL=redis://redis:6379/0

# Evolution API
EVOLUTION_API_KEY=__elegí_otro_password_largo__
EVOLUTION_BASE_URL=http://evolution:8080

# Producción
ENVIRONMENT=production

# URLs públicas del backend/frontend desde la red del cliente
# Reemplazá 10.0.0.42 por la IP estática real de tu VM
NEXT_PUBLIC_API_BASE_URL=http://10.0.0.42:8000/api/v1
NEXT_PUBLIC_APP_URL=http://10.0.0.42:3000
```

**Generar el `SECRET_KEY`** sin volver a salir del prompt:

```bash
openssl rand -hex 32
```

Copialo y pegalo en el `.env`. Repetí para `POSTGRES_PASSWORD` y
`EVOLUTION_API_KEY` (no es obligatorio usar `openssl`, pero al menos que sean
20+ caracteres y no triviales).

Guardá con `Ctrl+O`, `Enter`, `Ctrl+X`.

Permisos restrictivos:

```bash
chmod 600 .env
```

---

## 5. Levantar el stack

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

La primera vez tarda 5-10 minutos (build de la imagen de Next + instalar deps de
Node y Python + bajar Postgres / Redis / Evolution). Las siguientes corridas
arrancan en segundos.

Verificá que los 6 contenedores estén `running`:

```bash
docker compose ps
```

Esperás ver: `portal_postgres`, `portal_redis`, `portal_evolution`,
`portal_backend`, `portal_worker`, `portal_frontend`.

Si alguno está `restarting`, mirá sus logs:

```bash
docker compose logs --tail 100 <nombre_servicio>
```

---

## 6. Aplicar migraciones de base de datos

```bash
docker compose exec backend alembic upgrade head
```

Tiene que decir `Will assume transactional DDL` y aplicar varias revisiones.
Si ya estaba en `head`, no hace nada — ok igual.

---

## 7. Smoke test

```bash
bash deploy/check.sh
```

Esperás ver:

- `docker compose ps` con todo `running`
- `backend health` → 200
- `migrations` → la última revision (ej. `c3d4e5f6a7b8 (head)`)
- `frontend root` → 307 redirect a `/login`
- `send_message.php` → JSON con `"result_code":-2` (esperado sin params)
- `external app inbox` → `422` (esperado sin body)

Si todo eso pasa, **el portal está operativo** del lado infraestructura. Lo que
queda es la config aplicativa.

---

## 8. Crear el primer usuario

Desde tu workstation (la que tiene acceso a la red del cliente), abrí en el
browser:

```
http://10.0.0.42:3000
```

(Reemplazá por tu IP real.)

Te redirige a `/login`. Click en "Create one" abajo del form.

Llená:

- **Organization name**: nombre de tu empresa
- **Organization slug**: ej. `acme` (minúsculas, sin espacios)
- **Your name**: tu nombre
- **Email**: tu email
- **Password**: al menos 8 chars

Click "Create workspace" → te logea automáticamente como **owner**.

---

## 9. Crear y parear el número de WhatsApp

1. Dashboard → click "**New number**"
2. Display name: ej. `Línea principal`. Click "Create".
3. Te lleva a la página del número. Muestra el **QR code**.
4. En tu celular, abrí WhatsApp → **Settings → Linked devices → Link a device**.
5. Escaneá el QR.
6. El status del número en el portal cambia de `connecting` → `connected` en
   pocos segundos (polling automático cada 3s).

Cuando aparezca el teléfono y la badge verde "Connected", el número está vivo y
listo para recibir/enviar.

**Test rápido:** desde otro teléfono, mandate un WhatsApp a tu número paireado.
En el portal → click el número → "Conversations" → debería aparecer la
conversación en segundos.

---

## 10. Configurar Neotel (Aplicación Externa)

### 10.1. Crear la cuenta en Neotel

1. Logueate al CRM web de Neotel.
2. **Redes Sociales → Aplicaciones Externas** (sidebar lateral).
3. Botón "Nueva cuenta" (o equivalente).
4. **Descripción**: ej. `WhatsApp Portal`.
5. **Imagen perfil**: subí cualquiera (opcional).
6. **Dejá vacío el campo Webhook URL por ahora.**
7. Click **"Obtener Credenciales"**.
8. Te genera `ApplicationId` y `Token` (o `AccessToken`). **Copiá los dos.**
9. Guardá la cuenta.

### 10.2. Configurar el webhook en nuestro portal

1. Volvé a nuestro portal: número → "**Webhook**".
2. **Format**: "Neotel External Application — bidirectional, self-service ⭐ RECOMMENDED".
3. **Send Message URL**: dejá la default
   (`https://s2.neotel.us/NeoWebhook/api/ExternalApplication/SendMessage`), que
   es el host vivo de Neotel. Si tu cuenta usa otro host, pedile la URL a Neotel
   y reemplazala. (El viejo default `webhook.neotel.com.ar/NeoWebhookTest` no
   resuelve en DNS y hacía fallar el envío.)
4. **Application ID**: pegá el de Neotel.
5. **Access Token**: pegá el otro.
6. **Active**: marcado.
7. Click "**Save**".
8. Aparece la card verde con la **callback URL** completa. Click el botón
   "Copy".

### 10.3. Pegar la callback en Neotel

1. Volvé a la Aplicación Externa en Neotel.
2. Pegá la callback URL copiada en el campo "**Webhook URL**".
3. Guardá.

---

## 11. Test end-to-end

### 11.1. Cliente → agente (inbound)

1. Desde un teléfono que **NO sea el paireado**, mandá un WhatsApp al número
   paireado.
2. El mensaje aparece en:
   - Nuestro portal (número → Conversations) — confirmando que Evolution lo
     recibió y persistimos
   - Neotel — como conversación nueva del contacto, lista para que el agente la
     atienda

### 11.2. Agente → cliente (outbound)

1. En Neotel, abrí la conversación creada en el paso anterior.
2. El agente tipea un mensaje y manda.
3. Llega al teléfono original que escribió.

### 11.3. Verificar deliveries

En el portal: número → Webhook → tabla **Delivery history** (polling cada 10s).
Cada vez que entra un mensaje, ahí ves una entrada nueva con `success` (verde) y
HTTP 200 de Neotel. Si hay errores, click la fila para expandir el response
body — eso te dice exactamente qué falló.

---

## 12. Hacer que el stack sobreviva reboots

Por defecto los contenedores tienen `restart: unless-stopped`, así que si la VM
reinicia, Docker los relevanta automáticamente — **siempre que Docker mismo
arranque al boot**.

```bash
sudo systemctl enable docker
```

Probalo:

```bash
sudo reboot
# esperá ~1 min, reconectate por SSH
docker compose -f /opt/whatsapp-portal/docker-compose.yml -f /opt/whatsapp-portal/docker-compose.prod.yml ps
```

Los 6 contenedores tienen que estar arriba sin que vos hagas nada.

---

## 13. Mantenimiento

### Logs

```bash
# Todos los servicios
docker compose logs -f

# Solo el backend
docker compose logs -f backend

# Últimas 200 líneas del worker
docker compose logs --tail 200 worker
```

### Actualizar el código

```bash
cd /opt/whatsapp-portal
git pull
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
docker compose exec backend alembic upgrade head
```

### Backup de la base de datos

```bash
# Dump completo (corré como cron diario)
docker compose exec -T postgres pg_dump -U portal portal | gzip > /var/backups/portal-$(date +%F).sql.gz
```

Ejemplo de cron diario a las 03:00:

```bash
echo "0 3 * * * docker compose -f /opt/whatsapp-portal/docker-compose.yml exec -T postgres pg_dump -U portal portal | gzip > /var/backups/portal-\$(date +\%F).sql.gz" | sudo crontab -
```

### Reiniciar un servicio puntual

```bash
docker compose restart backend
docker compose restart worker
```

### Apagar todo (mantiene los datos)

```bash
docker compose down
```

### Apagar y **borrar todos los datos** (peligro)

```bash
docker compose down -v
```

---

## Troubleshooting rápido

**El frontend no abre desde el browser:**
- ¿La VM tiene la IP que pusiste en `.env`? `ip addr` adentro.
- ¿UFW está bloqueando el 3000? `sudo ufw status`.
- ¿El contenedor está corriendo? `docker compose ps frontend`.

**El QR del número no aparece o queda en `connecting`:**
- Mirá los logs de Evolution: `docker compose logs evolution`.
- Suele ser que el QR caducó (rotan cada 20s) — recargá la página del número.

**Neotel responde 4xx o no muestra la conversación:**
- Mirá el Delivery History en el portal — el response body te dice qué le falta
  al payload.
- Confirmá que la callback URL pegada en Neotel sea la actual (la que muestra
  el portal en la card verde después de Save).
- Confirmá que ApplicationId + AccessToken sean correctos (el AccessToken es
  case-sensitive y se renderiza como password en el form, ojo de copy/paste).

**El agente no ve el botón "Nuevo mensaje" / Cuenta para iniciar charla nueva:**
- Es esperable. La Aplicación Externa de Neotel es **customer-initiated only**.
  Si necesitás que el agente inicie, usá nuestro propio portal para mandar el
  primer mensaje (número → Conversations → typea en el textarea). Una vez que
  el cliente conteste, la charla aparece en Neotel para que el agente siga
  desde ahí.
