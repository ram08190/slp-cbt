import streamlit as st
import pandas as pd
import json
import os
import base64
import time
from datetime import datetime

# 1. 페이지 설정
st.set_page_config(page_title="언어재활사 2급 통합 CBT", layout="wide")

DB_FILE = "quiz_db.csv"
HTML_FILE = "자동화.html"
IMAGE_DIR = "images" # 🌟 깃허브에 올리신 폴더 이름

if not os.path.exists(IMAGE_DIR): 
    os.makedirs(IMAGE_DIR)

# 🌟 [이미지 긴급 복구 함수] D드라이브 경로가 적혀있어도 파일명만 추출해서 깃허브 images 폴더에서 찾음
def get_image_data(img_path):
    if not img_path: return ""
    
    # 1. 파일명만 추출 (예: 'D:\사진\01.png:C' -> '01.png')
    file_name = img_path.replace("\\", "/").split('/')[-1].split(':')[0].strip()
    
    # 2. 깃허브에 올린 images 폴더 내의 실제 경로 생성
    target_path = os.path.join(IMAGE_DIR, file_name)
    
    if os.path.exists(target_path):
        try:
            with open(target_path, "rb") as f:
                encoded = base64.b64encode(f.read()).decode()
                return f"data:image/png;base64,{encoded}"
        except:
            return ""
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

mode = st.sidebar.radio("메뉴 선택", ["📝 시험 시작", "🛠️ 문항 관리"])

# ---------------------------------------------------------
# 모드 1: 시험 시작 (경로 자동 치환 주입)
# ---------------------------------------------------------
if mode == "📝 시험 시작":
    df = st.session_state.df
    s1_list, s2_list = [], []
    for _, row in df.iterrows():
        try:
            real_id = int(row['id'])
            # 🌟 DB의 D드라이브 경로를 무시하고 깃허브 images 폴더에서 데이터를 가져옴
            img_data = get_image_data(clean_val(row.get('img', '')))
            
            q_obj = {
                "id": real_id % 100,
                "text": clean_val(row.get('question', '')),
                "passage": clean_val(row.get('case_box', '')),
                "answer": int(float(clean_val(row.get('answer', 1)) or 1)),
                "img": img_data,
                "options": [{"text": clean_val(row.get(f'option{i}', '')), "img": get_image_data(clean_val(row.get(f'opt_img{i}', '')))} for i in range(1, 6)]
            }
            if real_id < 200: s1_list.append(q_obj)
            else: s2_list.append(q_obj)
        except: continue

    if os.path.exists(HTML_FILE):
        with open(HTML_FILE, "r", encoding="utf-8") as f:
            base_html = f.read()
        
        inject_code = f"""
        <script>
            window.QUESTIONS_S1 = {json.dumps(s1_list, ensure_ascii=False)};
            window.QUESTIONS_S2 = {json.dumps(s2_list, ensure_ascii=False)};
            setTimeout(() => {{ window.render(); }}, 500);
        </script>
        """
        final_html = str(base_html).replace('<script src="questions1.js"></script>', '').replace('<script src="questions2.js"></script>', '').replace('<script src="database.js"></script>', inject_code)
        st.components.v1.html(final_html, height=1200, scrolling=True, key=f"cbt_final_{time.time()}")

# ---------------------------------------------------------
# 모드 2: 문항 관리 (기본 기능만 포함)
# ---------------------------------------------------------
elif mode == "🛠️ 문항 관리":
    st.header("🛠️ 문항 관리")
    all_df = st.session_state.df
    q_idx = st.selectbox("문항 선택", all_df.index, format_func=lambda x: f"{int(all_df.loc[x, 'id'])}번")
    
    # 수정 폼
    all_df.at[q_idx, 'question'] = st.text_area("문제 지문", value=clean_val(all_df.loc[q_idx, 'question']))
    
    if st.button("💾 저장하기"):
        all_df.to_csv(DB_FILE, index=False)
        st.success("저장되었습니다.")
