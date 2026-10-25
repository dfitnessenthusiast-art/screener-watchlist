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
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            # Fallback to standalone if consolidated returns 404
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

        # Helper function to clean numbers
        def clean_num(text):
            try:
                cleaned = text.replace(',', '').replace('₹', '').strip()
                return float(cleaned)
            except:
                return 0.0

        # Parse Top Ratios list on Screener.in
        # Screener stores key metrics in ul#top-ratios li or similar structure
        ratios_list = soup.find_all('li', {'id': True}) or soup.select('ul.top-ratios li')
        for li in ratios_list:
            name_span = li.find('span', class_='name')
            value_span = li.find('span', class_='number')
            if name_span and value_span:
                label = name_span.text.strip().lower()
                val = clean_num(value_span.text)
                
                if 'market capitalization' in label or 'market cap' in label:
                    data['marketCap'] = val
                elif label == 'stock p/e' or label == 'p/e':
                    data['pe'] = val
                elif label == 'roce':
                    data['roce'] = val
                elif label == 'roe':
                    data['roe'] = val
                elif 'current price' in label or label == 'price':
                    data['price'] = val
                elif 'book value' in label:
                    data['bookValue'] = val
                elif 'high / low' in label:
                    # Often formatted like "667 / 341"
                    parts = value_span.text.split('/')
                    if len(parts) == 2:
                        data['high52'] = clean_num(parts[0])
                        data['low52'] = clean_num(parts[1])

        # Fallback check for current price if not caught in ratios
        if data['price'] == 0.0:
            price_elem = soup.find('span', {'class': 'number'})
            if price_elem:
                data['price'] = clean_num(price_elem.text)

        print(f"Successfully scraped {symbol}: Price={data['price']}, P/E={data['pe']}, ROCE={data['roce']}")
        return data

    except Exception as e:
        print(f"Error scraping {symbol}: {e}")
        return None

def main():
    all_stocks = {}
    success_count = 0

    for symbol in TICKERS:
        print(f"Scraping {symbol}...")
        stock_data = fetch_screener_data(symbol)
        if stock_data and stock_data['price'] > 0:
            all_stocks[symbol] = stock_data
            success_count += 1
        else:
            # Keep fallback dummy/previous structure if scrape fails temporarily
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
    
    print(f"Sync complete. Updated {success_count}/{len(TICKERS)} stocks in screener_data.json")

if __name__ == "__main__":
    main()
