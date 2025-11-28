from fastapi import FastAPI, Request, HTTPException, Query, BackgroundTasks
import google.generativeai as genai
import uvicorn
import requests
import json

app = FastAPI()

# --- ACTUALIZA ESTO CON TUS NUEVAS CLAVES ---
GEMINI_API_KEY = "AIzaSyAWKASnFPc_6e2mdEqRa6Uu8wkawbCXNmI" 
#WHATSAPP_TOKEN = "EAAXeWdWIwHIBQJg4QvYegjAs0g5DArspJMZBW2yjwa2NNhTfEhy25GCHIB35cpZBSsZAR5ySYZC3LDVdYbBWZAmghPMNVZAXZCrh2kexXlU4RmzNZCZC9plSKZAr1MZBgYqsHZCzc99CUPkclwHePnJvZA9U0V4dl0TfZCLxoNsMWcDd7cp1bMogLhP7iWID6oUuf2cl9TdAZDZD" 
WHATSAPP_TOKEN = "EAAXeWdWIwHIBQKgu9WhWZAjeELKlPQQnqCkn7TlZCVCXADmZBA8X1zMZB3AMMBlIPFWusUsYIXCRq0txiVGZBhafgCnAZBYGPhr0ZCCz8a6LAQZCgZBZBQBBKihKtQsPPZBGzu5w93Ul5vZAlGGvbAZBgfZCEtzRwXGQ3WNrcoL7qpdeZB29UvQ9Q7vVSG7wqPZCiZCZBPObZBn8G9SiB030MACEnC2pIsPZB0HS5wyIT9MG1bTSMetjArZBaHJMes7npIkmE7KvkAjv6xYyEm9mTCDJ28ZBLbNzqLIfM35QXxrD1DupUT0AZDZD" 
PHONE_NUMBER_ID = "911239725403166" # Este se ve correcto en tu captura
VERIFY_TOKEN = "Guarana1z"

# --- CONFIGURACIÓN GEMINI ---
genai.configure(api_key=GEMINI_API_KEY)
# Usamos el modelo flash que es más rápido para chat
model = genai.GenerativeModel('gemini-2.5-flash')

# Variables globales
chat_sessions = {}
telefonos_vendedores = ["51937065891", "51902266061"] 

# --- FUNCIÓN DE PROCESAMIENTO (SE EJECUTA EN 2DO PLANO) ---
def procesar_mensaje(telefono_cliente, nombre_cliente, texto_usuario):
    print(f"🤖 Procesando mensaje para {nombre_cliente}...")
    
    try:
        # 1. Historial de Chat
        if telefono_cliente not in chat_sessions:
            CONTEXTO = """
            Eres InnovaBot, experto en muebles de Innova Mobili.
            Sé breve, amable y persuade a la venta.
            """
            chat_sessions[telefono_cliente] = model.start_chat(history=[
                {"role": "user", "parts": CONTEXTO},
                {"role": "model", "parts": "Entendido, soy InnovaBot."}
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
        return int(challenge)
    raise HTTPException(status_code=403, detail="Token incorrecto")

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
            texto_usuario = message_data["text"]["body"]
  
            profile = value.get("contacts", [{}])[0].get("profile", {})
            nombre_cliente = profile.get("name", "Cliente")

            print(f"Recibido de {nombre_cliente}: {texto_usuario}")

   
            background_tasks.add_task(procesar_mensaje, telefono_cliente, nombre_cliente, texto_usuario)
            
        return {"status": "received"}

    except Exception as e:

        return {"status": "ignored"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)