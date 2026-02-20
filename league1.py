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

def crawl_ligue1_github_actions():
    # 1. 브라우저 설정 (GitHub Actions 맞춤형)
    chrome_options = Options()
    chrome_options.add_argument("--window-size=1920,1080")
    # 💡 [필수 추가] 모니터가 없는 환경(GitHub Actions)에서 정상 작동하게 만듭니다.
    chrome_options.add_argument("--headless=new") 
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])

    service = Service()
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    all_results = []

    ligue1_teams = [
        "PSG", "OM", "OL", "AS Monaco", "LOSC", "RC Lens", "Rennes", "OGC Nice", 
        "Reims", "Toulouse", "Montpellier", "Strasbourg", "Nantes", "Le Havre", "Metz", 
        "Brest", "Lorient", "Clermont", "Auxerre", "Angers", "Saint-Étienne", "Paris FC",
        "Havre AC", "Angers SCO", "FC Nantes", "FC Metz", "FC Lorient", "Toulouse FC", "AJ Auxerre"
    ]
    ligue1_teams_lower = [t.lower() for t in ligue1_teams]

    try:
        url = "https://ligue1.com/en/competitions/ligue1mcdonalds/results?gameweek=1"
        print(f"🌍 접속 중: {url}")
        driver.get(url)

        print("\n" + "="*60)
        print("🤖 [봇 자동화 진행 중 - Headless 모드]")
        print("="*60)

        # 쿠키 팝업 처리
        time.sleep(3)
        try:
            btn_xpath = "//*[(self::button or self::a) and (contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'tout refuser') or contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'reject'))]"
            cookie_btns = driver.find_elements(By.XPATH, btn_xpath)
            
            if cookie_btns and cookie_btns[0].is_displayed():
                driver.execute_script("arguments[0].click();", cookie_btns[0])
                time.sleep(1)
            else:
                driver.execute_script("""
                    var overlays = document.querySelectorAll('[id*="onetrust"], [class*="didomi"], [id*="cookie"], [class*="cookie"]');
                    for (var i = 0; i < overlays.length; i++) elements[i].style.display = 'none';
                    document.body.style.overflow = 'auto';
                """)
        except:
            pass

        print("\n🚀 데이터 스캐닝을 시작합니다! (1~34라운드)")

        for gw in range(1, 35):
            print(f"\n▶️ [Gameweek {gw}] 데이터 추출 중...")
            
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
            time.sleep(1)
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2) 
            
            # 💡 [핵심 변경] 화면 렌더링에 의존하는 .text 대신, 자바스크립트로 강제로 내부 텍스트를 긁어옵니다.
            page_text = driver.execute_script("return document.body.innerText;")
            lines = [line.strip() for line in page_text.split('\n') if line.strip()]
            
            current_date = "Unknown Date"
            count = 0
            
            i = 0
            while i < len(lines):
                line = lines[i]
                
                # 날짜 인식
                if re.search(r'(MONDAY|TUESDAY|WEDNESDAY|THURSDAY|FRIDAY|SATURDAY|SUNDAY)\s\d{1,2}\s[A-Za-z]{3,}', line, re.IGNORECASE):
                    current_date = line
                    i += 1
                    continue
                
                # 홈팀 검사
                clean_line = re.sub(r'^\(\d+\)\s*|\s*\(\d+\)$', '', line).strip()
                is_home_team = clean_line.lower() in ligue1_teams_lower
                
                if is_home_team:
                    try:
                        raw_home = line
                        result_or_time = "--" 
                        raw_away = "Unknown"
                        found_match = False
                        
                        for offset in range(1, 6):
                            if i + offset >= len(lines): break
                            
                            next_line = lines[i + offset]
                            clean_next = re.sub(r'^\(\d+\)\s*|\s*\(\d+\)$', '', next_line).strip()
                            
                            if re.search(r'^\d+\s*-\s*\d+$', next_line) or re.search(r'(\d{1,2}:\d{2}|AM|PM|Postponed|TBC)', next_line, re.IGNORECASE):
                                result_or_time = next_line
                                continue
                            
                            if any(k in next_line.upper() for k in ['LIGUE', 'BEIN', 'DAZN', 'SPORTS', 'CANAL', 'PRIME']):
                                continue
                                
                            if clean_next.lower() in ligue1_teams_lower:
                                raw_away = next_line
                                found_match = True
                                i += offset 
                                break
                        
                        if found_match:
                            home_team = re.sub(r'^\(\d+\)\s*|\s*\(\d+\)$', '', raw_home).strip()
                            away_team = re.sub(r'^\(\d+\)\s*|\s*\(\d+\)$', '', raw_away).strip()
                            
                            if not re.search(r'(\d|--|Postponed|TBC)', result_or_time):
                                result_or_time = "--"
                            
                            all_results.append({
                                "Gameweek": f"GW{gw}",
                                "Date": current_date,
                                "Home": home_team,
                                "Away": away_team,
                                "Result/Time": result_or_time
                            })
                            count += 1
                    except:
                        pass
                
                i += 1
            
            if count == 0:
                print("   ⚠️ 추출된 경기가 없습니다.")
            else:
                print(f"   ✅ {count}경기 추출 완료!")

            if gw == 34:
                print("   🏁 34라운드 수집 완료!")
                break

            # 다음 라운드 이동
            button_clicked = False
            try:
                next_btn = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "button[aria-label='Next gameweek']"))
                )
                driver.execute_script("arguments[0].click();", next_btn)
                button_clicked = True
                time.sleep(4) 
            except Exception:
                pass

            if not button_clicked:
                print("\n   ❌ 봇이 '>' 버튼을 찾지 못했습니다.")
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
                
            file_path = os.path.join(save_folder, "Ligue1_2025_Final_Clean.csv")
            df.to_csv(file_path, index=False, encoding='utf-8-sig')
            
            print("\n" + "="*40)
            print(f"🎉 성공! 리그앙 데이터가 '{file_path}'에 저장되었습니다.")
            print(df.head())
        else:
            print("수집된 데이터가 없습니다.")

if __name__ == "__main__":
    crawl_ligue1_github_actions()
