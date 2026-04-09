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

# [데이터 로드] 1교시 80 / 2교시 70 틀 고정
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
        existing_ids = df['id'].astype(int).tolist()
        missing_ids = [i for i in all_target_ids if i not in existing_ids]
        
        if missing_ids:
            new_rows = []
            for m_id in missing_ids:
                row = {col: "" for col in required_cols}
                row["id"] = m_id
                row["session"] = "1" if m_id < 200 else "2"
                new_rows.append(row)
            df = pd.concat([df, pd.DataFrame(new_rows)], ignore_index=True)
        
        df['id'] = df['id'].astype(int)
        df = df.sort_values(by='id').reset_index(drop=True)
        return df.astype(object)
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

# ---------------------------------------------------------
# 모드 1: 시험 시작
# ---------------------------------------------------------
if mode == "📝 시험 시작":
    df = st.session_state.df
    s1_list, s2_list, concept_db = [], [], {}

    for _, row in df.iterrows():
        try:
            real_id = int(row['id'])
            if 100 < real_id < 200:
                display_id = real_id - 100
                session_type = "1"
            elif real_id > 200:
                display_id = real_id - 200
                session_type = "2"
            else: continue

            # 임시 문구 없이 데이터 구성
            q_obj = {
                "id": display_id,
                "subject": clean_val(row.get('subject', '')),
                "text": clean_val(row.get('question', '')),
                "passage": clean_val(row.get('case_box', '')),
                "answer": int(float(clean_val(row.get('answer', 1)) or 1)),
                "img": clean_val(row.get('img', '')),
                "options": [
                    {"text": clean_val(row.get(f'option{i}', '')), "img": clean_val(row.get(f'opt_img{i}', ''))} 
                    for i in range(1, 6)
                ]
            }
            
            # 2교시 버튼이 활성화되려면 '내용이 있는 문제'가 최소 하나는 필요할 수 있습니다.
            # 데이터가 아예 없더라도 리스트에는 무조건 추가합니다.
            if session_type == "1": s1_list.append(q_obj)
            else: s2_list.append(q_obj)

            concept_db[f"Q_{real_id:03d}"] = {
                "title": clean_val(row.get('concept_title', '')),
                "point": clean_val(row.get('concept_point', '')),
                "mindmap": clean_val(row.get('concept_mindmap', '')),
                "video": clean_val(row.get('concept_video', ''))
            }
        except: continue

    if os.path.exists(HTML_FILE):
        with open(HTML_FILE, "r", encoding="utf-8") as f:
            base_html = f.read()
        
        # 🌟 핵심: HTML 내부의 데이터 주입부를 강제로 초기화
        data_script = f"""
        <script>
            window.QUESTIONS_S1 = {json.dumps(s1_list, ensure_ascii=False)};
            window.QUESTIONS_S2 = {json.dumps(s2_list, ensure_ascii=False)};
            window.CONCEPT_DATABASE = {json.dumps(concept_db, ensure_ascii=False)};
            
            // 자동화.html의 초기화 함수가 있다면 강제 호출 (필요시)
            if(window.initExam) window.initExam(); 
        </script>
        """
        
        final_html = base_html.replace('<script src="questions1.js"></script>', '')\
                              .replace('<script src="questions2.js"></script>', '')\
                              .replace('<script src="database.js"></script>', data_script)
        
        import streamlit.components.v1 as components
        components.html(final_html, height=1200, scrolling=True)

# ---------------------------------------------------------
# 모드 2: 문항 관리
# ---------------------------------------------------------
else:
    st.header("🛠️ 문항 관리 (201번부터 2교시)")
    df = st.session_state.df.astype(object)
    
    def format_func(idx):
        r_id = int(df.loc[idx, 'id'])
        sess = "1교시" if r_id < 200 else "2교시"
        d_id = r_id - 100 if r_id < 200 else r_id - 200
        return f"[{sess} {d_id}번] {str(df.loc[idx, 'question'])[:20]}"

    q_idx = st.selectbox("수정할 문항 선택", df.index, format_func=format_func)
    
    tab1, tab2, tab3 = st.tabs(["문제", "보기", "해설"])
    with tab1:
        df.at[q_idx, 'subject'] = st.text_input("과목명", value=clean_val(df.loc[q_idx, 'subject']), key=f"s_{q_idx}")
        df.at[q_idx, 'question'] = st.text_area("문제 지문", value=clean_val(df.loc[q_idx, 'question']), key=f"q_{q_idx}")
        df.at[q_idx, 'case_box'] = st.text_area("사례 박스", value=clean_val(df.loc[q_idx, 'case_box']), key=f"c_{q_idx}")
        m_file = st.file_uploader("이미지 업로드", type=['png','jpg','jpeg'], key=f"m_{q_idx}")
        if m_file:
            with open(os.path.join(IMAGE_DIR, m_file.name), "wb") as f: f.write(m_file.getbuffer())
            df.at[q_idx, 'img'] = f"images/{m_file.name}:C"

    with tab2:
        df.at[q_idx, 'answer'] = st.number_input("정답", 1, 5, value=int(float(clean_val(df.loc[q_idx, 'answer']) or 1)), key=f"a_{q_idx}")
        for i in range(1, 6):
            df.at[q_idx, f'option{i}'] = st.text_input(f"보기 {i}", value=clean_val(df.loc[q_idx, f'option{i}']), key=f"ot{i}_{q_idx}")

    with tab3:
        df.at[q_idx, 'concept_title'] = st.text_input("해설 타이틀", value=clean_val(df.loc[q_idx, 'concept_title']), key=f"ct_{q_idx}")

    if st.button("💾 저장하기", use_container_width=True):
        st.session_state.df = df
        df.to_csv(DB_FILE, index=False)
        st.success("저장 완료! 이제 시험 시작 메뉴에서 확인하세요.")
        st.rerun()
