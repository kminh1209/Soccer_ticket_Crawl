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

def crawl_liga_portugal_github_actions():
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
        url = "https://www.ligaportugal.pt/competition/618/liga-portugal-betclic/round/20252026?tab=general"
        print(f"🌍 접속 중: {url}")
        driver.get(url)

        print("\n" + "="*60)
        print("🤖 [봇 자동화 진행 중 - 포르투갈 리그]")
        print("="*60)

        # -----------------------------------------------------------
        # 쿠키 팝업 강력 처리
        # -----------------------------------------------------------
        time.sleep(4)
        try:
            driver.execute_script("""
                var overlays = document.querySelectorAll('[id*="onetrust"], [class*="cookie"], [id*="cookie"], [role="dialog"], [class*="modal"]');
                for (var i = 0; i < overlays.length; i++) { overlays[i].style.display = 'none'; }
                document.body.style.overflow = 'auto';
            """)
            print("   ✅ 팝업 강제 제거 완료")
        except:
            pass

        print("\n🚀 데이터 스캐닝을 시작합니다! (1~34라운드)")

        # [Step 2] 크롤링 루프
        for gw in range(1, 35):
            print(f"\n▶️ [JORNADA {gw}] 데이터 추출 중...")
            
            clicked = driver.execute_script("""
                var tabs = document.querySelectorAll('a, button, li, .swiper-slide, div');
                for(var i=0; i<tabs.length; i++) {
                    if(tabs[i].innerText) {
                        var text = tabs[i].innerText.trim().toUpperCase();
                        if(text === 'JORNADA ' + arguments[0] || text === 'ROUND ' + arguments[0]) {
                            tabs[i].scrollIntoView({block: 'center', inline: 'center'});
                            tabs[i].click();
                            return true;
                        }
                    }
                }
                return false;
            """, gw)
            
            if not clicked:
                print(f"   ⚠️ 라운드 탭(JORNADA {gw})을 찾지 못했습니다.")
            
            max_retries = 3
            for attempt in range(max_retries):
                wait_time = 5 if attempt == 0 else 3
                time.sleep(wait_time) 
                
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
                time.sleep(1)
                
                elements = driver.find_elements(
                    By.XPATH, 
                    "//*[contains(@class, 'match-item-row-header-date') or contains(concat(' ', normalize-space(@class), ' '), ' match-item-row ')]"
                )
                
                current_date = "Unknown Date"
                count = 0
                temp_results = []
                
                for elem in elements:
                    cls = elem.get_attribute("class")
                    text = elem.text.strip()
                    if not text:
                        continue
                    
                    if "match-item-row-header-date" in cls:
                        current_date = text
                    elif "match-item-row" in cls:
                        lines = [line.strip() for line in text.split('\n') if line.strip()]
                        
                        # 1. 불필요한 텍스트(방송사, 티켓, 연기 등) 필터링
                        def is_ignored(t):
                            t_up = t.upper()
                            ignore_keywords = ['SPORT.TV', 'BTV', 'TVI', 'ELEVEN', 'CANAL 11', 'TICKETS', 'POSTPONED', 'ADIADO', 'BILHETES', 'COMPRAR']
                            return any(k in t_up for k in ignore_keywords)

                        filtered_lines = [l for l in lines if not is_ignored(l)]
                        
                        res_idx = -1
                        # 2. 💡 [핵심 강화] '- -' 기호도 시간/점수로 인식하도록 정규식 업데이트
                        for j, l in enumerate(filtered_lines):
                            if re.match(r'^(\d+\s*-\s*\d+|\d{1,2}:\d{2}|\d{1,2}[Hh]\d{2}|-|--|-\s*-|VS|V)$', l, re.IGNORECASE):
                                res_idx = j
                                break
                        
                        # 3. 홈팀, 원정팀, 결과 매핑
                        if res_idx != -1 and res_idx > 0 and res_idx < len(filtered_lines) - 1:
                            home_team = filtered_lines[res_idx - 1]
                            away_team = filtered_lines[res_idx + 1]
                            result_val = filtered_lines[res_idx]
                            
                            # 💡 '- -' 모양이든 'VS'든 모두 '--' 로 예쁘게 통일
                            if re.match(r'^(-|--|-\s*-|VS|V)$', result_val, re.IGNORECASE):
                                result_val = "--"
                        else:
                            # 기호조차 아예 렌더링되지 않은 예외 상황 대비
                            if len(filtered_lines) >= 2:
                                home_team = filtered_lines[0]
                                away_team = filtered_lines[-1]
                                result_val = "--"
                            else:
                                continue
                                
                        # 연기된(Postponed) 경기 처리
                        if any('POSTPONED' in l.upper() or 'ADIADO' in l.upper() for l in lines):
                            result_val = "--"
                                
                        temp_results.append({
                            "Gameweek": f"GW{gw}",
                            "Date": current_date,
                            "Home": home_team,
                            "Away": away_team,
                            "Result/Time": result_val
                        })
                        count += 1
                
                if count > 0:
                    all_results.extend(temp_results)
                    print(f"   ✅ {count}경기 추출 완료!")
                    break
                else:
                    if attempt < max_retries - 1:
                        print(f"   ⏳ 로딩 지연 감지됨. 추가 대기 후 재시도합니다... ({attempt+1}/{max_retries})")
                    else:
                        print("   ⚠️ 최대 대기 시간 초과. 추출된 경기가 없습니다.")

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
                
            file_path = os.path.join(save_folder, "LigaPortugal_2026_All_Matches.csv")
            df.to_csv(file_path, index=False, encoding='utf-8-sig')
            
            print("\n" + "="*40)
            print(f"🎉 성공! 포르투갈 리그 전체 데이터가 '{file_path}'에 저장되었습니다.")
            print(df.head())
        else:
            print("수집된 데이터가 없습니다.")

if __name__ == "__main__":
    crawl_liga_portugal_github_actions()