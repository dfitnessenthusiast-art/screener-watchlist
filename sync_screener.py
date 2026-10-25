import json
import requests
from bs4 import BeautifulSoup
import datetime
import csv
import io

# List of your 31 tracked stock ticker symbols on Screener.in
TICKERS = [
    "BALUFORGE", "DATAPATTNS", "BEL", "MAZDOCK", "COCHINSHIP", 
    "ULTRACEMCO", "APOLLOHOSP", "TCS", "INFY", "ITC", 
    "RELIANCE", "HDFCBANK", "ICICIBANK", "AXISBANK", "KOTAKBANK",
    "LT", "TITAN", "ASIANPAINT", "HINDUNILVR", "SUNPHARMA",
    "BAJFINANCE", "MARUTI", "NESTLEIND", "TATAMOTORS", "TATASTEEL",
    "NTPC", "POWERGRID", "ONGC", "COALINDIA", "SBIN", "BHARTIARTL"
]

def generate_search_index():
    """Fetches the official NSE active equities list for the frontend live search dropdown."""
    print("Generating master search index from NSE...")
    stocks = []
    
    url = "https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)',
        'Accept': 'text/csv'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        csv_data = csv.DictReader(io.StringIO(response.text))
        for row in csv_data:
            sym = row.get('SYMBOL', '').strip()
            name = row.get('NAME OF COMPANY', '').strip()
            if sym and name:
                stocks.append({"sym": sym, "name": name})
                
        with open("search_index.json", "w", encoding="utf-8") as f:
            json.dump(stocks, f, ensure_ascii=False, separators=(',', ':'))
            
        print(f"Successfully saved {len(stocks)} stocks to search_index.json")
        
    except Exception as e:
        print(f"Failed to fetch NSE master list: {e}")
        # Ensure file always exists so frontend doesn't error
        fallback = [{"sym": "BLS", "name": "BLS International Services Ltd"}, {"sym": "RELIANCE", "name": "Reliance Industries Ltd"}]
        with open("search_index.json", "w") as f:
            json.dump(fallback, f)

def fetch_screener_data(symbol):
    """Scrapes financial metrics directly from Screener.in"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }
    
    # Use requests Session to automatically handle redirects (fixes TATAMOTORS / DATAPATTNS)
    session = requests.Session()
    session.headers.update(headers)
    
    # Try consolidated first, then standalone
    urls_to_try = [
        f"https://www.screener.in/company/{symbol}/consolidated/",
        f"https://www.screener.in/company/{symbol}/"
    ]
    
    response = None
    for url in urls_to_try:
        try:
            temp_res = session.get(url, timeout=10, allow_redirects=True)
            if temp_res.status_code == 200:
                response = temp_res
                break
        except requests.exceptions.RequestException:
            continue
            
    if not response or response.status_code != 200:
        print(f"Failed to fetch {symbol}")
        return None

    soup = BeautifulSoup(response.text, 'html.parser')
    
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
            cleaned = text.replace(',', '').replace('₹', '').replace('%', '').strip()
            return float(cleaned)
        except:
            return 0.0

    # 1. Parse Top Ratios Ribbon
    ratios_list = soup.select('ul#top-ratios li')
    for li in ratios_list:
        name_elem = li.find('span', class_='name')
        if not name_elem: continue
        label = name_elem.text.strip().lower()
        
        # High / Low fix: Find ALL spans with class 'number' inside this list item
        if 'high / low' in label:
            num_spans = li.find_all('span', class_='number')
            if len(num_spans) >= 2:
                data['high52'] = clean_num(num_spans[0].text)
                data['low52'] = clean_num(num_spans[1].text)
            continue
            
        val_elem = li.find('span', class_='number')
        if not val_elem: continue
        val = clean_num(val_elem.text)

        if 'market cap' in label:
            data['marketCap'] = val
        elif 'stock p/e' in label or label == 'p/e':
            data['pe'] = val
        elif 'roce' in label:
            data['roce'] = val
        elif 'roe' in label:
            data['roe'] = val
        elif 'current price' in label:
            data['price'] = val
        elif 'book value' in label:
            data['bookValue'] = val

    # 2. Parse Sector (Usually in the breadcrumbs or tags)
    sector_links = soup.select('.company-links a')
    for link in sector_links:
        if 'sector' in link.get('href', '').lower():
            data['sector'] = link.text.strip()
            break

    # 3. Parse Latest OPM from the Quarters Table
    quarters_table = soup.select_one('section#quarters table')
    if quarters_table:
        rows = quarters_table.find_all('tr')
        for row in rows:
            header = row.find('td', class_='text')
            if header and 'OPM %' in header.text:
                cols = row.find_all('td')
                if len(cols) > 1:
                    # Grab the very last column's value (latest quarter)
                    data['opm'] = clean_num(cols[-1].text)
                break

    print(f"Parsed {symbol}: Price={data['price']}, H/L={data['high52']}/{data['low52']}, OPM={data['opm']}%")
    return data

def main():
    # 1. First, build the master search index for the frontend
    generate_search_index()
    
    # 2. Then, scrape the live metrics for the 31 tracked stocks
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
                "price": 0.0, "pe": 0.0, "roce": 0.0, "roe": 0.0,
                "marketCap": 0.0, "bookValue": 0.0, "high52": 0.0, "low52": 0.0, "opm": 0.0
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
