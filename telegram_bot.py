import requests
import os

def enviar_mensagem_telegram(mensagem):
    """Envia mensagem para o bot do Telegram"""
    token = os.environ.get('TELEGRAM_BOT_TOKEN')
    chat_id = os.environ.get('TELEGRAM_CHAT_ID')
    
    if not token or not chat_id:
        print("Token ou Chat ID do Telegram não configurados")
        return False
    
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    dados = {
        'chat_id': chat_id,
        'text': mensagem,
        'parse_mode': 'HTML'
    }
    
    try:
        response = requests.post(url, data=dados)
        return response.json().get('ok', False)
    except Exception as e:
        print(f"Erro ao enviar mensagem: {e}")
        return False
