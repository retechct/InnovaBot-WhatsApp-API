from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import PlainTextResponse
from google import genai
import os
import requests

app = FastAPI()

# ===============================
# VARIABLES DE ENTORNO
# ===============================
GEMINI_API_KEY = "AIzaSyDpDSoV9me-22A9W-9UyrSi4dDqH1fR91Q"
WHATSAPP_TOKEN = "EAAXeWdWIwHIBQTyb79jfXmjVWoo0MLSgzEGCuElVdPtq26h34rEXuc0BRMrqUrzE6jZCZBjjyI7hdlZBHnZCtZCtdfGEdaFJUIRSgbJ4UHQNRdU57UsqI0VleZAwZBJYlZA8v1BZAZAsQgr0pMRzIFFZBZC5mJZBWALQ08xhWAcrAZCaX6y7arFtAxM2RioSYEZC70PZAP2ZBmQZDZD"
PHONE_NUMBER_ID = "962569226933249" 
VERIFY_TOKEN = "1525" 

# ===============================
# CLIENTE GEMINI 3 (NUEVA GENERACIÓN)
# ===============================
client = genai.Client(api_key=GEMINI_API_KEY)

# ===============================
# TU ROTADOR DE VENDEDORES
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
# PROCESAMIENTO CON GEMINI 3 PRO PREVIEW
# ===============================
def procesar_ia(telefono_cliente: str, nombre_cliente: str, texto_usuario: str):
    try:
        es_vendedor = telefono_cliente in telefonos_vendedores
        contexto = (
            f"Eres InnovaBot con Gemini 3, asistente interno para el vendedor {nombre_cliente}. Da precios técnicos."
            if es_vendedor else 
            f"Eres InnovaBot con Gemini 3, experto en muebles para el cliente {nombre_cliente}. Sé muy persuasivo."
        )

        # USANDO EL ÚLTIMO MODELO GEMINI 3 PRO PREVIEW
        response = client.models.generate_content(
            model="gemini-3-pro-preview", 
            contents=f"Contexto: {contexto}\nUsuario dice: {texto_usuario}"
        )

        respuesta = response.text if hasattr(response, "text") else str(response)
        enviar_a_whatsapp(telefono_cliente, respuesta)

    except Exception as e:
        print(f"🔥 Error en IA Gemini 3: {e}", flush=True)

# ===============================
# VERIFICACIÓN WEBHOOK (TEXTO PLANO PARA META)
# ===============================
@app.get("/webhook", response_class=PlainTextResponse)
async def verify(request: Request):
    params = request.query_params
    if params.get("hub.mode") == "subscribe" and params.get("hub.verify_token") == VERIFY_TOKEN:
        print("✅ Webhook verificado con Gemini 3", flush=True)
        return params.get("hub.challenge")
    return "Error"

# ===============================
# RECEPCIÓN DE MENSAJES REALES
# ===============================
@app.post("/webhook")
async def webhook(request: Request, background_tasks: BackgroundTasks):
    data = await request.json()
    if "entry" in data:
        value = data["entry"][0]["changes"][0]["value"]
        if "messages" in value:
            msg = value["messages"][0]
            nombre = value.get("contacts", [{}])[0].get("profile", {}).get("name", "Cliente")
            print(f"📩 Mensaje de {nombre} ({msg['from']}): {msg['text']['body']}", flush=True)
            background_tasks.add_task(procesar_ia, msg["from"], nombre, msg["text"]["body"])
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)