// © 2026 Martín Viera. Todos los derechos reservados.
// Los precios viven ACÁ y en ningún otro lado: la landing los lee, el checkout
// los valida contra este mismo archivo. Un precio en dos lugares es un precio
// que en algún momento va a estar mal en uno de los dos.
//
// Referencia de mercado (septiembre 2026), para no inventar el número:
//   Weld / Hevo (mid-market)        USD  99–299 /mes   → 1.188–3.588 /año
//   Airbyte Cloud (plan pago)       USD 239     /mes   → 2.868       /año
//   Integrate.io (tarifa plana)     USD 1.999   /mes   → 23.988      /año
//   Fivetran                        por volumen de filas, sin techo
// MV Data Engineering se vende con LICENCIA PERPETUA: el pago único equivale a
// dos o tres meses del más barato de esa lista, y de ahí en adelante no se
// paga más. Ese es el argumento comercial, y por eso el mensual existe sólo
// como puerta de entrada sin fricción.
const PRECIOS = {
  demo:         { usd: 0,   tipo: "gratis" },
  licencia:     { usd: 390, tipo: "unico"  },  // alineado con MV Data Governance Professional
  professional: { usd: 890, tipo: "unico"  },  // + soporte y actualizaciones 12 meses
  mensual:      { usd: 49,  tipo: "mes"    },  // vs. 99–299 del mercado
};
if (typeof module !== "undefined") module.exports = { PRECIOS };
