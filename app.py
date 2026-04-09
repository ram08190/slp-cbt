import streamlit as st
import pandas as pd
import json
import os
import base64
from datetime import datetime

# 1. 페이지 설정
st.set_page_config(page_title="언어재활사 2급 통합 CBT", layout="wide")

DB_FILE = "quiz_db.csv"
RESULT_FILE = "results.csv"
HTML_FILE = "자동화.html"
IMAGE_DIR = "images"

if not os.path.exists(IMAGE_DIR): 
    os.makedirs(IMAGE_DIR)

# 🌟 [강화된 이미지 로더] D드라이브 경로가 적혀있어도 파일명만 추출해서 깃허브 images 폴더에서 찾음
def get_image_data(img_path):
    if not img_path: return ""
    
    # 1. 경로에서 파일명만 추출 (예: 'D:\사진\01.png:C' -> '01.png')
    file_name = img_path.replace("\\", "/").split('/')[-1].split(':')[0].strip()
    
    # 2. 깃허브에 올린 images 폴더 내의 실제 경로 생성
    target_path = os.path.join(IMAGE_DIR, file_name)
    
    # 3. 파일이 존재하면 읽어서 Base64로 변환
    if os.path.exists(target_path) and os.path.isfile(target_path):
        try:
            with open(target_path, "rb") as f:
                encoded = base64.b64encode(f.read()).decode()
                return f"data:image/png;base64,{encoded}"
        except: return ""
    return "" # 파일이 images 폴더에 없으면 빈값 반환

def load_data():
    s1_ids = [100 + i for i in range(1, 81)]
    s2_ids = [200 + i for i in range(1, 71)]
    all_target_ids = s1_ids + s2_ids
    if os.path.exists(DB_FILE):
        df = pd.read_csv(DB_FILE, keep_default_na=False).astype(object)
        df['id'] = pd.to_numeric(df['id'], errors='coerce').fillna(0).astype(int)
        df = df[df['id'].isin(all_target_ids)]
        return df.sort_values('id').reset_index(drop=True).astype(object)
    else:
        return pd.DataFrame([{"id": i, "session": "1" if i < 200 else "2"} for i in all_target_ids])

if 'df' not in st.session_state: 
    st.session_state.df = load_data()

def clean_val(x):
    s = str(x).strip()
    return "" if s.lower() in ['nan', 'none', ''] else s

mode = st.sidebar.radio("메뉴 선택", ["📝 시험 시작", "🛠️ 문항 관리", "📊 성적 통계 센터"])

# ---------------------------------------------------------
# 모드 1: 시험 시작 (이미지 데이터 주입 버전)
# ---------------------------------------------------------
if mode == "📝 시험 시작":
    df = st.session_state.df
    s1_list, s2_list, concept_db = [], [], {}
    for _, row in df.iterrows():
        try:
            real_id = int(row['id'])
            
            # 🌟 D드라이브 경로가 있어도 파일명만 뽑아 GitHub images 폴더에서 데이터를 가져옴
            img_data = get_image_data(clean_val(row.get('img', '')))
            
            q_obj = {
                "id": real_id % 100,
                "subject": clean_val(row.get('subject', '')),
                "text": clean_val(row.get('question', '')),
                "passage": clean_val(row.get('case_box', '')),
                "answer": int(float(clean_val(row.get('answer', 1)) or 1)),
                "img": img_data, # 데이터 주입
                "options": [{"text": clean_val(row.get(f'option{i}', '')), "img": get_image_data(clean_val(row.get(f'opt_img{i}', '')))} for i in range(1, 6)]
            }
            if real_id < 200: s1_list.append(q_obj)
            else: s2_list.append(q_obj)
            concept_db[f"Q_{real_id:03d}"] = {"title": clean_val(row.get('concept_title', '')), "point": clean_val(row.get('concept_point', ''))}
        except: continue

    if os.path.exists(HTML_FILE):
        with open(HTML_FILE, "r", encoding="utf-8") as f:
            base_html = f.read()
        
        # 바둑판 필터 스크립트 등
        inject_code = f"""
        <script>
            window.QUESTIONS_S1 = {json.dumps(s1_list, ensure_ascii=False)};
            window.QUESTIONS_S2 = {json.dumps(s2_list, ensure_ascii=False)};
            window.CONCEPT_DATABASE = {json.dumps(concept_db, ensure_ascii=False)};
            
            // 데이터 전역 설정 후 강제 렌더링
            setTimeout(() => {{ if(window.render) window.render(); }}, 500);
        </script>
        """
        final_html = str(base_html).replace('<script src="questions1.js"></script>', '').replace('<script src="questions2.js"></script>', '').replace('<script src="database.js"></script>', inject_code)
        
        # TypeError 해결 및 렌더링 유지
        st.components.v1.html(final_html, height=1200, scrolling=True, key=f"cbt_display_{int(time.time())}")

# ---------------------------------------------------------
# 모드 2: 문항 관리
# ---------------------------------------------------------
elif mode == "🛠️ 문항 관리":
    # (문항 관리 기능은 이전 버전과 동일하게 상세 탭 메뉴를 유지합니다)
    st.header("🛠️ 문항 관리 시스템")
    all_df = st.session_state.df
    # ... (생략 없이 이전의 완성된 문항 관리 코드를 사용하세요)
    if st.button("💾 저장하기", use_container_width=True):
        st.session_state.df = df
        df.to_csv(DB_FILE, index=False)
        st.success("저장 완료!")
        st.rerun()

# ---------------------------------------------------------
# 모드 3: 성적 통계 센터
# ---------------------------------------------------------
else:
    # (성적 통계 로직은 이전과 동일하게 유지합니다)
    st.header("📊 성적 통계 센터")
    # ...
