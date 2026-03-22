import time
import re
import os
import json
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def crawl_uefa_cl_github_actions():
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

    try:
        url = "https://www.uefa.com/uefachampionsleague/fixtures-results/#/d/2025-06-17"
        print(f"🌍 접속 중: {url}")
        driver.get(url)

        print("\n" + "="*60)
        print("🤖 [봇 자동화 진행 중 - UEFA 챔피언스리그]")
        print("="*60)

        # -----------------------------------------------------------
        # 쿠키 팝업 처리
        # -----------------------------------------------------------
        time.sleep(5)
        try:
            btn = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.ID, "onetrust-accept-btn-handler")))
            btn.click()
            print("   ✅ 쿠키 동의 버튼 클릭 완료!")
        except:
            driver.execute_script("""
                var overlays = document.querySelectorAll('[id*="onetrust"], [class*="cookie"], [role="dialog"], [class*="modal"]');
                for (var i = 0; i < overlays.length; i++) { overlays[i].style.display = 'none'; }
                document.body.style.overflow = 'auto';
            """)
            print("   ✅ 팝업 강제 제거 완료")

        # -----------------------------------------------------------
        # 실시간 스크롤 & 스캔 로직
        # -----------------------------------------------------------
        print("\n🚀 화면을 조금씩 내리며 모든 경기를 실시간으로 스캔합니다. (약 2~3분 소요)")
        
        current_date = "Unknown Date"
        current_round = "Unknown Round"
        parsed_ids = set()
        
        no_change_limit = 5
        no_change_count = 0
        last_scroll_y = -1
        
        for _ in range(300): 
            elements = driver.find_elements(By.XPATH, "//h2 | //h3 | //a[@data-tracking-type='card']")
            
            new_found = 0
            for elem in elements:
                try:
                    tag = elem.tag_name.lower()
                    text = elem.text.strip()
                    
                    if tag == 'h2':
                        if text: current_date = text
                    elif tag == 'h3':
                        if text: current_round = text
                    elif tag == 'a':
                        tracking_data = elem.get_attribute("data-tracking")
                        if tracking_data:
                            data = json.loads(tracking_data)
                            match_id = data.get("id")
                            match_name = data.get("name", "") 
                            
                            if match_id and match_id not in parsed_ids and " vs " in match_name:
                                parsed_ids.add(match_id)
                                
                                teams = match_name.split(" vs ", 1)
                                home_team = teams[0].strip()
                                away_team = teams[1].strip()
                                
                                lines = [l.strip() for l in text.split('\n') if l.strip()]
                                result_val = "--"
                                
                                # 💡 [핵심 해결] 영상 시간(01:59)보다 점수 추출을 최우선으로 배치!
                                nums = [l for l in lines if l.isdigit()]
                                if len(nums) >= 2:
                                    # 숫자가 2개 이상 있으면 무조건 '점수'로 인식
                                    result_val = f"{nums[0]} - {nums[1]}"
                                else:
                                    # 점수가 없을 때(예정된 경기)에만 시간을 인식
                                    for l in lines:
                                        if re.match(r'^\d{2}:\d{2}$', l):
                                            result_val = l
                                            break
                                
                                all_results.append({
                                    "Gameweek": current_round, 
                                    "Date": current_date,
                                    "Home": home_team,
                                    "Away": away_team,
                                    "Result/Time": result_val
                                })
                                new_found += 1
                except Exception:
                    continue
            
            if new_found > 0:
                print(f"   ✅ 데이터 수집 중... (현재까지 누적: {len(all_results)}경기)")
                
            driver.execute_script("window.scrollBy(0, 800);")
            time.sleep(1.5)
            
            current_scroll_y = driver.execute_script("return window.scrollY;")
            if current_scroll_y == last_scroll_y:
                no_change_count += 1
                if no_change_count >= no_change_limit:
                    print("   🏁 결승전(5월) 끝까지 도달하여 스크롤을 종료합니다!")
                    break
            else:
                no_change_count = 0
                last_scroll_y = current_scroll_y

        if len(all_results) == 0:
            print("   ⚠️ 추출된 경기가 없습니다.")
        else:
            print(f"\n   🎉 시즌 전체 스캔 완료! 총 {len(all_results)}개의 챔피언스리그 경기 추출 성공!")

    except Exception as e:
        print(f"❌ 크롤링 중 에러 발생: {e}")

    finally:
        driver.quit()
        if all_results:
            df = pd.DataFrame(all_results)
            
            save_folder = "result_csv"
            if not os.path.exists(save_folder):
                os.makedirs(save_folder)
                
            file_path = os.path.join(save_folder, "UCL_2026_All_Matches.csv")
            df.to_csv(file_path, index=False, encoding='utf-8-sig')
            
            print("\n" + "="*40)
            print(f"🎉 성공! 챔피언스리그 데이터가 '{file_path}'에 저장되었습니다.")
        else:
            print("수집된 데이터가 없습니다.")

if __name__ == "__main__":
    crawl_uefa_cl_github_actions()