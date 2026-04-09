import streamlit as st
import pandas as pd
import json
import os

# 1. 페이지 설정
st.set_page_config(page_title="언어재활사 2급 통합 CBT", layout="wide")

DB_FILE = "quiz_db.csv"
HTML_FILE = "자동화.html"
IMAGE_DIR = "images"

if not os.path.exists(IMAGE_DIR):
    os.makedirs(IMAGE_DIR)

# [데이터 로드] 1교시 80 / 2교시 70 고정 (ID: 101~180, 201~270)
def load_data():
    required_cols = [
        "id", "session", "subject", "question", "case_box", "answer", 
        "option1", "option2", "option3", "option4", "option5",
        "img", "opt_img1", "opt_img2", "opt_img3", "opt_img4", "opt_img5",
        "concept_title", "concept_point", "concept_mindmap", "concept_video"
    ]
    s1_ids = [100 + i for i in range(1, 81)]
    s2_ids = [200 + i for i in range(1, 71)]
    all_target_ids = s1_ids + s2_ids

    if os.path.exists(DB_FILE):
        df = pd.read_csv(DB_FILE, keep_default_na=False).astype(object)
        # ID를 숫자로 변환
        df['id'] = pd.to_numeric(df['id'], errors='coerce').fillna(0).astype(int)
        existing_ids = df['id'].tolist()
        missing_ids = [i for i in all_target_ids if i not in existing_ids]
        
        if missing_ids:
            new_rows = []
            for m_id in missing_ids:
                row = {col: "" for col in required_cols}
                row["id"] = m_id
                row["session"] = "1" if m_id < 200 else "2"
                new_rows.append(row)
            df = pd.concat([df, pd.DataFrame(new_rows)], ignore_index=True)
        
        # 유효하지 않은 기존 번호(1~150 등)는 제거하고 101~, 201~ 체계만 유지
        df = df[df['id'].isin(all_target_ids)]
        return df.sort_values('id').reset_index(drop=True).astype(object)
    else:
        initial_data = []
        for i in all_target_ids:
            row = {col: "" for col in required_cols}
            row["id"] = i
            row["session"] = "1" if i < 200 else "2"
            initial_data.append(row)
        return pd.DataFrame(initial_data).astype(object)

if 'df' not in st.session_state:
    st.session_state.df = load_data()

def clean_val(x):
    s = str(x).strip()
    if s.lower() in ['nan', 'none', '']: return ""
    return s

# --- 메뉴 선택 ---
mode = st.sidebar.radio("메뉴 선택", ["📝 시험 시작", "🛠️ 문항 관리"])

# ---------------------------------------------------------
# 모드 1: 시험 시작
# ---------------------------------------------------------
if mode == "📝 시험 시작":
    df = st.session_state.df
    s1_list, s2_list, concept_db = [], [], {}

    for _, row in df.iterrows():
        try:
            real_id = int(row['id'])
            display_id = real_id % 100
            
            q_obj = {
                "id": display_id,
                "subject": clean_val(row.get('subject', '')),
                "text": clean_val(row.get('question', '')),
                "passage": clean_val(row.get('case_box', '')),
                "answer": int(float(clean_val(row.get('answer', 1)) or 1)),
                "img": clean_val(row.get('img', '')),
                "options": [{"text": clean_val(row.get(f'option{i}', '')), "img": clean_val(row.get(f'opt_img{i}', ''))} for i in range(1, 6)]
            }
            if real_id < 200: s1_list.append(q_obj)
            else: s2_list.append(q_obj)

            concept_db[f"Q_{real_id:03d}"] = {
                "title": clean_val(row.get('concept_title', '')), "point": clean_val(row.get('concept_point', ''))
            }
        except: continue

    if os.path.exists(HTML_FILE):
        with open(HTML_FILE, "r", encoding="utf-8") as f:
            html_content = f.read()
        
        data_inject = f"""
        <script>
            window.QUESTIONS_S1 = {json.dumps(s1_list, ensure_ascii=False)};
            window.QUESTIONS_S2 = {json.dumps(s2_list, ensure_ascii=False)};
            window.CONCEPT_DATABASE = {json.dumps(concept_db, ensure_ascii=False)};
        </script>
        """
        final_html = html_content.replace('<script src="questions1.js"></script>', '').replace('<script src="questions2.js"></script>', '').replace('<script src="database.js"></script>', data_inject)
        st.components.v1.html(final_html, height=1200, scrolling=True)

# ---------------------------------------------------------
# 모드 2: 문항 관리 (교시 분리 선택형)
# ---------------------------------------------------------
else:
    st.header("🛠️ 문항 관리 시스템")
    
    # 🌟 1. 교시를 먼저 선택하게 함
    sel_session = st.radio("관리할 교시 선택", ["1교시 (신경/유창성/음성)", "2교시 (발달/조음)"], horizontal=True)
    
    # 🌟 2. 선택한 교시에 맞는 문항만 필터링
    all_df = st.session_state.df
    if "1교시" in sel_session:
        target_df = all_df[all_df['id'] < 200]
    else:
        target_df = all_df[all_df['id'] >= 200]
    
    # 🌟 3. 선택한 교시의 문항들만 드롭다운에 표시
    def format_func(idx):
        r_id = int(all_df.loc[idx, 'id'])
        d_id = r_id % 100
        return f"{d_id}번 문제"

    q_idx = st.selectbox("수정할 문항 선택", target_df.index, format_func=format_func)
    
    st.divider()
    
    # 입력 폼
    df = all_df.copy()
    col1, col2 = st.columns([2, 1])
    
    with col1:
        df.at[q_idx, 'subject'] = st.text_input("과목명", value=clean_val(df.loc[q_idx, 'subject']), key=f"s_{q_idx}")
        df.at[q_idx, 'question'] = st.text_area("문제 지문", value=clean_val(df.loc[q_idx, 'question']), height=150, key=f"q_{q_idx}")
        df.at[q_idx, 'case_box'] = st.text_area("사례 박스", value=clean_val(df.loc[q_idx, 'case_box']), key=f"c_{q_idx}")
    
    with col2:
        df.at[q_idx, 'answer'] = st.number_input("정답", 1, 5, value=int(float(clean_val(df.loc[q_idx, 'answer']) or 1)), key=f"a_{q_idx}")
        st.write("🖼️ 이미지")
        m_file = st.file_uploader("파일 업로드", type=['png','jpg','jpeg'], key=f"img_{q_idx}")
        if m_file:
            with open(os.path.join(IMAGE_DIR, m_file.name), "wb") as f: f.write(m_file.getbuffer())
            df.at[q_idx, 'img'] = f"images/{m_file.name}:C"
        if st.button("❌ 이미지 삭제"): df.at[q_idx, 'img'] = ""; st.rerun()

    for i in range(1, 6):
        df.at[q_idx, f'option{i}'] = st.text_input(f"보기 {i}", value=clean_val(df.loc[q_idx, f'option{i}']), key=f"opt_{i}_{q_idx}")

    if st.button("💾 저장하기", use_container_width=True):
        st.session_state.df = df
        df.to_csv(DB_FILE, index=False)
        st.success("저장 완료!")
        st.rerun()
