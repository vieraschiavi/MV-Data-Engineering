# Landing de MV Data Engineering

Estática, sin build. Se sirve tal cual (`python3 -m http.server` para probar) y
se despliega en Vercel con las funciones de `api/` al lado.

## El idioma es un solo estado

`index.html` no tiene tres versiones: tiene un diccionario (`i18n.js`) y un
estado. Cuando el visitante toca ES/EN/PT cambian **a la vez** el texto, las
capturas de pantalla y el video con su locución. Con tres HTML separados eso se
mantiene a mano y se desincroniza en la primera edición.

El idioma sale, en orden: `?lang=`, lo último elegido (`localStorage`), el del
navegador, y si no, español.

## Los precios están en un solo lugar

`precios.js`. La landing los muestra y `api/checkout.test.js` **falla** si el
número del checkout no coincide con el de la landing. Un precio en dos archivos
es un precio que en algún momento va a estar mal en uno de los dos.

## Capturas

`img/<idioma>_<n>_<pantalla>.jpg` — reales, del programa corriendo la demo
`cartera`, tomadas con Playwright a escala 2 y guardadas como JPEG progresivo
(10,4 MB → 2,5 MB). Nombres sólo ASCII: un `õ` en el nombre de archivo rompe en
algunos servidores.

Para regenerarlas: levantar la app (`streamlit run app/app.py`), correr la demo
`cartera` y capturar las pestañas Pipeline, Salud, Cargas, Transformaciones y
Relevamiento en los tres idiomas.

## Videos

`video/MVDataEngineering_Comercial_<idioma>.mp4` y
`video/MVDataEngineering_Demo_<idioma>.mp4`.

Si el archivo del idioma no existe, la landing **esconde el reproductor y lo
dice**: un `<video>` roto es peor que no tener video.

Los `.mp4` no se versionan (`.gitignore`): se generan y se publican al hosting.

## Pago

`pago.html` → `api/checkout.js`. Dos cosas que no se tocan:

- El **Access Token de MercadoPago vive sólo como variable de entorno del
  servidor** (`MP_ACCESS_TOKEN`). Sin token, `MP_LINK_<PLAN>` permite vender con
  un link de pago. Sin ninguno de los dos, el checkout **falla cerrado** y dice
  qué falta — no simula un pago que después no cobra.
- **La preferencia se crea en UYU, no en USD.** La cuenta de cobro es de Uruguay
  (site MLU) y sólo acepta pesos uruguayos: mandar `USD` hace que MercadoPago
  rechace la preferencia, no llega `init_point` y el checkout muere con «No se
  pudo iniciar el pago». Los precios se muestran en USD y se cobran en UYU al
  tipo de cambio del día (`MP_TASA_UYU`), y `pago.html` lo avisa **antes** de
  cobrar: enterarse en el resumen de la tarjeta es una queja.

## Variables de entorno

| Variable | Para qué |
|---|---|
| `MP_ACCESS_TOKEN` | Token de MercadoPago (servidor). Nunca al navegador. |
| `MP_LINK_LICENCIA` / `_PROFESSIONAL` / `_MENSUAL` | Links de pago, alternativa sin token. |
| `MP_CURRENCY` | Moneda de la preferencia. Por defecto `UYU`. |
| `MP_TASA_UYU` | Tipo de cambio de referencia. Por defecto 40. |

## Verificación

```bash
node --test api/checkout.test.js      # 7 tests: precios alineados, UYU, falla cerrada, token no se filtra
cd landing && python3 -m http.server 8620
```
