import requests
import os

def enviar_mensagem_telegram(mensagem):
    """Envia mensagem para o bot do Telegram"""
    token = os.environ.get('TELEGRAM_BOT_TOKEN')
    chat_id = os.environ.get('TELEGRAM_CHAT_ID')
    
    print(f"Token configurado: {'Sim' if token else 'Não'}")
    print(f"Chat ID configurado: {'Sim' if chat_id else 'Não'}")
    
    if not token or not chat_id:
        print("⚠️ Token ou Chat ID do Telegram não configurados")
        return False
    
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    dados = {
        'chat_id': chat_id,
        'text': mensagem,
        'parse_mode': 'HTML'
    }
    
    try:
        print(f"Enviando mensagem para o Telegram...")
        response = requests.post(url, data=dados)
        resultado = response.json()
        print(f"Resposta do Telegram: {resultado}")
        
        if resultado.get('ok'):
            print("✅ Mensagem enviada com sucesso!")
            return True
        else:
            print(f"❌ Erro do Telegram: {resultado.get('description')}")
            return False
    except Exception as e:
        print(f"❌ Erro ao enviar mensagem: {e}")
        return False
