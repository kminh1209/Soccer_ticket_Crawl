import time
import random
import os
import pandas as pd
import re
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup

def crawl_laliga_github_actions():
    # 1. 브라우저 설정 (GitHub Actions 맞춤형)
    chrome_options = Options()
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--headless=new") # 화면 없이 실행 (필수)
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])

    # 💡 GitHub Actions 환경에 맞춰 webdriver_manager 없이 기본 Service 사용
    service = Service()
    driver = webdriver.Chrome(service=service, options=chrome_options)

    all_results = [] # 모든 라운드의 데이터를 담을 리스트

    try:
        # 2. 1라운드부터 38라운드까지 반복
        for gameweek in range(1, 39): 
            # URL 동적 생성 (f-string 사용)
            url = f"https://www.laliga.com/en-ES/laliga-easports/results/2025-26/gameweek-{gameweek}"
            
            print(f"\n▶️ [Gameweek {gameweek}/38] 이동 중: {url}")
            driver.get(url)

            # 3. 로딩 대기 (사람처럼 보이기 위해 랜덤 딜레이 적용)
            wait_time = random.uniform(3, 5) 
            time.sleep(wait_time)

            soup = BeautifulSoup(driver.page_source, 'html.parser')
            rows = soup.select('tbody tr')
            
            if not rows:
                print(f"   ⚠️ 데이터 없음 (아직 경기가 없거나 로딩 실패)")
                continue

            count = 0
            for row in rows:
                try:
                    # --- 날짜 & 시간 ---
                    date_cell = row.find('td', attrs={'type': 'date'})
                    if not date_cell: continue
                    match_date = date_cell.get_text(strip=True)

                    time_cell = row.find('td', attrs={'type': 'time'})
                    match_time = time_cell.get_text(strip=True) if time_cell else "N/A"

                    # --- 팀명 & 점수 ---
                    match_cell = row.find('td', class_=lambda x: x and 'TableCellMatch' in x)
                    
                    if match_cell:
                        full_text = match_cell.get_text(" ", strip=True)
                        # 공백이 섞인 점수 포맷 대응 (예: "1 - 3")
                        pattern = r'(.*?)\s+(\d+\s*-\s*\d+)\s+(.*)'
                        found = re.search(pattern, full_text)

                        if found:
                            home_team = found.group(1).strip()
                            score = found.group(2).strip()
                            away_team = found.group(3).strip()
                        else:
                            # 점수가 아직 없는 경우 (경기 예정)
                            home_team = full_text
                            score = "Match Pending" 
                            away_team = "Match Pending" 
                    else:
                        continue

                    # --- 결과 저장 (Gameweek 정보 추가) ---
                    all_results.append({
                        "Gameweek": f"GW{gameweek}",  # 통일성을 위해 GW1 형식으로 변경
                        "Date": match_date,
                        "Time": match_time,
                        "Home Team": home_team,
                        "Away Team": away_team,
                        "Result": score
                    })
                    count += 1

                except Exception as e:
                    continue
            
            print(f"   ✅ {count}개 경기 추출 완료")

    except Exception as e:
        print(f"❌ 에러 발생: {e}")

    finally:
        driver.quit()

        # 4. 💡 [핵심 변경] 전체 데이터를 result_csv 폴더에 CSV로 저장
        if all_results:
            df = pd.DataFrame(all_results)
            
            save_folder = "result_csv"
            if not os.path.exists(save_folder):
                os.makedirs(save_folder)
                
            file_path = os.path.join(save_folder, "laliga_full_season_results.csv")
            df.to_csv(file_path, index=False, encoding='utf-8-sig')
            
            print("-" * 40)
            print(f"🎉 전체 크롤링 완료! 총 {len(df)}개의 라리가 데이터가 저장되었습니다.")
            print(f"📂 파일명: {file_path}")
            print(df.head())
        else:
            print("저장할 데이터가 없습니다.")

if __name__ == "__main__":
    crawl_laliga_github_actions()