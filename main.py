from fastapi import FastAPI, Request, HTTPException, Query, BackgroundTasks
import google.generativeai as genai
import uvicorn
import requests
import json
import os 

app = FastAPI()

# Configuración desde variables de entorno
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
WHATSAPP_TOKEN = os.environ.get("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.environ.get("PHONE_NUMBER_ID") 
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN")

# --- CONFIGURACIÓN GEMINI ---
genai.configure(api_key=GEMINI_API_KEY)
# Nota: Asegúrate que el modelo sea 'gemini-1.5-flash' o el que tengas habilitado
model = genai.GenerativeModel('gemini-2.5-flash')

chat_sessions = {}
telefonos_vendedores = [
    "51937065891", "51902266061","51930462599","51950159000","51978738558",
    "51926855419","51940080847","51946763654","51987122022","51912018611",
    "51910221011","51935359873","51925277455"
] 

def procesar_mensaje(telefono_cliente, nombre_cliente, texto_usuario):
    # El flush=True es vital para ver el log en Render inmediatamente
    print(f"🤖 Procesando mensaje para {nombre_cliente}...", flush=True)
    
    try:
        es_vendedor = telefono_cliente in telefonos_vendedores
        
        if telefono_cliente not in chat_sessions:
            if es_vendedor:
                CONTEXTO = """
                Eres InnovaBot, el asistente interno exclusivo para el equipo de ventas de Innova Mobili.
                Tu rol es dar información precisa, técnica y confidencial solo a los vendedores.
                Datos confidenciales: BCP Cuenta Corriente: 194-2550181-0-51, a nombre de Innova Mobili SAC.
                """
                mensaje_inicial = "Entendido. Iniciando sesión como asistente interno."
            else:
                CONTEXTO = """
                Eres InnovaBot, experto en muebles de Innova Mobili.
                Sé breve, amable y persuade a la venta.
                """
                mensaje_inicial = "Entendido, soy InnovaBot."
                
            chat_sessions[telefono_cliente] = model.start_chat(history=[
                {"role": "user", "parts": [CONTEXTO]},
                {"role": "model", "parts": [mensaje_inicial]}
            ])
        
        chat = chat_sessions[telefono_cliente]
        
        # Generar respuesta con Gemini
        response = chat.send_message(texto_usuario)
        respuesta_bot = response.text
        print(f"🧠 Respuesta generada para {telefono_cliente}: {respuesta_bot[:50]}...", flush=True)

        # Enviar a WhatsApp (v22.0 o v18.0 son recomendadas)
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
            print(f"✅ Mensaje ENVIADO exitosamente a {telefono_cliente}", flush=True)
        else:
            print(f"❌ ERROR AL ENVIAR WHATSAPP: {envio.status_code} - {envio.text}", flush=True)

    except Exception as e:
        print(f"🔥 Error CRÍTICO en la lógica del bot: {str(e)}", flush=True)


@app.get("/webhook")
async def verify_webhook(mode: str = Query(None, alias="hub.mode"),
                         token: str = Query(None, alias="hub.verify_token"),
                         challenge: str = Query(None, alias="hub.challenge")):
    if mode == "subscribe" and token == VERIFY_TOKEN:
        print("✅ Webhook verificado correctamente por Meta", flush=True)
        return int(challenge)
    raise HTTPException(status_code=403, detail="Token de verificación inválido")

@app.post("/webhook")
async def whatsapp_webhook(request: Request, background_tasks: BackgroundTasks):
    try:
        body = await request.json()
        
        # Verificar que sea un mensaje de WhatsApp
        if "entry" in body and body["entry"][0]["changes"][0]["value"].get("messages"):
            value = body["entry"][0]["changes"][0]["value"]
            message_data = value["messages"][0]
            
            telefono_cliente = message_data["from"]
            texto_usuario = message_data.get("text", {}).get("body", "")
            
            # Obtener nombre del perfil
            profile = value.get("contacts", [{}])[0].get("profile", {})
            nombre_cliente = profile.get("name", "Cliente")

            print(f"📩 NUEVO MENSAJE: De {nombre_cliente} ({telefono_cliente}): {texto_usuario}", flush=True)

            # Ejecutar lógica pesada en segundo plano
            background_tasks.add_task(procesar_mensaje, telefono_cliente, nombre_cliente, texto_usuario)
            
            return {"status": "received"}
        
        return {"status": "event_ignored"}

    except Exception as e:
        print(f"⚠️ Error procesando JSON entrante: {e}", flush=True)
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)