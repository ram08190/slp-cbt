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

mode = st.sidebar.radio("메뉴 선택", ["📝 시험 시작", "🛠️ 문항 관리"])

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
            concept_db[f"Q_{real_id:03d}"] = {"title": clean_val(row.get('concept_title', '')), "point": clean_val(row.get('concept_point', ''))}
        except: continue

    if os.path.exists(HTML_FILE):
        with open(HTML_FILE, "r", encoding="utf-8") as f:
            base_html = f.read()
        
        # OMR 카드 가독성을 위한 스타일 및 로직 주입
        # 푼 문제는 배경색을 입히는 스크립트가 자동화.html에 있다고 가정하거나, 아래에서 강제 주입합니다.
        data_inject = f"""
        <script>
            window.QUESTIONS_S1 = {json.dumps(s1_list, ensure_ascii=False)};
            window.QUESTIONS_S2 = {json.dumps(s2_list, ensure_ascii=False)};
            window.CONCEPT_DATABASE = {json.dumps(concept_db, ensure_ascii=False)};
            
            // OMR 상태 업데이트 함수 (푼 문제 표시용)
            function updateOMRStatus() {{
                const omrButtons = document.querySelectorAll('.omr-item'); // OMR 번호 버튼들
                omrButtons.forEach(btn => {{
                    const qIdx = btn.getAttribute('data-id');
                    if (window.userAnswers && window.userAnswers[qIdx]) {{
                        btn.style.backgroundColor = '#007bff'; // 푼 문제는 파란색
                        btn.style.color = 'white';
                    }} else {{
                        btn.style.backgroundColor = ''; 
                        btn.style.color = '';
                    }}
                }});
            }}
        </script>
        """
        final_html = base_html.replace('<script src="questions1.js"></script>', '').replace('<script src="questions2.js"></script>', '').replace('<script src="database.js"></script>', data_inject)
        st.components.v1.html(final_html, height=1200, scrolling=True)

else:
    st.header("🛠️ 문항 관리 및 엑셀 표 도우미")
    all_df = st.session_state.df
    sel_sess = st.radio("관리할 교시 선택", ["1교시", "2교시"], horizontal=True)
    target_df = all_df[all_df['id'] < 200] if "1교시" in sel_sess else all_df[all_df['id'] >= 200]
    q_idx = st.selectbox("수정할 문항 선택", target_df.index, format_func=lambda x: f"{int(all_df.loc[x, 'id']) % 100}번 문제")
    
    df = all_df.copy()
    tab1, tab2, tab3 = st.tabs(["📄 문제 & 사례(표)", "🔢 보기 & 이미지", "💡 엑셀 표 붙여넣기 도우미"])

    with tab1:
        df.at[q_idx, 'subject'] = st.text_input("과목명", value=clean_val(df.loc[q_idx, 'subject']), key=f"s_{q_idx}")
        df.at[q_idx, 'question'] = st.text_area("문제 지문", value=clean_val(df.loc[q_idx, 'question']), key=f"q_{q_idx}")
        df.at[q_idx, 'case_box'] = st.text_area("사례 박스", value=clean_val(df.loc[q_idx, 'case_box']), height=200, key=f"c_{q_idx}")
        
    with tab2:
        c1, c2 = st.columns(2)
        with c1:
            st.write("🖼️ 메인 이미지")
            m_f = st.file_uploader("업로드", type=['png','jpg','jpeg'], key=f"m_{q_idx}")
            if m_f:
                with open(os.path.join(IMAGE_DIR, m_f.name), "wb") as f: f.write(m_f.getbuffer())
                df.at[q_idx, 'img'] = f"images/{m_f.name}:C"
        with c2:
            df.at[q_idx, 'answer'] = st.number_input("정답", 1, 5, value=int(float(clean_val(df.loc[q_idx, 'answer']) or 1)))
        
        for i in range(1, 6):
            c_t, c_u = st.columns([2, 1])
            df.at[q_idx, f'option{i}'] = c_t.text_input(f"보기 {i}", value=clean_val(df.loc[q_idx, f'option{i}']), key=f"ot{i}_{q_idx}")
            o_f = c_u.file_uploader(f"보기{i}이미지", type=['png','jpg','jpeg'], key=f"ou{i}_{q_idx}")
            if o_f:
                with open(os.path.join(IMAGE_DIR, o_f.name), "wb") as f: f.write(o_f.getbuffer())
                df.at[q_idx, f'opt_img{i}'] = f"images/{o_f.name}"

    with tab3:
        st.subheader("📊 엑셀 표 → 마크다운 변환")
        excel_paste = st.text_area("엑셀에서 복사한 내용을 붙여넣으세요")
        if excel_paste:
            lines = excel_paste.strip().split('\n')
            markdown_table = ""
            for line in lines:
                cells = line.split('\t')
                markdown_table += "| " + " | ".join(cells) + " |\n"
            st.code(markdown_table)
            if st.button("사례 박스에 적용"):
                df.at[q_idx, 'case_box'] = markdown_table
                st.success("적용 완료!")

    if st.button("💾 최종 저장하기", use_container_width=True):
        st.session_state.df = df
        df.to_csv(DB_FILE, index=False)
        st.success("저장되었습니다!")
        st.rerun()
