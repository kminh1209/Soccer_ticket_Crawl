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

def crawl_eredivisie_github_actions():
    # 1. 브라우저 설정 (GitHub Actions 맞춤형)
    chrome_options = Options()
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--headless=new") # 화면 없이 실행 (필수)
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])

    service = Service()
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    all_results = []

    try:
        # [Step 1] 접속
        url = "https://eredivisie.eu/competition/fixtures/"
        print(f"🌍 접속 중: {url}")
        driver.get(url)

        print("\n" + "="*60)
        print("🤖 [봇 자동화 진행 중 - 에레디비시]")
        print("="*60)

        # -----------------------------------------------------------
        # 쿠키 팝업 처리
        # -----------------------------------------------------------
        time.sleep(4)
        try:
            btn_xpath = "//*[(self::button or self::a) and (contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'accept') or contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'agree'))]"
            cookie_btn = driver.find_element(By.XPATH, btn_xpath)
            driver.execute_script("arguments[0].click();", cookie_btn)
            print("   ✅ 쿠키 동의 버튼 클릭 완료!")
            time.sleep(2)
        except:
            driver.execute_script("""
                var overlays = document.querySelectorAll('[id*="onetrust"], [class*="cookie"], [role="dialog"], [class*="modal"]');
                for (var i = 0; i < overlays.length; i++) { overlays[i].style.display = 'none'; }
                document.body.style.overflow = 'auto';
            """)
            print("   ✅ 팝업 강제 제거 완료")

        # -----------------------------------------------------------
        # MATCHWEEK 1로 쾌속 되감기
        # -----------------------------------------------------------
        print("   ⏪ 1라운드(MATCHWEEK 1)로 되감기 중...")
        for _ in range(34): # 에레디비시는 총 34라운드
            page_text = driver.execute_script("return document.body.innerText;")
            if "MATCHWEEK 1\n" in page_text.upper():
                print("   ✅ MATCHWEEK 1 도착 완료!")
                break
            
            try:
                prev_btn = driver.find_element(By.XPATH, "//button[@aria-label='Previous round']")
                driver.execute_script("arguments[0].click();", prev_btn)
                time.sleep(2) 
            except:
                break

        print("\n🚀 데이터 스캐닝을 시작합니다! (1~34라운드)")

        # [Step 2] 크롤링 루프
        for gw in range(1, 35):
            print(f"\n▶️ [MATCHWEEK {gw}] 데이터 추출 중...")
            
            time.sleep(3) 
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
            time.sleep(1)
            
            page_text = driver.execute_script("return document.body.innerText;")
            lines = [line.strip() for line in page_text.split('\n') if line.strip()]
            
            count = 0
            
            i = 0
            while i < len(lines):
                line = lines[i]
                
                # 1. 날짜 패턴 인식 (예: "SUN, 11 JANUARY 2026")
                if re.match(r'^(MON|TUE|WED|THU|FRI|SAT|SUN)[,\s]+\d{1,2}\s[A-Za-z]+(\s\d{4})?$', line, re.IGNORECASE):
                    current_date = line
                    
                    for offset in range(1, 8):
                        if i + offset >= len(lines): break
                        
                        candidate = lines[i + offset]
                        
                        # 💡 [상황 A] 미진행 경기 (시간 표기) -> "14:30"
                        if re.match(r'^\d{2}:\d{2}$', candidate):
                            home_team = lines[i + offset - 1]
                            away_team = lines[i + offset + 1]
                            
                            all_results.append({
                                "Gameweek": f"GW{gw}",
                                "Date": current_date,
                                "Home": home_team,
                                "Away": away_team,
                                "Result/Time": candidate
                            })
                            count += 1
                            i += offset
                            break
                            
                        # 💡 [상황 B] 진행 완료 경기 (점수가 쪼개진 경우) -> 위:점수, 중간:-, 아래:점수
                        elif candidate == '-':
                            if lines[i + offset - 1].isdigit() and lines[i + offset + 1].isdigit():
                                home_team = lines[i + offset - 2] # 2칸 위가 홈팀
                                away_team = lines[i + offset + 2] # 2칸 아래가 원정팀
                                home_score = lines[i + offset - 1]
                                away_score = lines[i + offset + 1]
                                
                                all_results.append({
                                    "Gameweek": f"GW{gw}",
                                    "Date": current_date,
                                    "Home": home_team,
                                    "Away": away_team,
                                    "Result/Time": f"{home_score} - {away_score}"
                                })
                                count += 1
                                i += (offset + 1)
                                break
                                
                        # 💡 [상황 C] 점수가 한 줄에 붙어있는 경우 (혹시 모를 예비용) -> "1 - 0"
                        elif re.match(r'^\d+\s*-\s*\d+$', candidate):
                            home_team = lines[i + offset - 1]
                            away_team = lines[i + offset + 1]
                            
                            all_results.append({
                                "Gameweek": f"GW{gw}",
                                "Date": current_date,
                                "Home": home_team,
                                "Away": away_team,
                                "Result/Time": candidate
                            })
                            count += 1
                            i += offset
                            break
                            
                        # 💡 [상황 D] 기타 미진행 표시 ("--", "VS" 등)
                        elif candidate.upper() in ['--', 'VS', 'V']:
                            home_team = lines[i + offset - 1]
                            away_team = lines[i + offset + 1]
                            
                            all_results.append({
                                "Gameweek": f"GW{gw}",
                                "Date": current_date,
                                "Home": home_team,
                                "Away": away_team,
                                "Result/Time": "--"
                            })
                            count += 1
                            i += offset
                            break
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
            try:
                next_btn = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.XPATH, "//button[@aria-label='Next round']"))
                )
                driver.execute_script("arguments[0].click();", next_btn)
            except Exception:
                print("\n   ❌ 봇이 다음 라운드 버튼을 찾지 못해 크롤링을 종료합니다.")
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
                
            file_path = os.path.join(save_folder, "Eredivisie_2026_All_Matches.csv")
            df.to_csv(file_path, index=False, encoding='utf-8-sig')
            
            print("\n" + "="*40)
            print(f"🎉 성공! 에레디비시 전체 데이터가 '{file_path}'에 저장되었습니다.")
            print(df.head())
        else:
            print("수집된 데이터가 없습니다.")

if __name__ == "__main__":
    crawl_eredivisie_github_actions()