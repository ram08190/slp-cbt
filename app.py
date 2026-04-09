import streamlit as st
import pandas as pd
import json
import os
import base64
from datetime import datetime

# 1. 페이지 설정
st.set_page_config(page_title="언어재활사 2급 통합 CBT", layout="wide")

DB_FILE = "quiz_db.csv"
HTML_FILE = "자동화.html"
IMAGE_DIR = "images"

if not os.path.exists(IMAGE_DIR): os.makedirs(IMAGE_DIR)

# 🌟 [강화된 이미지 로더] 파일 위치를 끝까지 추적해서 가져옵니다.
def get_image_data(img_path):
    if not img_path: return ""
    
    # 1. 파일명만 추출 (예: images/01.png:C -> 01.png)
    file_name = img_path.split('/')[-1].split(':')[0].strip()
    
    # 2. 찾을 후보 경로들
    search_paths = [
        os.path.join(IMAGE_DIR, file_name), # images/01.png
        file_name,                         # 01.png (최상단)
        img_path.split(':')[0].strip()      # 기록된 전체 경로
    ]
    
    for path in search_paths:
        if os.path.exists(path) and os.path.isfile(path):
            try:
                with open(path, "rb") as f:
                    encoded = base64.b64encode(f.read()).decode()
                    # 파일 확장자에 맞게 mime type 설정
                    ext = path.split('.')[-1].lower()
                    mime = "image/png" if ext == "png" else "image/jpeg"
                    return f"data:{mime};base64,{encoded}"
            except: continue
    return ""

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

if 'df' not in st.session_state: st.session_state.df = load_data()

def clean_val(x):
    s = str(x).strip()
    return "" if s.lower() in ['nan', 'none', ''] else s

mode = st.sidebar.radio("메뉴 선택", ["📝 시험 시작", "🛠️ 문항 관리"])

# ---------------------------------------------------------
# 모드 1: 시험 시작 (강력한 이미지 데이터 주입)
# ---------------------------------------------------------
if mode == "📝 시험 시작":
    df = st.session_state.df
    s1_list, s2_list, concept_db = [], [], {}
    for _, row in df.iterrows():
        try:
            real_id = int(row['id'])
            q_obj = {
                "id": real_id % 100,
                "subject": clean_val(row.get('subject', '')),
                "text": clean_val(row.get('question', '')),
                "passage": clean_val(row.get('case_box', '')),
                "answer": int(float(clean_val(row.get('answer', 1)) or 1)),
                "img": get_image_data(clean_val(row.get('img', ''))), # 👈 강화된 로더 사용
                "options": [{"text": clean_val(row.get(f'option{i}', '')), "img": get_image_data(clean_val(row.get(f'opt_img{i}', '')))} for i in range(1, 6)]
            }
            if real_id < 200: s1_list.append(q_obj)
            else: s2_list.append(q_obj)
        except: continue

    if os.path.exists(HTML_FILE):
        with open(HTML_FILE, "r", encoding="utf-8") as f:
            base_html = f.read()
        inject_code = f"<script>window.QUESTIONS_S1={json.dumps(s1_list, ensure_ascii=False)}; window.QUESTIONS_S2={json.dumps(s2_list, ensure_ascii=False)};</script>"
        final_html = base_html.replace('<script src="questions1.js"></script>', '').replace('<script src="questions2.js"></script>', '').replace('<script src="database.js"></script>', inject_code)
        st.components.v1.html(final_html, height=1200, scrolling=True)

# ---------------------------------------------------------
# 모드 2: 문항 관리
# ---------------------------------------------------------
elif mode == "🛠️ 문항 관리":
    st.header("🛠️ 문항 관리")
    all_df = st.session_state.df
    sel_sess = st.radio("교시", ["1교시", "2교시"], horizontal=True)
    target_df = all_df[all_df['id'] < 200] if "1교시" in sel_sess else all_df[all_df['id'] >= 200]
    q_idx = st.selectbox("문항 선택", target_df.index, format_func=lambda x: f"{int(all_df.loc[x, 'id']) % 100}번")
    
    df = all_df.copy()
    c1, c2 = st.columns([2, 1])
    with c1:
        df.at[q_idx, 'question'] = st.text_area("문제 지문", value=clean_val(df.loc[q_idx, 'question']), key=f"q_{q_idx}")
    with c2:
        m_f = st.file_uploader("이미지 업로드", type=['png','jpg','jpeg'], key=f"m_{q_idx}")
        if m_f:
            with open(os.path.join(IMAGE_DIR, m_f.name), "wb") as f: f.write(m_f.getbuffer())
            df.at[q_idx, 'img'] = f"images/{m_f.name}:C"
            st.success(f"업로드됨: {m_f.name}")

    if st.button("💾 저장하기", use_container_width=True):
        st.session_state.df = df
        df.to_csv(DB_FILE, index=False)
        st.rerun()
