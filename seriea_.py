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

def crawl_serie_a():
    # 1. 브라우저 설정 (GitHub Actions용 Headless 모드 포함)
    chrome_options = Options()
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--headless=new") # 화면 없이 실행
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])

    service = Service()
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    all_results = []

    # 💡 세리에 A 팀 명단
    serie_a_teams = [
        "ATALANTA", "BOLOGNA", "CAGLIARI", "COMO", "CREMONESE", "EMPOLI", 
        "FIORENTINA", "GENOA", "INTER", "JUVENTUS", "LAZIO", "LECCE", 
        "MILAN", "MONZA", "NAPOLI", "PARMA", "PISA", "ROMA", 
        "SASSUOLO", "TORINO", "UDINESE", "VERONA", "VENEZIA"
    ]
    teams_lower = [t.lower() for t in serie_a_teams]

    try:
        # [Step 1] 접속
        url = "https://www.legaseriea.it/serie-a/calendario-risultati"
        print(f"🌍 접속 중: {url}")
        driver.get(url)

        print("\n" + "="*60)
        print("🤖 [봇 자동화 진행 중 - 세리에 A]")
        print("="*60)

        # -----------------------------------------------------------
        # 쿠키 팝업 처리 (이탈리아어 'Accetta' 수락 버튼)
        # -----------------------------------------------------------
        time.sleep(4)
        try:
            btn_xpath = "//*[(self::button or self::a) and (contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'accetta'))]"
            cookie_btn = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, btn_xpath))
            )
            cookie_btn.click()
            print("   ✅ 쿠키 동의(Accetta) 버튼 클릭 완료!")
            time.sleep(2)
        except:
            driver.execute_script("""
                var overlays = document.querySelectorAll('[id*="onetrust"], [class*="iubenda"], [id*="cookie"], [class*="cookie"], [role="dialog"], [class*="modal"]');
                for (var i = 0; i < overlays.length; i++) { overlays[i].style.display = 'none'; }
                document.body.style.overflow = 'auto';
            """)
            print("   ✅ 팝업 강제 제거 완료")

        # -----------------------------------------------------------
        # MATCHDAY 1로 쾌속 되감기
        # -----------------------------------------------------------
        print("   ⏪ 1라운드(MATCHDAY 1)로 되감기 중...")
        for _ in range(38):
            page_text = driver.execute_script("return document.body.innerText;")
            if "MATCHDAY 1\n" in page_text.upper() or "GIORNATA 1\n" in page_text.upper():
                print("   ✅ MATCHDAY 1 도착 완료!")
                break
            
            try:
                prev_btn_xpath = "//button[contains(translate(@aria-label, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'precedent') or contains(translate(@aria-label, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'previous')]"
                prev_btn = driver.find_element(By.XPATH, prev_btn_xpath)
                driver.execute_script("arguments[0].click();", prev_btn)
                time.sleep(1.5)
            except:
                break

        print("\n🚀 데이터 스캐닝을 시작합니다! (1~38라운드)")

        # [Step 2] 크롤링 루프
        for gw in range(1, 39):
            print(f"\n▶️ [MATCHDAY {gw}] 데이터 추출 중...")
            
            time.sleep(2)
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
            time.sleep(1)
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)
            
            page_text = driver.execute_script("return document.body.innerText;")
            lines = [line.strip() for line in page_text.split('\n') if line.strip()]
            
            current_datetime = "Unknown Date"
            count = 0
            
            i = 0
            while i < len(lines):
                line = lines[i]
                
                # 1. 💡 [핵심 해결] 날짜와 시간 완벽 결합 로직
                # HTML 텍스트에 '|'가 없어도, 날짜 패턴(lun, mar...)을 찾으면 시간과 예쁘게 합쳐줍니다.
                date_match = re.match(r'^(lun|mar|mer|gio|ven|sab|dom),\s\d{1,2}\s[a-zA-Z]{3}', line, re.IGNORECASE)
                if date_match:
                    # 1) 날짜와 시간이 같은 줄에 붙어있는 경우
                    time_match = re.search(r'\d{2}:\d{2}', line)
                    if time_match:
                        current_datetime = f"{date_match.group(0)} | {time_match.group(0)}"
                        i += 1
                        continue
                    # 2) 날짜 아래 줄에 시간이 나뉘어 있는 경우
                    elif i + 1 < len(lines) and re.match(r'^\d{2}:\d{2}$', lines[i+1]):
                        current_datetime = f"{line} | {lines[i+1]}"
                        i += 2
                        continue
                    else:
                        current_datetime = line
                        i += 1
                        continue
                
                # 2. 홈팀 찾기
                is_home_team = line.lower() in teams_lower
                
                if is_home_team:
                    try:
                        home_team = line
                        raw_away = "Unknown"
                        found_match = False
                        
                        middle_elements = []
                        for offset in range(1, 6):
                            if i + offset >= len(lines): break
                            
                            next_line = lines[i + offset]
                            
                            if next_line.upper() in ['DAZN', 'SKY']:
                                continue
                                
                            if next_line.lower() in teams_lower:
                                raw_away = next_line
                                found_match = True
                                i += offset 
                                break
                            else:
                                middle_elements.append(next_line)
                        
                        if found_match:
                            nums = [val for val in middle_elements if val.isdigit()]
                            
                            # 💡 미진행 경기 '--' 표기 유지
                            result_val = "--" 
                            
                            if len(nums) >= 2:
                                result_val = f"{nums[0]} - {nums[1]}"
                            

                            # lun (Lunedì) = 월요일 (Mon)
                            # mar (Martedì) = 화요일 (Tue)
                            # mer (Mercoledì) = 수요일 (Wed)
                            # gio (Giovedì) = 목요일 (Thu)
                            # ven (Venerdì) = 금요일 (Fri)
                            # sab (Sabato) = 토요일 (Sat)
                            # dom (Domenica) = 일요일 (Sun)
                            
                            all_results.append({
                                "Gameweek": f"GW{gw}",
                                "Date": current_datetime,  # 이제 'sab, 21 feb | 04:45'가 완벽하게 들어갑니다!
                                "Home": home_team,
                                "Away": raw_away,
                                "Result/Time": result_val
                            })
                            count += 1
                    except:
                        pass
                
                i += 1
            
            if count == 0:
                print("   ⚠️ 추출된 경기가 없습니다.")
            else:
                print(f"   ✅ {count}경기 추출 완료!")

            if gw == 38:
                print("   🏁 38라운드 수집 완료!")
                break

            # -------------------------------------------------------
            # [Step 3] 다음 라운드로 이동
            # -------------------------------------------------------
            button_clicked = False
            try:
                next_btn_xpath = "//button[contains(@aria-label, 'Prossima giornata di campionato')]"
                next_btn = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.XPATH, next_btn_xpath))
                )
                driver.execute_script("arguments[0].click();", next_btn)
                button_clicked = True
            except Exception:
                pass

            if not button_clicked:
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
                
            file_path = os.path.join(save_folder, "SerieA_2026_All_Matches.csv")
            df.to_csv(file_path, index=False, encoding='utf-8-sig')
            
            print("\n" + "="*40)
            print(f"🎉 성공! 세리에 A 데이터가 '{file_path}'에 저장되었습니다.")
            print(df.head())
        else:
            print("수집된 데이터가 없습니다.")

if __name__ == "__main__":
    crawl_serie_a()