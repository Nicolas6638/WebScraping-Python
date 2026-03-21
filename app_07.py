import requests
from bs4 import BeautifulSoup
import time
import sqlite3
import pandas as pd
import asyncio
from telegram import Bot
import os
from dotenv import load_dotenv

load_dotenv()

# Configurações do bot do Telegram
TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
bot = Bot(token=TOKEN)

def fetch_page():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    url = 'https://www.mercadolivre.com.br/apple-iphone-16-256-gb-preto-distribuidor-autorizado/p/MLB1040287796#polycard_client=search-desktop&search_layout=grid&position=2&type=product&tracking_id=eacbc4cd-5e30-4551-a8fd-fb70eacf8f93&wid=MLB3931272075&sid=search'
    response = requests.get(url, headers=headers)
    return response.text

def parse_page(html):
    soup = BeautifulSoup(html, 'html.parser')
    product_name = soup.find('h1', class_='ui-pdp-title').get_text(strip=True)
    prices = soup.find_all('span', class_='andes-money-amount__fraction')
    old_price = int(prices[0].get_text(strip=True).replace('.', ''))
    new_price = int(prices[1].get_text(strip=True).replace('.', ''))
    installment_price = int(prices[2].get_text(strip=True).replace('.', ''))

    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')

    return {
        'product_name': product_name,
        'old_price': old_price,
        'new_price': new_price,
        'installment_price': installment_price,
        'timestamp': timestamp
    }

def create_connection(db_name='data_base.db'):
    """Cria uma conexão com o banco de dados SQLite."""
    conn = sqlite3.connect(db_name)
    return conn

def setup_database(conn):
    """Cria a tabela de preços se ela não existir."""
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS prices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_name TEXT,
            old_price INTEGER,
            new_price INTEGER,
            installment_price INTEGER,
            timestamp TEXT
        )
    ''')
    conn.commit()

def save_to_database(conn, data):
    """Salva uma linha de dados no banco de dados SQLite usando pandas."""
    df = pd.DataFrame([data])  # Converte o dicionário em um DataFrame de uma linha
    df.to_sql('prices', conn, if_exists='append', index=False)  # Salva no banco de dados

def get_max_price(conn):
    """Consulta o maior preço registrado até o momento."""
    cursor = conn.cursor()
    cursor.execute("SELECT MAX(new_price), timestamp FROM prices")
    result = cursor.fetchone()
    if result and result[0] is not None:
        return result[0], result[1]
    return None, None

async def send_telegram_message(text):
    """Envia uma mensagem para o Telegram."""
    await bot.send_message(chat_id=CHAT_ID, text=text)

async def main():
    conn = create_connection()
    setup_database(conn)

    try:
        while True:
            # Faz a requisição e parseia a página
            page_content = fetch_page()
            product_info = parse_page(page_content)
            current_price = product_info['new_price']
            
            # Obtém o maior preço já salvo
            max_price, max_price_timestamp = get_max_price(conn)
            
            # Comparação de preços
            if max_price is None or current_price > max_price:
                message = f"Novo preço maior detectado: {current_price}"
                print(message)
                await send_telegram_message(message)
                max_price = current_price
                max_price_timestamp = product_info['timestamp']
            else:
                message = f"O maior preço registrado é {max_price} em {max_price_timestamp}"
                print(message)
                await send_telegram_message(message)

            # Salva os dados no banco de dados SQLite
            save_to_database(conn, product_info)
            print("Dados salvos no banco:", product_info)
            
            # Aguarda 10 segundos antes da próxima execução
            await asyncio.sleep(10)

    except KeyboardInterrupt:
        print("Parando a execução...")
    finally:
        conn.close()

# Executa o loop assíncrono
asyncio.run(main())