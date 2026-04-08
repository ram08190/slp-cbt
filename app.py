import streamlit as st
import pandas as pd
import json
import os
import base64

# 1. 페이지 설정
st.set_page_config(page_title="언어재활사 통합 CBT 관리시스템", layout="wide")

DB_FILE = "quiz_db.csv"
HTML_FILE = "자동화.html"
IMAGE_DIR = "images" # 이미지 저장 폴더

if not os.path.exists(IMAGE_DIR):
    os.makedirs(IMAGE_DIR)

# 데이터 로드 (TypeError 및 nan 방지)
def load_data():
    required_cols = [
        "id", "session", "subject", "question", "case_box", "answer", 
        "option1", "option2", "option3", "option4", "option5",
        "img", "opt_img1", "opt_img2", "opt_img3", "opt_img4", "opt_img5",
        "concept_title", "concept_point", "concept_mindmap", "concept_video"
    ]
    if os.path.exists(DB_FILE):
        df = pd.read_csv(DB_FILE, keep_default_na=False).astype(object)
        for col in required_cols:
            if col not in df.columns: df[col] = ""
        return df
    else:
        initial_data = [{"id": i, "session": "1" if i<=70 else "2"} for i in range(1, 141)]
        df = pd.DataFrame(initial_data).astype(object)
        for col in required_cols:
            if col not in df.columns: df[col] = ""
        return df

if 'df' not in st.session_state:
    st.session_state.df = load_data()

# --- 유틸리티 함수: nan 텍스트 제거 ---
def clean_val(x):
    s = str(x).strip()
    if s.lower() in ['nan', 'none', '']: return ""
    return s

mode = st.sidebar.radio("메뉴 선택", ["📝 시험 시작", "🛠️ 문항 관리"])

# ---------------------------------------------------------
# 모드 1: 시험 시작
# ---------------------------------------------------------
if mode == "📝 시험 시작":
    df = st.session_state.df
    s1_list, s2_list, concept_db = [], [], {}

    for _, row in df.iterrows():
        try:
            q_id = int(float(row['id']))
            q_obj = {
                "id": q_id,
                "subject": clean_val(row.get('subject', '')),
                "text": clean_val(row.get('question', '')),
                "passage": clean_val(row.get('case_box', '')),
                "answer": int(float(clean_val(row.get('answer', 1)) or 1)),
                "img": clean_val(row.get('img', '')),
                "options": [
                    {"text": clean_val(row.get(f'option{i}', '')), "img": clean_val(row.get(f'opt_img{i}', ''))} for i in range(1, 6)
                ]
            }
            if str(row.get('session')) == "2": s2_list.append(q_obj)
            else: s1_list.append(q_obj)

            f_id = f"Q_{q_id:03d}"
            concept_db[f_id] = {
                "title": clean_val(row.get('concept_title', '')),
                "point": clean_val(row.get('concept_point', '')),
                "mindmap": clean_val(row.get('concept_mindmap', '')),
                "video": clean_val(row.get('concept_video', ''))
            }
        except: continue

    if os.path.exists(HTML_FILE):
        with open(HTML_FILE, "r", encoding="utf-8") as f:
            base_html = f.read()
        final_html = base_html.replace('<script src="questions1.js"></script>', f'<script>window.QUESTIONS_S1 = {json.dumps(s1_list, ensure_ascii=False)};</script>')\
                              .replace('<script src="questions2.js"></script>', f'<script>window.QUESTIONS_S2 = {json.dumps(s2_list, ensure_ascii=False)};</script>')\
                              .replace('<script src="database.js"></script>', f'<script>window.CONCEPT_DATABASE = {json.dumps(concept_db, ensure_ascii=False)};</script>')
        st.components.v1.html(final_html, height=900, scrolling=False)
    else:
        st.error("자동화.html 파일을 찾을 수 없습니다.")

# ---------------------------------------------------------
# 모드 2: 문항 관리 (이미지 업로드 기능 포함)
# ---------------------------------------------------------
else:
    st.header("🛠️ 문항 및 이미지 업로드 관리")
    df = st.session_state.df.astype(object)
    q_idx = st.selectbox("수정할 문항 선택", df.index, format_func=lambda x: f"[{df.loc[x, 'id']}번] {str(df.loc[x, 'question'])[:30]}...")

    tab1, tab2, tab3 = st.tabs(["1. 문제 정보", "2. 보기/이미지 업로드", "3. 오답 분석"])

    with tab1:
        df.at[q_idx, 'question'] = st.text_area("문제 지문", value=clean_val(df.loc[q_idx, 'question']), key=f"q_{q_idx}")
        df.at[q_idx, 'case_box'] = st.text_area("사례 박스", value=clean_val(df.loc[q_idx, 'case_box']), key=f"c_{q_idx}")
        
        # 메인 이미지 업로드
        st.write("🖼️ **문제 메인 이미지**")
        main_img_file = st.file_uploader("이미지 파일 선택", type=['png', 'jpg', 'jpeg'], key=f"m_up_{q_idx}")
        if main_img_file:
            with open(os.path.join(IMAGE_DIR, main_img_file.name), "wb") as f:
                f.write(main_img_file.getbuffer())
            df.at[q_idx, 'img'] = f"images/{main_img_file.name}:C" # 자동 중앙정렬 옵션 포함
            st.success(f"업로드 완료: {main_img_file.name}")
        
        # 이미지 삭제 버튼
        if st.button("❌ 메인 이미지 삭제", key=f"m_del_{q_idx}"):
            df.at[q_idx, 'img'] = ""
            st.rerun()

    with tab2:
        df.at[q_idx, 'answer'] = st.number_input("정답", 1, 5, value=int(float(clean_val(df.loc[q_idx, 'answer']) or 1)))
        for i in range(1, 6):
            st.markdown(f"--- **보기 {i}** ---")
            df.at[q_idx, f'option{i}'] = st.text_input(f"보기 {i} 텍스트", value=clean_val(df.loc[q_idx, f'option{i}']), key=f"opt_{i}_{q_idx}")
            opt_file = st.file_uploader(f"보기 {i} 이미지 업로드", type=['png', 'jpg', 'jpeg'], key=f"o_up_{i}_{q_idx}")
            if opt_file:
                with open(os.path.join(IMAGE_DIR, opt_file.name), "wb") as f:
                    f.write(opt_file.getbuffer())
                df.at[q_idx, f'opt_img{i}'] = f"images/{opt_file.name}"
                st.info(f"업로드됨: {opt_file.name}")
            if st.button(f"보기 {i} 이미지 삭제", key=f"o_del_{i}_{q_idx}"):
                df.at[q_idx, f'opt_img{i}'] = ""
                st.rerun()

    if st.button("💾 이 문항 최종 저장하기", use_container_width=True):
        st.session_state.df = df
        st.session_state.df.to_csv(DB_FILE, index=False)
        st.success("데이터베이스에 저장되었습니다!")
        st.rerun()
