from fastapi import FastAPI, Request, BackgroundTasks
from google import genai
import os
import requests

app = FastAPI()

# ===============================
# VARIABLES DE ENTORNO
# ===============================
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
WHATSAPP_TOKEN = os.environ.get("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.environ.get("PHONE_NUMBER_ID")
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN")

# ===============================
# CLIENTE GEMINI (LIBRERÍA NUEVA)
# ===============================
client = genai.Client(api_key=GEMINI_API_KEY)

# ===============================
# LISTA DE VENDEDORES
# ===============================
telefonos_vendedores = [
    "51937065891", "51902266061", "51930462599", "51950159000", "51978738558",
    "51926855419", "51940080847", "51946763654", "51987122022", "51912018611",
    "51910221011", "51935359873", "51925277455"
]

# ===============================
# FUNCIÓN ENVÍO WHATSAPP
# ===============================
def enviar_a_whatsapp(telefono: str, texto: str):
    url = f"https://graph.facebook.com/v22.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "messaging_product": "whatsapp",
        "to": telefono,
        "type": "text",
        "text": {"body": texto}
    }

    r = requests.post(url, headers=headers, json=data)
    print(f"📤 WhatsApp: {r.status_code} - {r.text}", flush=True)

# ===============================
# PROCESAMIENTO IA
# ===============================
def procesar_ia(telefono_cliente: str, nombre_cliente: str, texto_usuario: str):
    try:
        es_vendedor = telefono_cliente in telefonos_vendedores

        if es_vendedor:
            contexto = (
                f"Eres InnovaBot, asistente INTERNO para el vendedor {nombre_cliente}. "
                "Da información técnica, precios internos y cuentas BCP: 194-2550181-0-51."
            )
        else:
            contexto = (
                f"Eres InnovaBot, experto en muebles para el cliente {nombre_cliente}. "
                "Sé amable, claro y persuade a la venta."
            )

        response = client.models.generate_content(
            model="gemini-3-pro-preview",
            contents=f"Contexto: {contexto}\nUsuario dice: {texto_usuario}"
        )

        # Seguridad: algunas respuestas no traen .text
        respuesta = response.text if hasattr(response, "text") else str(response)

        enviar_a_whatsapp(telefono_cliente, respuesta)

    except Exception as e:
        print(f"🔥 Error en procesamiento IA: {e}", flush=True)

# ===============================
# RUTA RAÍZ (OPCIONAL)
# ===============================
@app.get("/")
def home():
    return {"status": "InnovaBot activo"}

# ===============================
# VERIFICACIÓN WEBHOOK
# ===============================
@app.get("/webhook")
async def verify(mode: str = None, token: str = None, challenge: str = None):
    if mode == "subscribe" and token == VERIFY_TOKEN:
        print("✅ Webhook verificado", flush=True)
        return int(challenge)

# ===============================
# RECEPCIÓN DE MENSAJES
# ===============================
@app.post("/webhook")
async def webhook(request: Request, background_tasks: BackgroundTasks):
    data = await request.json()

    try:
        value = data["entry"][0]["changes"][0]["value"]

        if "messages" in value:
            msg_obj = value["messages"][0]

            telefono = msg_obj["from"]
            texto = msg_obj["text"]["body"]

            profile = value.get("contacts", [{}])[0].get("profile", {})
            nombre = profile.get("name", "Cliente")

            print(f"📩 Mensaje de {nombre} ({telefono}): {texto}", flush=True)

            background_tasks.add_task(
                procesar_ia,
                telefono,
                nombre,
                texto
            )

    except Exception as e:
        print(f"⚠️ Error webhook: {e}", flush=True)

    return {"status": "ok"}
