// © 2026 Martín Viera. Todos los derechos reservados.
//
// Checkout de MercadoPago para MV Data Engineering — función serverless (Vercel,
// CommonJS). Mismo esquema que el de MV Kobra AI, con sus dos lecciones ya
// pagadas incorporadas:
//
// 1. **El token vive SOLO en el servidor** (`MP_ACCESS_TOKEN`). Nunca viaja al
//    navegador ni entra al repo. Sin token se puede operar con links de pago
//    por plan (`MP_LINK_<PLAN>`), que es el modo sin integración.
//
// 2. **La preferencia se crea en UYU, no en USD.** La cuenta de cobro es de
//    Uruguay (site MLU) y sólo acepta preferencias en pesos uruguayos: mandar
//    "USD" hace que la API rechace la preferencia, no llega `init_point` y el
//    checkout muere con «No se pudo iniciar el pago». Los precios se muestran
//    en USD como referencia y se cobran en UYU al tipo de cambio del día.
//
// POST + JSON y no un redirect: así el cliente recibe la URL y navega él, que
// es lo que permite adjuntar verificación antibot al pedido.

const PRECIOS_USD = {
  licencia:     { titulo: "MV Data Engineering · Licencia",                  usd: 390, recurrente: false },
  professional: { titulo: "MV Data Engineering · Professional (12 meses)",   usd: 890, recurrente: false },
  mensual:      { titulo: "MV Data Engineering · Mensual",                   usd: 49,  recurrente: true  },
};

const MONEDA = process.env.MP_CURRENCY || "UYU";
const TASA_UYU = Number(process.env.MP_TASA_UYU) || 40;   // US$1 ≈ $U 40, mismo valor que la landing
const API_MP = "https://api.mercadopago.com/checkout/preferences";

function baseDe(req) {
  const proto = (req.headers["x-forwarded-proto"] || "https").split(",")[0];
  const host = req.headers["x-forwarded-host"] || req.headers.host;
  return `${proto}://${host}`;
}

/** El importe que se le manda a MercadoPago. En UYU se redondea a peso entero:
 *  un importe con decimales en una moneda sin centavos de uso corriente es una
 *  fuente de diferencias de un peso entre lo que dice la web y lo que cobra. */
function importe(usd) {
  return MONEDA === "UYU" ? Math.round(usd * TASA_UYU) : usd;
}

module.exports = async function handler(req, res) {
  if (req.method !== "POST") {
    res.setHeader("Allow", "POST");
    return res.status(405).json({ ok: false, error: "método no permitido" });
  }
  const { plan, lang = "es", email = "" } = req.body || {};
  const item = PRECIOS_USD[plan];
  if (!item) return res.status(400).json({ ok: false, error: "plan desconocido" });

  // Modo sin integración: un link de pago por plan, cargado por variable de
  // entorno. Sirve para vender antes de tener el token configurado.
  const link = process.env[`MP_LINK_${plan.toUpperCase()}`];
  if (link) return res.status(200).json({ ok: true, url: link, modo: "link" });

  const token = process.env.MP_ACCESS_TOKEN;
  if (!token) {
    // Falla CERRADO y con un motivo accionable: sin token no se inventa un
    // checkout que después no cobra.
    return res.status(503).json({ ok: false, error: "pago no configurado", detalle: "falta MP_ACCESS_TOKEN o MP_LINK_" + plan.toUpperCase() });
  }

  const base = baseDe(req);
  const preferencia = {
    items: [{
      title: item.titulo,
      quantity: 1,
      unit_price: importe(item.usd),
      currency_id: MONEDA,
      description: item.recurrente ? "Suscripción mensual" : "Licencia perpetua",
    }],
    metadata: { plan, lang, usd: item.usd, moneda: MONEDA, tasa: TASA_UYU },
    back_urls: {
      success: `${base}/gracias.html?plan=${plan}&lang=${lang}`,
      pending: `${base}/gracias.html?plan=${plan}&lang=${lang}&estado=pendiente`,
      failure: `${base}/?lang=${lang}#precios`,
    },
    auto_return: "approved",
    statement_descriptor: "MV DATA ENG",
    ...(email ? { payer: { email } } : {}),
  };

  try {
    const r = await fetch(API_MP, {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
      body: JSON.stringify(preferencia),
    });
    const data = await r.json().catch(() => ({}));
    const url = data.init_point || data.sandbox_init_point;
    if (!r.ok || !url) {
      // El motivo de MercadoPago se registra del lado del servidor; al cliente
      // se le da un mensaje que pueda leer, sin filtrar la respuesta cruda.
      console.error("MP rechazó la preferencia:", r.status, JSON.stringify(data).slice(0, 400));
      return res.status(502).json({ ok: false, error: "no se pudo iniciar el pago" });
    }
    return res.status(200).json({ ok: true, url, modo: "preferencia", moneda: MONEDA, importe: importe(item.usd) });
  } catch (e) {
    console.error("checkout:", e);
    return res.status(502).json({ ok: false, error: "no se pudo iniciar el pago" });
  }
};

module.exports.PRECIOS_USD = PRECIOS_USD;
module.exports.importe = importe;
