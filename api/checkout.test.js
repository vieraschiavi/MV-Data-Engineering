// Tests del checkout, con el runner nativo de Node (sin framework, como en web/ de MV SQL).
const assert = require("node:assert");
const { test } = require("node:test");
const handler = require("./checkout.js");
const { PRECIOS_USD, importe } = handler;
const { PRECIOS } = require("../landing/precios.js");

function res() {
  const r = { code: 0, body: null, headers: {} };
  r.status = (c) => { r.code = c; return r; };
  r.json = (b) => { r.body = b; return r; };
  r.setHeader = (k, v) => { r.headers[k] = v; };
  return r;
}
const req = (body, method = "POST") => ({ method, body, headers: { host: "x.test" } });

test("el precio de la landing y el del checkout son el mismo número", () => {
  // Un precio en dos lugares es un precio que en algún momento está mal en uno.
  for (const [plan, p] of Object.entries(PRECIOS_USD)) {
    assert.equal(p.usd, PRECIOS[plan].usd, `${plan}: landing ${PRECIOS[plan].usd} vs checkout ${p.usd}`);
  }
  assert.equal(PRECIOS.demo.usd, 0, "la demo se descarga, no se cobra");
});

test("la preferencia se arma en UYU, no en USD", async () => {
  // La cuenta de cobro es de Uruguay (MLU) y rechaza preferencias en USD:
  // sin esto no llega init_point y el checkout muere sin explicar por qué.
  assert.equal(importe(390), 390 * 40);
  assert.ok(Number.isInteger(importe(49)), "UYU no lleva centavos: importe entero");
});

test("un plan que no existe se rechaza antes de tocar MercadoPago", async () => {
  const r = res();
  await handler(req({ plan: "gratis_total" }), r);
  assert.equal(r.code, 400);
  assert.equal(r.body.ok, false);
});

test("sin token ni link configurado falla CERRADO y dice qué falta", async () => {
  delete process.env.MP_ACCESS_TOKEN;
  delete process.env.MP_LINK_LICENCIA;
  const r = res();
  await handler(req({ plan: "licencia" }), r);
  assert.equal(r.code, 503);
  assert.match(r.body.detalle, /MP_ACCESS_TOKEN|MP_LINK_LICENCIA/);
});

test("con link de pago configurado no hace falta el token", async () => {
  process.env.MP_LINK_LICENCIA = "https://mpago.la/algo";
  const r = res();
  await handler(req({ plan: "licencia" }), r);
  assert.equal(r.code, 200);
  assert.equal(r.body.url, "https://mpago.la/algo");
  delete process.env.MP_LINK_LICENCIA;
});

test("sólo POST", async () => {
  const r = res();
  await handler(req({ plan: "licencia" }, "GET"), r);
  assert.equal(r.code, 405);
});

test("el token nunca viaja en la respuesta", async () => {
  process.env.MP_ACCESS_TOKEN = "APP_USR-secreto-que-no-debe-salir";
  process.env.MP_LINK_MENSUAL = "https://mpago.la/mensual";
  const r = res();
  await handler(req({ plan: "mensual" }), r);
  assert.ok(!JSON.stringify(r.body).includes("secreto"), "el token se filtró en la respuesta");
  delete process.env.MP_ACCESS_TOKEN; delete process.env.MP_LINK_MENSUAL;
});
