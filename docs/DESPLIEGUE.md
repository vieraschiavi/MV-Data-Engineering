# MV Data Engineering · puesta en marcha en un servidor

Para el área de infraestructura del cliente. Una carilla: qué es, qué necesita,
cómo se levanta y cómo se apaga.

## Qué es y por qué no se instala nada

Es una aplicación web en Python. Corre en un servidor y la gente entra con el
navegador, como a cualquier intranet. **No se instala nada en la PC de los
usuarios**, no hay `.exe` ni `.bat` que repartir, y no requiere permisos de
administrador en los puestos de trabajo.

Los datos no salen del servidor donde se instala. La aplicación no llama a
ningún servicio externo salvo que alguien configure a mano un proveedor de IA
con su propia clave, que es opcional y viene apagado.

## Qué necesita

| Recurso | Mínimo | Recomendado |
|---|---|---|
| CPU | 2 vCPU | 4 vCPU |
| RAM | 2 GB | 4 GB |
| Disco | 5 GB | 20 GB, según el volumen de datos |
| Sistema | Linux con Docker, o Linux/Windows con Python 3.11+ | Linux con Docker |
| Red | Un puerto interno (8501 por defecto) detrás del proxy corporativo | — |

No necesita salida a internet para funcionar. Sí la necesita **una sola vez**,
al construir la imagen, para bajar las dependencias de Python. Si la VM no
tiene salida, se construye la imagen en otra máquina y se transfiere con
`docker save` / `docker load`.

## Puesta en marcha con Docker

```bash
# 1. Crear las credenciales. Una línea por persona; pide la contraseña sin
#    mostrarla y devuelve la línea ya hasheada. La contraseña no se guarda.
mkdir -p secretos datos
python3 -m mvde usuario martin >> secretos/usuarios.txt

# 2. Levantar
docker compose up -d --build

# 3. Verificar
curl -s localhost:8501/_stcore/health     # responde "ok"
docker compose logs -f mvde
```

La aplicación queda escuchando en `127.0.0.1:8501`, **sólo en la VM**. El
último paso es publicarla por el proxy corporativo (nginx, Traefik, IIS) con
HTTPS y el nombre interno que corresponda.

Para apagarla: `docker compose down`. Para actualizarla: `git pull` y repetir
el paso 2. Los proyectos y las salidas viven en `datos/`, fuera del contenedor,
así que una actualización no borra nada.

### Sin Docker

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
export MVDE_USUARIOS_ARCHIVO=/ruta/a/secretos/usuarios.txt
.venv/bin/streamlit run app/app.py --server.port 8501 --server.address 0.0.0.0
```

Conviene dejarlo como servicio de systemd para que arranque solo tras un
reinicio.

## Seguridad

- **El login se activa solo cuando se declaran usuarios.** Con
  `MVDE_USUARIOS_ARCHIVO` (o `MVDE_USUARIOS`) apuntando a credenciales
  válidas, nadie entra sin usuario y contraseña. Sin esa variable **no hay
  login**: eso es correcto para el uso de escritorio y es inaceptable en un
  servidor, así que verificá que la variable esté puesta antes de publicar.
- Las contraseñas se guardan como PBKDF2-HMAC-SHA256 con sal por usuario y
  200.000 iteraciones. En texto plano no quedan en ningún lado.
- Cinco intentos fallidos bloquean al usuario cinco minutos.
- **Publicala siempre detrás de HTTPS.** La sesión viaja por la red; sin TLS
  la contraseña también.
- Esto es autenticación propia, **no es SSO corporativo**. Si la política exige
  Entra ID / Okta, el proxy debe hacer la autenticación adelante.
- Si el proyecto se conecta a una base, usá una cuenta de servicio **de sólo
  lectura**. La aplicación nunca escribe en las bases de origen, pero la cuenta
  no tiene por qué poder hacerlo.
- Quien entra puede subir archivos y consultar las bases que estén declaradas.
  Dar usuario es dar ese acceso: creá uno por persona, no uno compartido.

### Una trampa verificada, para no perder una tarde

**No pongas el hash de la contraseña en un archivo `.env` de Docker Compose.**
Compose interpola las variables y se come el último tramo del hash: el valor
`...$bf59cdeb...` lo toma como una variable llamada `bf59cdeb...`, no la
encuentra y la borra. El contenedor arranca sin un solo error y nadie puede
entrar. Por eso las credenciales van en un archivo montado, que Compose nunca
toca.

## Qué queda afuera en el contenedor

La etapa de Power BI genera el `.pbit` usando MV DAX Lab, que vive en el repo
hermano. Si no está presente, esa etapa **se omite y el pipeline sigue**: se
generan igual las medidas DAX, el reporte HTML, el Excel y la bitácora. No es
un error, aparece marcada como omitida.

## Si algo falla

| Síntoma | Causa habitual |
|---|---|
| No abre la página | El proxy no apunta al puerto, o el contenedor no está arriba (`docker compose ps`) |
| Pide login y ninguna clave entra | El archivo de credenciales no se montó, o el hash se cortó (ver la trampa de arriba) |
| «Demasiados intentos fallidos» | Bloqueo por cinco minutos; se libera solo, o reiniciando el contenedor |
| El pipeline se queda sin memoria | Subir `mem_limit` en `docker-compose.yml` |
| La etapa Power BI aparece omitida | Es lo esperado sin MV DAX Lab presente |
