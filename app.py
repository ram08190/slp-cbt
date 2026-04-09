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

# [데이터 로드] 1교시 80 / 2교시 70 고정 체계 유지
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
        try: df['id'] = df['id'].astype(int)
        except: df['id'] = pd.to_numeric(df['id'], errors='coerce').fillna(0).astype(int)
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
        df = df[df['id'].isin(all_target_ids)]
        return df.sort_values('id').reset_index(drop=True).astype(object)
    else:
        initial_data = [{"id": i, "session": "1" if i < 200 else "2"} for i in all_target_ids]
        return pd.DataFrame(initial_data).astype(object)

if 'df' not in st.session_state:
    st.session_state.df = load_data()

def clean_val(x):
    s = str(x).strip()
    return "" if s.lower() in ['nan', 'none', ''] else s

# 메뉴 선택
mode = st.sidebar.radio("메뉴 선택", ["📝 시험 시작", "🛠️ 문항 관리"])

# ---------------------------------------------------------
# 모드 1: 시험 시작 (자동화.html 데이터 전달)
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
                "img": clean_val(row.get('img', '')),
                "options": [{"text": clean_val(row.get(f'option{i}', '')), "img": clean_val(row.get(f'opt_img{i}', ''))} for i in range(1, 6)]
            }
            if real_id < 200: s1_list.append(q_obj)
            else: s2_list.append(q_obj)
            concept_db[f"Q_{real_id:03d}"] = {"title": clean_val(row.get('concept_title', '')), "point": clean_val(row.get('concept_point', ''))}
        except: continue

    if os.path.exists(HTML_FILE):
        with open(HTML_FILE, "r", encoding="utf-8") as f:
            base_html = f.read()
        data_inject = f"<script>window.QUESTIONS_S1 = {json.dumps(s1_list, ensure_ascii=False)}; window.QUESTIONS_S2 = {json.dumps(s2_list, ensure_ascii=False)}; window.CONCEPT_DATABASE = {json.dumps(concept_db, ensure_ascii=False)};</script>"
        final_html = base_html.replace('<script src="questions1.js"></script>', '').replace('<script src="questions2.js"></script>', '').replace('<script src="database.js"></script>', data_inject)
        st.components.v1.html(final_html, height=1200, scrolling=True)

# ---------------------------------------------------------
# 모드 2: 문항 관리 (1/2교시 분리 및 기존 입력 폼 전체 유지)
# ---------------------------------------------------------
else:
    st.header("🛠️ 문항 관리 및 엑셀 표 도우미")
    all_df = st.session_state.df
    sel_sess = st.radio("관리할 교시 선택", ["1교시 (80문항)", "2교시 (70문항)"], horizontal=True)
    
    # 교시 필터링
    target_df = all_df[all_df['id'] < 200] if "1교시" in sel_sess else all_df[all_df['id'] >= 200]
    
    q_idx = st.selectbox("수정할 문항 선택", target_df.index, format_func=lambda x: f"{int(all_df.loc[x, 'id']) % 100}번 문제")
    st.divider()
    
    df = all_df.copy() # 작업용 카피
    
    # 🌟 기존 코드의 3개 탭 구성 유지 + 엑셀 도우미 포함
    tab1, tab2, tab3 = st.tabs(["📄 문제 내용 및 사례(표)", "🔢 보기 및 이미지 업로드", "💡 엑셀 표 붙여넣기 도우미"])

    with tab1:
        c1, c2 = st.columns([2, 1])
        with c1:
            df.at[q_idx, 'subject'] = st.text_input("과목명", value=clean_val(df.loc[q_idx, 'subject']), key=f"s_{q_idx}")
            df.at[q_idx, 'question'] = st.text_area("문제 지문", value=clean_val(df.loc[q_idx, 'question']), height=100, key=f"q_{q_idx}")
            df.at[q_idx, 'case_box'] = st.text_area("사례 박스 (표가 들어가는 곳)", value=clean_val(df.loc[q_idx, 'case_box']), height=150, key=f"c_{q_idx}")
        with c2:
            st.write("🖼️ 메인 문제 이미지")
            m_f = st.file_uploader("이미지 선택", type=['png','jpg','jpeg'], key=f"m_{q_idx}")
            if m_f:
                with open(os.path.join(IMAGE_DIR, m_f.name), "wb") as f: f.write(m_f.getbuffer())
                df.at[q_idx, 'img'] = f"images/{m_f.name}:C"
            if st.button("이미지 삭제", key=f"md_{q_idx}"): df.at[q_idx, 'img'] = ""; st.rerun()

    with tab2:
        df.at[q_idx, 'answer'] = st.number_input("정답 (1-5)", 1, 5, value=int(float(clean_val(df.loc[q_idx, 'answer']) or 1)))
        st.divider()
        for i in range(1, 6):
            col_t, col_i = st.columns([2, 1])
            df.at[q_idx, f'option{i}'] = col_t.text_input(f"보기 {i} 텍스트", value=clean_val(df.loc[q_idx, f'option{i}']), key=f"ot{i}_{q_idx}")
            o_f = col_i.file_uploader(f"보기 {i} 이미지", type=['png','jpg','jpeg'], key=f"ou{i}_{q_idx}")
            if o_f:
                with open(os.path.join(IMAGE_DIR, o_f.name), "wb") as f: f.write(o_f.getbuffer())
                df.at[q_idx, f'opt_img{i}'] = f"images/{o_f.name}"
            st.markdown("---")

    with tab3:
        st.subheader("📊 엑셀 표 → 사례 박스 변환 도우미")
        st.write("엑셀의 표 영역을 복사(Ctrl+C)해서 아래에 붙여넣으세요.")
        excel_input = st.text_area("여기에 붙여넣기(Ctrl+V)", height=150)
        if excel_input:
            lines = excel_input.strip().split('\n')
            md_table = ""
            for line in lines:
                cells = line.split('\t')
                md_table += "| " + " | ".join(cells) + " |\n"
            st.code(md_table, language="text")
            if st.button("이 표 형식을 사례 박스에 즉시 적용하기"):
                df.at[q_idx, 'case_box'] = md_table
                st.success("적용되었습니다! '문제 내용' 탭에서 확인하세요.")

    if st.button("💾 이 문항 최종 저장하기", use_container_width=True):
        st.session_state.df = df
        df.to_csv(DB_FILE, index=False)
        st.success("저장 완료!")
        st.rerun()
