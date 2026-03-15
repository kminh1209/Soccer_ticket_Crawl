import time
import re
import os
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def crawl_bundesliga_github_actions():
    # 1. 브라우저 설정
    chrome_options = Options()
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])

    service = Service()
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    all_results = []

    # 25/26시즌 분데스리가 18개 팀 명단
    bundesliga_teams = [
        "Borussia Mönchengladbach", "St. Pauli", "Bayer Leverkusen", "Bayern Munich", 
        "Eintracht Frankfurt", "Heidenheim", "Borussia Dortmund", "Augsburg", 
        "Hoffenheim", "Wolfsburg", "Hamburg", "Cologne", "Werder Bremen", 
        "Mainz", "Freiburg", "Union Berlin", "VfB Stuttgart", "RB Leipzig"
    ]
    teams_lower = [t.lower() for t in bundesliga_teams]

    try:
        print("\n" + "="*60)
        print("🤖 [봇 자동화 진행 중 - 분데스리가]")
        print("="*60)

        print("\n🚀 데이터 스캐닝을 시작합니다! (1~34라운드)")

        for gw in range(1, 35):
            url = f"https://www.bundesliga.com/en/bundesliga/matchday/2025-2026/{gw}"
            print(f"\n▶️ [MATCHDAY {gw}] 이동 및 데이터 추출 중...")
            driver.get(url)
            
            time.sleep(5) 
            
            # 첫 주차 쿠키 팝업 처리
            if gw == 1:
                try:
                    btn = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.ID, "onetrust-accept-btn-handler")))
                    btn.click()
                    time.sleep(1)
                except:
                    driver.execute_script("""
                        var overlays = document.querySelectorAll('[id*="onetrust"], [class*="cookie"], [role="dialog"], [class*="modal"]');
                        for (var i = 0; i < overlays.length; i++) { overlays[i].style.display = 'none'; }
                        document.body.style.overflow = 'auto';
                    """)

            driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
            time.sleep(1)
            
            page_text = driver.execute_script("return document.body.innerText;")
            lines = [line.strip() for line in page_text.split('\n') if line.strip()]
            
            current_date = "Unknown Date"
            count = 0
            
            i = 0
            while i < len(lines):
                line = lines[i]
                
                # 1. 날짜 패턴 인식
                months_pattern = r'(August|September|October|November|December|January|February|March|April|May)'
                if re.search(months_pattern, line, re.IGNORECASE):
                    if i > 0 and re.search(r'(MONDAY|TUESDAY|WEDNESDAY|THURSDAY|FRIDAY|SATURDAY|SUNDAY)', lines[i-1], re.IGNORECASE):
                        current_date = f"{lines[i-1]} {line}"
                    else:
                        current_date = line
                    i += 1
                    continue
                
                # 2. 팀 이름 인식 (홈팀 발견 시 작동)
                if line.lower() in teams_lower:
                    home_team = next(t for t in bundesliga_teams if t.lower() == line.lower())
                    away_team = None
                    result_val = "--"
                    scores = []
                    
                    # [시간 찾기] 홈팀 위로 스캔
                    for offset in range(-3, 0):
                        if i + offset >= 0:
                            time_match = re.search(r'^\d{2}:\d{2}$', lines[i+offset])
                            if time_match:
                                result_val = time_match.group(0)
                    
                    # [점수 및 원정팀 찾기]
                    found_away_offset = 0 # 💡 추가된 핵심 변수 (원정팀 위치 기억)
                    for offset in range(1, 16):
                        if i + offset >= len(lines): break
                        candidate = lines[i+offset]
                        
                        # 💡 원정팀을 발견한 경우
                        if candidate.lower() in teams_lower and candidate.lower() != home_team.lower():
                            away_team = next(t for t in bundesliga_teams if t.lower() == candidate.lower())
                            
                            if len(scores) >= 2:
                                result_val = f"{scores[0]} - {scores[-1]}"
                            
                            all_results.append({
                                "Gameweek": f"GW{gw}",
                                "Date": current_date,
                                "Home": home_team,
                                "Away": away_team,
                                "Result/Time": result_val
                            })
                            count += 1
                            found_away_offset = offset # 원정팀 위치 저장
                            break 
                        
                        if candidate.isdigit():
                            scores.append(candidate)
                        elif re.match(r'^\d+\s*[:-]\s*\d+$', candidate):
                            result_val = candidate
                            
                    # 💡 [핵심 해결] 경기를 찾았다면, 원정팀 다음 줄부터 탐색하도록 인덱스를 강제 점프!
                    if found_away_offset > 0:
                        i += found_away_offset
                            
                i += 1
            
            if count == 0:
                print("   ⚠️ 추출된 경기가 없습니다. (아직 일정이 없거나 로딩 지연)")
            else:
                print(f"   ✅ {count}경기 추출 완료!")

            if gw == 34:
                print("   🏁 34라운드 수집 완료!")
                break

    except Exception as e:
        print(f"❌ 크롤링 중 에러 발생: {e}")

    finally:
        driver.quit()
        if all_results:
            df = pd.DataFrame(all_results)
            
            save_folder = "result_csv"
            if not os.path.exists(save_folder):
                os.makedirs(save_folder)
                
            file_path = os.path.join(save_folder, "Bundesliga_2026_All_Matches.csv")
            df.to_csv(file_path, index=False, encoding='utf-8-sig')
            
            print("\n" + "="*40)
            print(f"🎉 성공! 유령 경기가 제거된 데이터가 '{file_path}'에 저장되었습니다.")
            print(df.head())
        else:
            print("수집된 데이터가 없습니다.")

if __name__ == "__main__":
    crawl_bundesliga_github_actions()