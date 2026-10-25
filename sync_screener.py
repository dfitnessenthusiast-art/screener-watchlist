import json
import requests
from bs4 import BeautifulSoup
import datetime

# List of your 31 tracked stock ticker symbols on Screener.in
TICKERS = [
    "BALUFORGE", "DATAPATTNS", "BEL", "MAZDOCK", "COCHINSHIP", 
    "ULTRACEMCO", "APOLLOHOSP", "TCS", "INFY", "ITC", 
    "RELIANCE", "HDFCBANK", "ICICIBANK", "AXISBANK", "KOTAKBANK",
    "LT", "TITAN", "ASIANPAINT", "HINDUNILVR", "SUNPHARMA",
    "BAJFINANCE", "MARUTI", "NESTLEIND", "TATAMOTORS", "TATASTEEL",
    "NTPC", "POWERGRID", "ONGC", "COALINDIA", "SBIN", "BHARTIARTL"
]

def fetch_screener_data(symbol):
    url = f"https://www.screener.in/company/{symbol}/consolidated/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            url = f"https://www.screener.in/company/{symbol}/"
            response = requests.get(url, headers=headers, timeout=10)
            
        if response.status_code != 200:
            print(f"Failed to fetch {symbol}: HTTP {response.status_code}")
            return None

        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract Company Name
        name_elem = soup.find('h1', class_='margin-0')
        company_name = name_elem.text.strip() if name_elem else symbol

        data = {
            "symbol": symbol,
            "name": company_name,
            "sector": "",
            "note": "",
            "price": 0.0,
            "pe": 0.0,
            "roce": 0.0,
            "roe": 0.0,
            "marketCap": 0.0,
            "bookValue": 0.0,
            "high52": 0.0,
            "low52": 0.0,
            "opm": 0.0
        }

        def clean_num(text):
            try:
                cleaned = text.replace(',', '').replace('₹', '').strip()
                return float(cleaned)
            except:
                return 0.0

        # Parse ratios from the top-ratios list items and flex cards
        ratios_list = soup.select('ul#top-ratios li, div.company-ratios li, .flex-row li')
        for li in ratios_list:
            name_elem = li.find('span', class_='name')
            val_elem = li.find('span', class_='number')
            if not name_elem or not val_elem:
                # alternative structure check
                spans = li.find_all('span')
                if len(spans) >= 2:
                    label = spans[0].text.strip().lower()
                    val = clean_num(spans[1].text)
                else:
                    continue
            else:
                label = name_elem.text.strip().lower()
                val = clean_num(val_elem.text)

            if 'market capitalization' in label or 'market cap' in label:
                data['marketCap'] = val
            elif 'stock p/e' in label or label == 'p/e':
                data['pe'] = val
            elif 'roce' in label:
                data['roce'] = val
            elif 'roe' in label:
                data['roe'] = val
            elif 'current price' in label or label == 'price':
                data['price'] = val
            elif 'book value' in label:
                data['bookValue'] = val
            elif 'high / low' in label:
                parts = val_elem.text.split('/')
                if len(parts) == 2:
                    data['high52'] = clean_num(parts[0])
                    data['low52'] = clean_num(parts[1])

        # Fallback price search if 0
        if data['price'] == 0.0:
            price_box = soup.select_one('.current-price .number, b.number')
            if price_box:
                data['price'] = clean_num(price_box.text)

        print(f"Parsed {symbol}: Price={data['price']}, P/E={data['pe']}, ROCE={data['roce']}")
        return data

    except Exception as e:
        print(f"Error scraping {symbol}: {e}")
        return None

def main():
    all_stocks = {}
    success_count = 0

    for symbol in TICKERS:
        stock_data = fetch_screener_data(symbol)
        if stock_data and stock_data['price'] > 0:
            all_stocks[symbol] = stock_data
            success_count += 1
        else:
            all_stocks[symbol] = {
                "symbol": symbol,
                "name": symbol,
                "sector": "Equities",
                "note": "Live fetch pending",
                "price": 0.0,
                "pe": 0.0,
                "roce": 0.0,
                "roe": 0.0,
                "marketCap": 0.0,
                "bookValue": 0.0,
                "high52": 0.0,
                "low52": 0.0,
                "opm": 0.0
            }

    output = {
        "lastUpdated": datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
        "total": len(TICKERS),
        "stocks": all_stocks
    }

    with open("screener_data.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)
    
    print(f"Sync complete. Updated {success_count}/{len(TICKERS)} stocks.")

if __name__ == "__main__":
    main()
