import requests
from bs4 import BeautifulSoup
import json
import re
import time
from datetime import datetime
import os

DEFAULT_TICKERS = [
    {"symbol": "BALUFORGE", "name": "Balu Forge Industries", "sector": "Capital Goods / Engineering", "note": ""},
    {"symbol": "ACE", "name": "Action Construction Equipment", "sector": "Capital Goods / Engineering", "note": ""},
    {"symbol": "AIAENG", "name": "AIA Engineering", "sector": "Capital Goods / Engineering", "note": ""},
    {"symbol": "ENGINERSIN", "name": "Engineers India", "sector": "Capital Goods / Engineering", "note": ""},
    {"symbol": "ENVIRONS", "name": "Enviro Infra Engineers", "sector": "Infrastructure", "note": ""},
    {"symbol": "CRIZAC", "name": "Crizac Ltd", "sector": "EdTech & Services", "note": "Wait"},
    {"symbol": "JEENA", "name": "Jeena Sikho Lifecare", "sector": "Healthcare & Wellness", "note": ""},
    {"symbol": "ONEGLOBAL", "name": "One Global Service Provider", "sector": "Technology / IT", "note": ""},
    {"symbol": "GPPL", "name": "Gujarat Pipavav Port", "sector": "Logistics & Ports", "note": ""},
    {"symbol": "MCX", "name": "Multi Commodity Exchange", "sector": "Financial Exchanges", "note": "Wait"},
    {"symbol": "ASHOKA", "name": "Ashoka Buildcon", "sector": "Infrastructure / EPC", "note": ""},
    {"symbol": "KNRCON", "name": "KNR Constructions", "sector": "Infrastructure / EPC", "note": ""},
    {"symbol": "SIGMASOLVE", "name": "Sigma Solve", "sector": "Technology / IT", "note": ""},
    {"symbol": "COALINDIA", "name": "Coal India (CMPDI)", "sector": "Mining & Natural Resources", "note": ""},
    {"symbol": "CANARAROB", "name": "Canara Robeco AMC", "sector": "Asset Management", "note": ""},
    {"symbol": "LUPIN", "name": "Lupin Ltd", "sector": "Pharmaceuticals", "note": ""},
    {"symbol": "SYNCOMF", "name": "Syncom Formulations", "sector": "Pharmaceuticals", "note": ""},
    {"symbol": "CAPLIPOINT", "name": "Caplin Point Laboratories", "sector": "Pharmaceuticals", "note": ""},
    {"symbol": "ADVENZYMES", "name": "Advanced Enzyme Tech", "sector": "Specialty Chemicals / Pharma", "note": ""},
    {"symbol": "MUTHOOTFIN", "name": "Muthoot Finance", "sector": "Financials / NBFC", "note": ""},
    {"symbol": "MAYURUNIQ", "name": "Mayur Uniquoters", "sector": "Auto Ancillary / Polymers", "note": ""},
    {"symbol": "VOLTAMP", "name": "Voltamp Transformers", "sector": "Electrical Equipment", "note": "Wait"},
    {"symbol": "VIPULLTD", "name": "Vipul Ltd", "sector": "Real Estate", "note": "Research This"},
    {"symbol": "PFIZER", "name": "Pfizer Ltd", "sector": "Pharmaceuticals", "note": ""},
    {"symbol": "KAMDHENU", "name": "Kamdhenu Ltd", "sector": "Building Materials / Steel", "note": "Wait"},
    {"symbol": "SUZLON", "name": "Suzlon Energy", "sector": "Renewable Energy", "note": ""},
    {"symbol": "WAAREEENER", "name": "Waaree Energies", "sector": "Renewable Energy", "note": ""},
    {"symbol": "DAMCAPITAL", "name": "DAM Capital Advisors", "sector": "Financials / Advisory", "note": ""},
    {"symbol": "KOVAI", "name": "Kovai Medical Center", "sector": "Healthcare / Hospitals", "note": ""},
    {"symbol": "BORORENEW", "name": "Borosil Renewables", "sector": "Solar Glass / Green Energy", "note": ""},
    {"symbol": "ARROWGREEN", "name": "Arrow Greentech", "sector": "Specialty Packaging", "note": "Review"}
]

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
}

def clean_num(text):
    if not text:
        return None
    val = re.sub(r'[^\d.-]', '', text.replace(',', ''))
    try:
        return float(val) if '.' in val else int(val)
    except ValueError:
        return None

def fetch_single_ticker(sym, existing_record=None):
    url = f"https://www.screener.in/company/{sym}/consolidated/"
    record = existing_record or {
        "symbol": sym,
        "name": sym,
        "sector": "Equity",
        "note": "",
        "price": None, "pe": None, "roce": None, "roe": None,
        "marketCap": None, "bookValue": None, "high52": None, "low52": None, "opm": None,
        "status": "success"
    }
    try:
        resp = requests.get(url, headers=HEADERS, timeout=12)
        if resp.status_code == 404:
            url_std = f"https://www.screener.in/company/{sym}/"
            resp = requests.get(url_std, headers=HEADERS, timeout=12)

        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'html.parser')
            h1 = soup.find('h1')
            if h1 and (record.get("name") == sym or not record.get("name")):
                record["name"] = h1.text.strip()

            ratios = {}
            for li in soup.select('ul#top-ratios li'):
                name_span = li.find('span', class_='name')
                val_span = li.find('span', class_='nowrap value') or li.find('span', class_='value')
                if name_span and val_span:
                    key = name_span.text.strip()
                    ratios[key] = clean_num(val_span.text.strip())

            record["price"] = ratios.get("Current Price")
            record["pe"] = ratios.get("Stock P/E")
            record["roce"] = ratios.get("ROCE")
            record["roe"] = ratios.get("ROE")
            record["marketCap"] = ratios.get("Market Cap")
            record["bookValue"] = ratios.get("Book Value")
            
            high_low = soup.find('span', text=re.compile(r'High\s*/\s*Low', re.I))
            if high_low and high_low.parent:
                nums = re.findall(r'[\d,.]+', high_low.parent.text)
                if len(nums) >= 2:
                    record["high52"] = clean_num(nums[0])
                    record["low52"] = clean_num(nums[1])

            print(f"✓ {sym}: Price={record['price']}, PE={record['pe']}, ROCE={record['roce']}%")
            record["status"] = "success"
        else:
            print(f"⚠ {sym}: HTTP {resp.status_code}")
            record["status"] = f"HTTP {resp.status_code}"
    except Exception as e:
        print(f"✗ {sym}: Error {e}")
        record["status"] = str(e)
    return record

def main():
    current_stocks = {}
    if os.path.exists("screener_data.json"):
        try:
            with open("screener_data.json", "r", encoding="utf-8") as f:
                prev_data = json.load(f)
                current_stocks = prev_data.get("stocks", {})
        except Exception:
            current_stocks = {}

    if not current_stocks:
        for item in DEFAULT_TICKERS:
            current_stocks[item["symbol"]] = {
                "symbol": item["symbol"],
                "name": item["name"],
                "sector": item["sector"],
                "note": item["note"],
                "price": None, "pe": None, "roce": None, "roe": None,
                "marketCap": None, "bookValue": None, "high52": None, "low52": None, "opm": None,
                "status": "pending"
            }

    updated_stocks = {}
    print(f"Running automated sync for {len(current_stocks)} stocks...")
    for sym, item in current_stocks.items():
        updated_stocks[sym] = fetch_single_ticker(sym, item)
        time.sleep(1.2)

    payload = {
        "lastUpdated": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
        "total": len(updated_stocks),
        "stocks": updated_stocks
    }

    with open("screener_data.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    print("Done! Updated screener_data.json")

if __name__ == "__main__":
    main()
