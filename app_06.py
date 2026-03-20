import requests
from bs4 import BeautifulSoup
import time
import pandas as pd
import sqlite3

def fetch_page():
    url = 'https://www.mercadolivre.com.br/apple-iphone-16-256-gb-preto-distribuidor-autorizado/p/MLB1040287796#polycard_client=search-desktop&search_layout=grid&position=2&type=product&tracking_id=962e90aa-c7f9-48ad-9a0a-4cfab0e325a5&wid=MLB3931272075&sid=search'

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    response = requests.get(url, headers=headers)
    return response.text

def parse_page(html): 
    soup = BeautifulSoup(html, 'html.parser')
    product_name = soup.find('h1', class_= "ui-pdp-title").get_text()
    prices: list = soup.find_all('span', class_="andes-money-amount__fraction")
    old_price: int = int(prices[0].get_text().replace('.', ''))
    new_price: int = int(prices[1].get_text().replace('.', ''))
    installment_prices: int = int(prices[2].get_text().replace('.', ''))

    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

    return{
        'product_name': product_name,
        'old_price' : old_price,
        'new_price': new_price,
        'installment_prices': installment_prices,
        'timestamp': timestamp
    }

def create_connection(db_name='data_base.db'):
    conn = sqlite3.connect(db_name)
    return conn

def setup_database(conn):
 cursor = conn.cursor()
 cursor.execute('''
        CREATE TABLE IF NOT EXISTS prices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_name TEXT,
            old_price INTEGER,
            new_price INTEGER,
            installment_prices INTEGER,
            timestamp TEXT
                   
    )
 ''')
 conn.commit()

def save_to_database(conn, data):
    df = pd.DataFrame([data])
    df.to_sql('prices', conn, if_exists='append', index=False)

def get_max_price(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT MAX(new_price), timestamp FROM prices")

    result = cursor.fetchone()

    if result and result[0] is not None:
        return result[0], result[1]
    return None, None

if __name__ == "__main__":

    conn = create_connection()
    setup_database(conn)

    while True:
        page_content = fetch_page()
        produto_info = parse_page(page_content)
        current_price = produto_info["new_price"]
        
        max_price, max_price_timestamp = get_max_price(conn)

        if max_price is None or current_price > max_price:
            print("Preço maior detectado")
            max_price = current_price
            max_price_timestamp = produto_info['timestamp']
        else:
            print(f"O maior preço registrado é {max_price} em {max_price_timestamp}")

        save_to_database(conn, produto_info)
        print("Dados salvos no banco:",produto_info)
        time.sleep(10)

    
    conn.close()