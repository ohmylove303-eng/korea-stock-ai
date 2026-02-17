import requests
from bs4 import BeautifulSoup
import pandas as pd

def verify_naver_scrape():
    print("=== Fallback Verification: Naver Finance Scraping ===")
    code = "005930" # Samsung Electronics
    url = f"https://finance.naver.com/item/frgn.naver?code={code}"
    
    print(f"Target: {code}")
    print(f"Source: {url}")
    
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    try:
        resp = requests.get(url, headers=headers)
        soup = BeautifulSoup(resp.content, "html.parser")
        
        # Select table with class 'type2' (usually investor data)
        # Naver pages often have multiple type2 tables. 
        # The one with Date, Foreigner, Institution is usually the 2nd or has specific attributes.
        
        tables = soup.select('table.type2')
        
        found_data = False
        
        for idx, table in enumerate(tables):
            # Check headers to confirm it's the right table
            headers_text = [th.get_text().strip() for th in table.select('th')]
            if '날짜' in headers_text and '기관' in headers_text and '외국인' in headers_text:
                print(f"\n✅ Found Investor Table (Index {idx})")
                
                rows = table.select('tr')
                data = []
                for row in rows:
                    cols = row.select('td')
                    if len(cols) < 5: continue # Skip dividers
                    
                    try:
                        date_str = cols[0].get_text().strip()
                        # Foreigner Net Buy is usually column 6 or so.
                        # Detailed inspection:
                        # 0: Date
                        # 1: Close
                        # 2: Change
                        # 3: Change Rate
                        # 4: Volume
                        # 5: Institution Net Buy
                        # 6: Foreigner Net Buy
                        # 7: Foreigner Holdings
                        # 8: Holding Rate
                        
                        inst_net = cols[5].get_text().strip()
                        foreign_net = cols[6].get_text().strip()
                        
                        data.append({
                            "Date": date_str,
                            "ForeignNet": foreign_net,
                            "InstNet": inst_net
                        })
                    except:
                        continue
                        
                if data:
                    print("\n📊 Recent Investor Supply Flow (Last 5 days):")
                    for item in data[:5]:
                        print(f"   [{item['Date']}] Foreign: {item['ForeignNet']}, Inst: {item['InstNet']}")
                    found_data = True
                    break
        
        if not found_data:
            print("❌ Could not parse Naver Finance table structure.")
            
    except Exception as e:
        print(f"❌ Error scraping Naver: {e}")

if __name__ == "__main__":
    verify_naver_scrape()
