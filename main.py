from fastapi import FastAPI, Request, HTTPException, Query, BackgroundTasks
import google.generativeai as genai
import uvicorn
import requests
import os 

app = FastAPI()

# --- CONFIGURACIÓN DE VARIABLES DE ENTORNO ---
# Estas se leen directamente de tu panel de Render
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
WHATSAPP_TOKEN = os.environ.get("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.environ.get("PHONE_NUMBER_ID") 
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN")

# --- CONFIGURACIÓN GEMINI ---
genai.configure(api_key=GEMINI_API_KEY)
# Usamos el nombre técnico exacto de tu captura de Google AI Studio
model = genai.GenerativeModel('gemini-3-pro-preview') 

chat_sessions = {}
telefonos_vendedores = [
    "51937065891", "51902266061", "51930462599", "51950159000", "51978738558",
    "51926855419", "51940080847", "51946763654", "51987122022", "51912018611",
    "51910221011", "51935359873", "51925277455"
] 

def procesar_mensaje(telefono_cliente, nombre_cliente, texto_usuario):
    print(f"🤖 Procesando mensaje para {nombre_cliente}...", flush=True)
    
    try:
        es_vendedor = telefono_cliente in telefonos_vendedores
        
        # 1. Inicializar sesión de chat si es nueva
        if telefono_cliente not in chat_sessions:
            if es_vendedor:
                CONTEXTO = """Eres InnovaBot, el asistente interno exclusivo para el equipo de ventas de Innova Mobili.
                Tu rol es dar información precisa, técnica y confidencial solo a los vendedores.
                Datos confidenciales: BCP Cuenta Corriente: 194-2550181-0-51, a nombre de Innova Mobili SAC."""
                mensaje_inicial = "Entendido. Iniciando sesión como asistente interno."
            else:
                CONTEXTO = """Eres InnovaBot, experto en muebles de Innova Mobili.
                Sé breve, amable y persuade a la venta."""
                mensaje_inicial = "Entendido, soy InnovaBot."
            
            # Nota: 'parts' debe ser una lista [] como indica la documentación
            chat_sessions[telefono_cliente] = model.start_chat(history=[
                {"role": "user", "parts": [CONTEXTO]},
                {"role": "model", "parts": [mensaje_inicial]}
            ])
        
        chat = chat_sessions[telefono_cliente]
        
        # 2. Generar respuesta con Gemini 3
        response = chat.send_message(texto_usuario)
        respuesta_bot = response.text

        # 3. Enviar a WhatsApp usando la versión v22.0
        url = f"https://graph.facebook.com/v22.0/{PHONE_NUMBER_ID}/messages"
        headers = {
            "Authorization": f"Bearer {WHATSAPP_TOKEN}",
            "Content-Type": "application/json"
        }
        data = {
            "messaging_product": "whatsapp",
            "to": telefono_cliente,
            "type": "text",
            "text": {"body": respuesta_bot}
        }
        
        envio = requests.post(url, headers=headers, json=data)
        
        if envio.status_code == 200:
            print(f"✅ Mensaje enviado a {telefono_cliente}", flush=True)
        else:
            print(f"❌ ERROR WHATSAPP: {envio.status_code} - {envio.text}", flush=True)

    except Exception as e:
        print(f"🔥 Error en la lógica del bot: {str(e)}", flush=True)


@app.get("/webhook")
async def verify_webhook(mode: str = Query(None, alias="hub.mode"),
                         token: str = Query(None, alias="hub.verify_token"),
                         challenge: str = Query(None, alias="hub.challenge")):
    # El Verify Token debe coincidir con el de Render: Guarana1z
    if mode == "subscribe" and token == VERIFY_TOKEN:
        print("✅ Webhook validado correctamente", flush=True)
        return int(challenge)
    raise HTTPException(status_code=403, detail="Token de verificación incorrecto")

@app.post("/webhook")
async def whatsapp_webhook(request: Request, background_tasks: BackgroundTasks):
    try:
        data = await request.json()
        entry = data["entry"][0]
        changes = entry["changes"][0]
        value = changes["value"]
        
        if "messages" in value:
            message_data = value["messages"][0]
            telefono_cliente = message_data["from"]
            texto_usuario = message_data.get("text", {}).get("body", "")
            
            profile = value.get("contacts", [{}])[0].get("profile", {})
            nombre_cliente = profile.get("name", "Cliente")

            print(f"📩 Recibido de {nombre_cliente}: {texto_usuario}", flush=True)

            # Usamos background_tasks para responder rápido a Meta y procesar la IA en paralelo
            background_tasks.add_task(procesar_mensaje, telefono_cliente, nombre_cliente, texto_usuario)
            
        return {"status": "received"}
    except Exception:
        return {"status": "ignored"}

if __name__ == "__main__":
    # Render usa el puerto 10000 por defecto
    uvicorn.run(app, host="0.0.0.0", port=10000)