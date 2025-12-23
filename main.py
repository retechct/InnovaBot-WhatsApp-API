from fastapi import FastAPI, Request, BackgroundTasks
from google import genai 
import os
import requests

app = FastAPI()

# --- VARIABLES DE ENTORNO ---
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
WHATSAPP_TOKEN = os.environ.get("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.environ.get("PHONE_NUMBER_ID")
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN")

# Cliente de Gemini 3 (Librería nueva)
client = genai.Client(api_key=GEMINI_API_KEY)

# --- LISTA DE VENDEDORES PARA ROTACIÓN/RECONOCIMIENTO ---
telefonos_vendedores = [
    "51937065891", "51902266061", "51930462599", "51950159000", "51978738558",
    "51926855419", "51940080847", "51946763654", "51987122022", "51912018611",
    "51910221011", "51935359873", "51925277455"
]

def enviar_a_whatsapp(telefono, texto):
    url = f"https://graph.facebook.com/v22.0/{PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}", "Content-Type": "application/json"}
    data = {
        "messaging_product": "whatsapp",
        "to": telefono,
        "type": "text",
        "text": {"body": texto}
    }
    r = requests.post(url, headers=headers, json=data)
    print(f"Respuesta de WhatsApp: {r.status_code} - {r.text}", flush=True)

def procesar_ia(telefono_cliente, nombre_cliente, texto_usuario):
    try:
        # Determinar el ROL del usuario
        es_vendedor = telefono_cliente in telefonos_vendedores
        
        if es_vendedor:
            CONTEXTO = f"Eres InnovaBot, asistente INTERNO para el vendedor {nombre_cliente}. Da info técnica y cuentas BCP: 194-2550181-0-51."
        else:
            CONTEXTO = f"Eres InnovaBot, experto en muebles para el cliente {nombre_cliente}. Sé amable y persuade a la venta."

        # Llamada a Gemini 3 según tu documentación oficial
        response = client.models.generate_content(
            model="gemini-3-pro-preview",
            contents=f"Contexto: {CONTEXTO}\nUsuario dice: {texto_usuario}"
        )
        
        enviar_a_whatsapp(telefono_cliente, response.text)
        
    except Exception as e:
        print(f"🔥 Error en procesamiento: {e}", flush=True)

@app.get("/webhook")
async def verify(mode: str = None, token: str = None, challenge: str = None):
    if mode == "subscribe" and token == VERIFY_TOKEN:
        print("✅ Webhook verificado", flush=True)
        return int(challenge)

@app.post("/webhook")
async def webhook(request: Request, background_tasks: BackgroundTasks):
    data = await request.json()
    try:
        if "messages" in data["entry"][0]["changes"][0]["value"]:
            value = data["entry"][0]["changes"][0]["value"]
            msg_obj = value["messages"][0]
            
            telefono = msg_obj["from"]
            texto = msg_obj["text"]["body"]
            
            profile = value.get("contacts", [{}])[0].get("profile", {})
            nombre = profile.get("name", "Cliente")
            
            print(f"📩 Mensaje de {nombre} ({telefono}): {texto}", flush=True)
            
            # Mandar a procesar en segundo plano
            background_tasks.add_task(procesar_ia, telefono, nombre, texto)
    except:
        pass
    return {"status": "ok"}