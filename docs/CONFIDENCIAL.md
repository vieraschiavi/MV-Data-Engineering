# Trabajar con datos de un cliente sin que salgan de su red

Guía para el caso de consultoría: una empresa contratista pone a una persona en
un proyecto para un cliente, y **los datos del cliente no pueden estar en la
laptop del consultor** — ni personal ni corporativa. El acuerdo suele
prohibirlo, y la responsabilidad de que no pase no es de quien configuró: es de
quien entregó una herramienta que podía.

## La regla que ordena todo lo demás

> **El programa corre donde están los datos. La persona sólo aporta el navegador.**

Todo lo que sigue son formas de cumplir esa regla según cuánta infraestructura
haya disponible. Si en algún escenario no se puede cumplir, la respuesta
correcta no es «con cuidado»: es **no procesar datos del cliente en esa
máquina**.

## Lo que este producto NO pide

Conviene tenerlo a mano para la conversación con seguridad, porque suele ser la
primera pregunta:

- **No pide licencia, ni clave de producto, ni activación.** No hay `licencia.py`
  en el motor y ninguna función escribe ni valida un serial. Nada llama a casa
  para autorizar la ejecución.
- **No manda telemetría.** `browser.gatherUsageStats` está en `false` en la
  configuración y en el `CMD` de la imagen.
- **No necesita permisos de administrador** en ninguna de sus formas.

## Los tres escenarios, de menos a más restrictivo

### 1 · El cliente da una VM o un servidor — el caso normal

El programa se despliega en la infraestructura del cliente y se entra por
navegador con usuario y contraseña.

```bash
docker compose -f docker-compose.yml -f docker-compose.confidencial.yml up -d
```

| | |
|---|---|
| Dónde viven los datos | Volumen `./datos` de la VM del cliente |
| Qué se instala en la laptop del consultor | **Nada** |
| Qué queda en la laptop del consultor | **Nada**: lo que ve es HTML servido |
| Restricción de la laptop corporativa | Irrelevante: alcanza con un navegador |

Esto resuelve al mismo tiempo los dos problemas: la laptop que no deja instalar
`.exe` ni `.bat` no necesita instalar nada, y los datos nunca la tocan.

Antes de empezar, generar las credenciales **en la VM**:

```bash
python -m mvde usuario mviera     # pide la contraseña sin mostrarla
```

La línea que devuelve va a `secretos/usuarios.txt`. La contraseña en sí no se
guarda en ningún lado.

### 2 · No hay VM, pero hay una máquina del cliente

El instalador de Windows (`MV_DataEngineering_Setup.exe`) se instala **en una
máquina del cliente**, no en la del consultor. No pide administrador, así que
suele poder hacerlo el propio usuario del área.

El consultor trabaja sentado al lado o por escritorio compartido. Los datos no
se mueven.

Con el modo confidencial encendido en esa máquina:

```
setx MVDE_CONFIDENCIAL 1
```

### 3 · No hay VM ni máquina del cliente disponible — el caso de mayor restricción

**No se procesan datos del cliente.** No hay una versión del programa que haga
seguro tener los datos en una máquina donde no deberían estar; lo único que
cambiaría es cuánto se tarda en notarlo.

Lo que **sí** se puede hacer en la laptop del consultor, sin ningún dato del
cliente:

- Correr las **demos sintéticas** (`python -m mvde demo conaprole ...`) para
  diseñar el modelo, preparar el relevamiento y mostrar la herramienta.
- Escribir el **YAML del proyecto**: es una declaración de estructura, no
  contiene datos.
- Preparar **reglas de calidad, medidas y documentación**.

Y en paralelo, la conversación que destraba el escenario: pedirle al cliente una
VM chica. Es un pedido barato de justificar cuando la alternativa es que sus
datos salgan de su red.

## Qué bloquea exactamente el modo confidencial

Con `MVDE_CONFIDENCIAL=1`, el motor **corta con una excepción** en los cuatro
caminos por los que un dato puede cruzar el borde de la red:

| Camino | Qué pasa |
|---|---|
| Fuente `url` (`http://`, `https://`) | Bloqueada |
| Ruta de nube (`s3://`, `gs://`, `az://`, `abfs://`, `adl://`) | Bloqueada |
| Descarga de un dataset de Kaggle | Bloqueada (un archivo ya bajado se lee igual) |
| Consulta a un proveedor de IA | La IA cae al **modo local**, que responde con los datos de la corrida sin salir |

Lo que **no** bloquea, a propósito: fuentes SQL y archivos locales. Son la red
del cliente y el disco de su propia VM. El borde que se defiende es la **salida**
de la infraestructura, no el acceso a lo que ya está adentro — bloquearlas
dejaría al producto sin poder leer los datos que vino a procesar.

## Cómo se demuestra que funciona

No alcanza con decir que está apagado por defecto. La garantía se verifica:

```bash
pytest tests/test_confidencial.py -v
```

Cada test recorre un camino de salida real con el modo encendido y comprueba que
corta — y, tan importante como eso, que con el modo apagado el camino sigue
existiendo, para que nadie confunda «bloqueado» con «roto».

Además, **cada corrida deja constancia por escrito**. El `manifiesto.json` de la
entrega lleva:

```json
"confidencial": {
  "activo": true,
  "variable": "MVDE_CONFIDENCIAL",
  "bloquea": ["fuentes url", "fuentes kaggle", "rutas de nube",
              "proveedores de IA"],
  "nota": "Esta corrida no pudo sacar datos de la red donde se ejecutó."
}
```

y el `RESUMEN.md` abre con el sello del modo. Una corrida sobre datos de un
cliente que no deja constancia de en qué modo se ejecutó obliga a confiar en la
memoria de alguien.

## Las tres capas, y por qué ninguna alcanza sola

| Capa | Qué hace | Quién la administra |
|---|---|---|
| **1 · La aplicación se niega** | `MVDE_CONFIDENCIAL=1` | Viaja con el programa. Se verifica en cada build |
| **2 · El contenedor no puede hacer de más** | Sin capacidades, sin privilegios nuevos, disco raíz de sólo lectura | El `docker-compose.confidencial.yml` |
| **3 · La red no lo deja salir** | Regla de egreso en el firewall de la VM | Infraestructura del cliente |

La capa 3 es la más fuerte y la única que no controla quien entrega el software:
la administra otra gente y cambia sin avisar. Por eso la capa 1 existe y por eso
se testea — es la que sobrevive a que alguien mueva la VM de red un martes.

Si la capa 3 no se puede aplicar, el despliegue **no queda desprotegido**: lo que
se pierde es la defensa en profundidad. Conviene dejarlo escrito en el acta del
proyecto en vez de asumir que alguien lo hizo.

## Checklist antes de tocar el primer dato real

- [ ] El programa corre en infraestructura del cliente, no en la laptop del consultor
- [ ] `MVDE_CONFIDENCIAL=1` está puesto y el `RESUMEN.md` de una corrida de prueba lo muestra
- [ ] `pytest tests/test_confidencial.py` en verde en ese despliegue
- [ ] Login activo: `secretos/usuarios.txt` con una línea por persona, generado en la VM
- [ ] El puerto no está publicado en `0.0.0.0`; sale por reverse proxy con HTTPS
- [ ] Regla de egreso pedida a infraestructura (o su ausencia, anotada en el acta)
- [ ] Acordado por escrito quién borra el volumen `./datos` cuando el proyecto termina
