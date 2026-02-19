import time
import re
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os

def crawl_ligue1_perfect_filtered():
    # 1. 브라우저 설정
    chrome_options = Options()
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])

    chrome_options.add_argument("--headless")
    
    service = Service()
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    all_results = []

    # 💡 리그앙 18개 팀 명단 
    ligue1_teams = [
        "PSG", "OM", "OL", "AS Monaco", "LOSC", "RC Lens", "Rennes", "OGC Nice", 
        "Reims", "Toulouse", "Montpellier", "Strasbourg", "Nantes", "Le Havre", "Metz", 
        "Brest", "Lorient", "Clermont", "Auxerre", "Angers", "Saint-Étienne", "Paris FC",
        "Havre AC", "Angers SCO", "FC Nantes", "FC Metz", "FC Lorient", "Toulouse FC", "AJ Auxerre"
    ]
    
    # 비교를 위해 전부 소문자로 변환해 둡니다.
    ligue1_teams_lower = [t.lower() for t in ligue1_teams]

    try:
        # [Step 1] 접속
        url = "https://ligue1.com/en/competitions/ligue1mcdonalds/results?gameweek=1"
        print(f"🌍 접속 중: {url}")
        driver.get(url)

        print("\n" + "="*60)
        print("🤖 [봇 자동화 진행 중]")
        print("우측 뉴스 영역을 차단하고 경기 일정만 수집합니다...")
        print("="*60)

        # -----------------------------------------------------------
        # 쿠키 팝업 처리 (수정됨)
        # -----------------------------------------------------------
        time.sleep(3)
        try:
            btn_xpath = "//*[(self::button or self::a) and (contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'tout refuser') or contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'reject'))]"
            cookie_btns = driver.find_elements(By.XPATH, btn_xpath)
            
            if cookie_btns and cookie_btns[0].is_displayed():
                driver.execute_script("arguments[0].click();", cookie_btns[0])
                print("   ✅ 쿠키 거절 버튼 클릭 완료")
                time.sleep(1)
            else:
                driver.execute_script("""
                    var overlays = document.querySelectorAll('[id*="onetrust"], [class*="didomi"], [id*="cookie"], [class*="cookie"]');
                    // 💡 elements -> overlays 로 변수명 수정 완료
                    for (var i = 0; i < overlays.length; i++) overlays[i].style.display = 'none';
                    document.body.style.overflow = 'auto';
                """)
                print("   ✅ 팝업 강제 삭제 완료")
        except Exception as e:
            # 에러가 나면 그냥 넘어가지 않고 로그를 출력하도록 수정
            print(f"   ⚠️ 팝업 처리 중 에러 발생: {e}")
            
            

        print("\n🚀 데이터 스캐닝을 시작합니다! (1~34라운드)")

        # [Step 2] 크롤링 루프
        for gw in range(1, 35):
            print(f"\n▶️ [Gameweek {gw}] 데이터 추출 중...")
            
            # 스크롤
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
            time.sleep(1)
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2) 
            
            # 페이지 텍스트 가져오기
            page_text = driver.find_element(By.TAG_NAME, "body").text
            lines = [line.strip() for line in page_text.split('\n') if line.strip()]
            
            current_date = "Unknown Date"
            count = 0
            
            i = 0
            while i < len(lines):
                line = lines[i]
                
                # 1. 날짜 인식
                if re.search(r'(MONDAY|TUESDAY|WEDNESDAY|THURSDAY|FRIDAY|SATURDAY|SUNDAY)\s\d{1,2}\s[A-Za-z]{3,}', line, re.IGNORECASE):
                    current_date = line
                    i += 1
                    continue
                
                # 2. 💡 [핵심 변경] 홈팀 100% 일치 검사
                # 괄호(순위)를 떼어낸 글자가 리그앙 팀 명단과 '정확히' 일치해야만 통과
                clean_line = re.sub(r'^\(\d+\)\s*|\s*\(\d+\)$', '', line).strip()
                
                is_home_team = clean_line.lower() in ligue1_teams_lower
                
                if is_home_team:
                    try:
                        raw_home = line
                        result_or_time = "--" 
                        raw_away = "Unknown"
                        found_match = False
                        
                        # 홈팀 아래 5줄까지 스캔
                        for offset in range(1, 6):
                            if i + offset >= len(lines): break
                            
                            next_line = lines[i + offset]
                            clean_next = re.sub(r'^\(\d+\)\s*|\s*\(\d+\)$', '', next_line).strip()
                            
                            # 점수 또는 시간 확인
                            if re.search(r'^\d+\s*-\s*\d+$', next_line) or re.search(r'(\d{1,2}:\d{2}|AM|PM|Postponed|TBC)', next_line, re.IGNORECASE):
                                result_or_time = next_line
                                continue
                            
                            # 방송사 키워드는 무시
                            if any(k in next_line.upper() for k in ['LIGUE', 'BEIN', 'DAZN', 'SPORTS', 'CANAL', 'PRIME']):
                                continue
                                
                            # 💡 [핵심 변경] 원정팀도 100% 일치 검사
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

            # -------------------------------------------------------
            # [Step 3] 다음 라운드로 이동
            # -------------------------------------------------------
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
                print(f"   👉 브라우저에서 직접 다음 라운드(GW{gw+1}) 화면으로 넘겨주세요.")
                input("   >> 화면이 넘어갔다면 [Enter] 키를 쳐주세요...")

    except Exception as e:
        print(f"❌ 크롤링 중 에러 발생: {e}")

    finally:
        driver.quit()
        if all_results:
            df = pd.DataFrame(all_results)
            
            # 💡 1. 저장할 폴더 이름 설정 (원하는 이름으로 변경 가능)
            save_folder = "result_csv"
            
            # 💡 2. 해당 폴더가 없으면 자동으로 생성
            if not os.path.exists(save_folder):
                os.makedirs(save_folder)
                
            # 💡 3. 폴더 경로와 파일 이름을 합쳐서 최종 저장 경로 생성
            file_path = os.path.join(save_folder, "Ligue1_2025_Final_Clean.csv")
            
            # 💡 4. 생성된 경로에 CSV 파일 저장
            df.to_csv(file_path, index=False, encoding='utf-8-sig')
            
            print("\n" + "="*40)
            print(f"🎉 성공! 우측 기사가 제거된 데이터가 '{file_path}'에 저장되었습니다.")
            print(df.head())
        else:
            print("수집된 데이터가 없습니다.")

if __name__ == "__main__":
    crawl_ligue1_perfect_filtered()