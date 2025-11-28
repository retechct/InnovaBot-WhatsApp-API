from fastapi import FastAPI, Request, HTTPException, Query, BackgroundTasks
import google.generativeai as genai
import uvicorn
import requests
import json
import os # Necesitas esta librería para leer variables de entorno

app = FastAPI()

# --- ACTUALIZA ESTO CON TUS NUEVAS CLAVES ---
# NOTA: En producción, estos valores se leerán de las Variables de Entorno de Render.

# Lee las variables de entorno para las claves. Si no las encuentra (ej: en local), usa un valor por defecto.
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "TU_CLAVE_GEMINI_AQUI")
WHATSAPP_TOKEN = os.environ.get("WHATSAPP_TOKEN", "TU_TOKEN_WHATSAPP_AQUI")
PHONE_NUMBER_ID = os.environ.get("PHONE_NUMBER_ID", "911239725403166") 
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN", "Guarana1z")

# --- CONFIGURACIÓN GEMINI ---
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash')

# Variables globales
chat_sessions = {}
# Esta lista de vendedores deberá ser cargada desde una base de datos o variable de entorno en un entorno real.
telefonos_vendedores = ["51937065891", "51902266061","51930462599","51950159000","51978738558","51926855419","51940080847","51946763654","51987122022","51912018611","51910221011","51935359873","51925277455"] 

# --- FUNCIÓN DE PROCESAMIENTO (SE EJECUTA EN 2DO PLANO) ---
# Hemos incluido la lógica de ROL (Vendedor vs. Cliente) en esta versión para ser completa.
def procesar_mensaje(telefono_cliente, nombre_cliente, texto_usuario):
    print(f"🤖 Procesando mensaje para {nombre_cliente}...")
    
    try:
        # Determinar el ROL del usuario
        es_vendedor = telefono_cliente in telefonos_vendedores
        
        # 1. Inicializar Historial de Chat
        if telefono_cliente not in chat_sessions:
            
            # Definir Contexto según el ROL
            if es_vendedor:
                # CONTEXTO ASISTENTE INTERNO
                CONTEXTO = """
                Eres InnovaBot, el asistente interno exclusivo para el equipo de ventas de Innova Mobili.
                Tu rol es dar información precisa, técnica y confidencial solo a los vendedores.
                Datos confidenciales: BCP Cuenta Corriente: 194-2550181-0-51, a nombre de Innova Mobili SAC.
                """
                mensaje_inicial = "Entendido. Iniciando sesión como asistente interno."
            else:
                # CONTEXTO CLIENTE FINAL
                CONTEXTO = """
                Eres InnovaBot, experto en muebles de Innova Mobili.
                Sé breve, amable y persuade a la venta.
                """
                mensaje_inicial = "Entendido, soy InnovaBot."
                
            chat_sessions[telefono_cliente] = model.start_chat(history=[
                {"role": "user", "parts": CONTEXTO},
                {"role": "model", "parts": mensaje_inicial}
            ])
        
        chat = chat_sessions[telefono_cliente]
        
        # 2. Preguntar a Gemini
        response = chat.send_message(texto_usuario)
        respuesta_bot = response.text

        # 3. Enviar a WhatsApp
        url = f"https://graph.facebook.com/v21.0/{PHONE_NUMBER_ID}/messages"
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
            print(f" Mensaje enviado a {telefono_cliente}")
        else:
            print(f" ERROR WHATSAPP: {envio.status_code} - {envio.text}")

    except Exception as e:
        print(f" Error en la lógica del bot: {e}")


@app.get("/webhook")
async def verify_webhook(mode: str = Query(alias="hub.mode"),
                         token: str = Query(alias="hub.verify_token"),
                         challenge: str = Query(alias="hub.challenge")):
    if mode == "subscribe" and token == VERIFY_TOKEN:
        # Asegúrate de que el token recibido coincida con el token de verificación
        return int(challenge)
    raise HTTPException(status_code=403, detail="Token incorrecto")

@app.post("/webhook")
async def whatsapp_webhook(request: Request, background_tasks: BackgroundTasks):
    # El resto de la función POST queda igual, ya que maneja la lógica de Meta.
    try:
        data = await request.json()
        
        entry = data["entry"][0]
        changes = entry["changes"][0]
        value = changes["value"]
        
        if "messages" in value:
            message_data = value["messages"][0]
            telefono_cliente = message_data["from"]
            texto_usuario = message_data["text"]["body"]
 
            profile = value.get("contacts", [{}])[0].get("profile", {})
            nombre_cliente = profile.get("name", "Cliente")

            print(f"Recibido de {nombre_cliente}: {texto_usuario}")

            background_tasks.add_task(procesar_mensaje, telefono_cliente, nombre_cliente, texto_usuario)
            
        return {"status": "received"}

    except Exception as e:
        # Esto ignora otros eventos que no son mensajes, como lecturas o estados.
        return {"status": "ignored"}

if __name__ == "__main__":
    # Render usará el puerto 10000. Esto es solo para pruebas locales.
    uvicorn.run(app, host="0.0.0.0", port=8001)