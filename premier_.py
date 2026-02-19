import time
import random
import re
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os

def crawl_pl_all_matches_auto():
    # 1. 브라우저 설정
    chrome_options = Options()
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])

    chrome_options.add_argument("--headless")
    
    service = Service()
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    all_results = []

    try:
        # [Step 1] 접속 및 초기 세팅
        url = "https://www.premierleague.com/en/matches?competition=8&season=2025&matchweek=1&month=02"
        print(f"🌍 접속 중: {url}")
        driver.get(url)

        print("\n" + "="*60)
        print("🤖 [봇 자동화 진행 중]")
        print("팝업과 광고를 봇이 알아서 처리합니다. 잠시만 기다려주세요...")
        print("="*60)

        # -----------------------------------------------------------
        # 💡 [추가된 부분] 팝업 자동 제거 로직
        # -----------------------------------------------------------
        # 1. 쿠키 동의 팝업 닫기
        try:
            # 최대 5초간 쿠키 버튼이 나타나길 기다렸다가 클릭합니다.
            cookie_btn = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.ID, "onetrust-accept-btn-handler"))
            )
            cookie_btn.click()
            print("   🍪 쿠키 팝업 자동 닫기 완료!")
            time.sleep(1) # 창이 닫히는 애니메이션 대기
        except:
            print("   🍪 (쿠키 팝업이 없거나 이미 처리되었습니다.)")

        # 2. 전면 광고 팝업 닫기 (With Pride 등)
        try:
            # 최대 5초간 광고 닫기(X) 버튼이 나타나길 기다렸다가 클릭합니다.
            ad_close_btn = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.ID, "advertClose"))
            )
            ad_close_btn.click()
            print("   ❌ 광고 팝업 자동 닫기 완료!")
            time.sleep(1)
        except:
            print("   ❌ (광고 팝업이 없거나 이미 처리되었습니다.)")
        # -----------------------------------------------------------

        print("\n🚀 데이터 스캐닝을 시작합니다! (1~38라운드)")

        # [Step 2] 크롤링 루프
        for mw in range(1, 39):
            print(f"\n▶️ [MW{mw}] 데이터 추출 중...")
            
            # 페이지 스크롤 (데이터 로딩 유도)
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
            time.sleep(1)
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2) 
            
            # 텍스트 전체 스캔
            page_text = driver.find_element(By.TAG_NAME, "body").text
            lines = [line.strip() for line in page_text.split('\n') if line.strip()]
            
            current_date = "Unknown Date"
            count = 0
            
            for i, line in enumerate(lines):
                # 1. 날짜 업데이트 (예: Sun 22 Feb)
                if re.match(r'^(Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s\d{1,2}\s[a-zA-Z]{3,}', line):
                    current_date = line
                    continue
                
                # 2. 💡 핵심: '가운데 기준점' 찾기
                middle_pattern = r'^(\d+\s*-\s*\d+|\d{2}:\d{2}|v|Postponed|TBC)$'
                
                if re.match(middle_pattern, line, re.IGNORECASE):
                    try:
                        home_team = lines[i-1]
                        away_team = lines[i+1]
                        result_or_time = line
                        
                        invalid_keywords = ['FT', 'HT', 'Live blog >', 'Matchweek']
                        if home_team in invalid_keywords or away_team in invalid_keywords:
                            continue
                        if re.match(r'^(Mon|Tue|Wed|Thu|Fri|Sat|Sun)', home_team):
                            continue
                        
                        all_results.append({
                            "Matchweek": f"MW{mw}",
                            "Date": current_date,
                            "Home": home_team,
                            "Away": away_team,
                            "Result/Time": result_or_time
                        })
                        count += 1
                    except IndexError:
                        pass
            
            if count == 0:
                print("   ⚠️ 추출된 경기가 없습니다.")
            else:
                print(f"   ✅ {count}경기 추출 완료!")

            if mw == 38:
                print("   🏁 38라운드 수집 완료!")
                break

            # -------------------------------------------------------
            # [Step 3] 다음 라운드로 이동
            # -------------------------------------------------------
            print(f"   👉 다음 라운드(MW{mw+1})로 넘어가는 중...")
            button_clicked = False
            try:
                next_btn = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "button[aria-label='Next Matchweek']"))
                )
                driver.execute_script("arguments[0].click();", next_btn)
                button_clicked = True
                
                # 다음 페이지 로딩 대기
                time.sleep(3) 
            except Exception as e:
                pass

            if not button_clicked:
                print("\n   ❌ 봇이 '>' 버튼을 찾지 못했습니다.")
                print(f"   👉 브라우저에서 직접 '>' 버튼을 눌러 [MW{mw+1}] 화면으로 넘겨주세요.")
                input("   >> 화면이 넘어갔다면 [Enter] 키를 쳐주세요...")

    except Exception as e:
        print(f"❌ 크롤링 중 에러 발생: {e}")

    finally:
        driver.quit()
        if all_results:
            df = pd.DataFrame(all_results)
            
            # 1. 저장할 폴더 이름 설정 (리그앙 코드와 동일하게 맞춰줍니다)
            save_folder = "result_csv"
            
            # 2. 해당 폴더가 없으면 자동으로 생성
            if not os.path.exists(save_folder):
                os.makedirs(save_folder)
                
            # 3. 폴더 경로와 프리미어리그 파일 이름을 합쳐서 최종 저장 경로 생성
            file_path = os.path.join(save_folder, "PL_2025_All_Matches_Auto.csv")
            
            # 4. 생성된 경로에 CSV 파일 저장
            df.to_csv(file_path, index=False, encoding='utf-8-sig')
            
            print("\n" + "="*40)
            print(f"🎉 성공! 프리미어리그 데이터가 '{file_path}'에 저장되었습니다.")
            print(df.head())
        else:
            print("수집된 데이터가 없습니다.")

if __name__ == "__main__":
    crawl_pl_all_matches_auto()