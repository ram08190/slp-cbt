import streamlit as st
import pandas as pd
import json
import os

# 1. 페이지 설정
st.set_page_config(page_title="언어재활사 2급 통합 CBT", layout="wide")

DB_FILE = "quiz_db.csv"
HTML_FILE = "자동화.html"
IMAGE_DIR = "images"

# 이미지 폴더 생성
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
        
        # ID 안전 변환
        try: df['id'] = df['id'].astype(int)
        except: df['id'] = pd.to_numeric(df['id'], errors='coerce').fillna(0).astype(int)
            
        existing_ids = df['id'].tolist()
        missing_ids = [i for i in all_target_ids if i not in existing_ids]
        
        # 부족한 행 추가
        if missing_ids:
            new_rows = []
            for m_id in missing_ids:
                row = {col: "" for col in required_cols}
                row["id"] = m_id
                row["session"] = "1" if m_id < 200 else "2"
                new_rows.append(row)
            df = pd.concat([df, pd.DataFrame(new_rows)], ignore_index=True)
        
        # 유효한 체계만 남기고 정리
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
            # 표시 번호 (101->1, 201->1)
            display_id = real_id % 100
            
            q_obj = {
                "id": display_id,
                "subject": clean_val(row.get('subject', '')),
                "text": clean_val(row.get('question', '')),
                "passage": clean_val(row.get('case_box', '')),
                "answer": int(float(clean_val(row.get('answer', 1)) or 1)),
                "img": clean_val(row.get('img', '')),
                # 🌟 보기별 텍스트와 이미지를 쌍으로 전달
                "options": [
                    {
                        "text": clean_val(row.get(f'option{i}', '')), 
                        "img": clean_val(row.get(f'opt_img{i}', ''))
                    } for i in range(1, 6)
                ]
            }
            if real_id < 200: s1_list.append(q_obj)
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
        
        # 스크립트 강제 주입 방식 (가장 안전)
        data_inject = f"""
        <script>
            window.QUESTIONS_S1 = {json.dumps(s1_list, ensure_ascii=False)};
            window.QUESTIONS_S2 = {json.dumps(s2_list, ensure_ascii=False)};
            window.CONCEPT_DATABASE = {json.dumps(concept_db, ensure_ascii=False)};
        </script>
        """
        final_html = base_html.replace('<script src="questions1.js"></script>', '').replace('<script src="questions2.js"></script>', '').replace('<script src="database.js"></script>', data_inject)
        st.components.v1.html(final_html, height=1200, scrolling=True)
    else:
        st.error(f"'{HTML_FILE}' 파일을 찾을 수 없습니다.")

# ---------------------------------------------------------
# 모드 2: 문항 관리 (1/2교시 분리 및 보기 이미지 복원)
# ---------------------------------------------------------
else:
    st.header("🛠️ 문항 및 이미지 관리 도구")
    all_df = st.session_state.df
    
    # 교시 분리 선택
    sel_sess = st.radio("관리할 교시 선택", ["1교시 (80문항)", "2교시 (70문항)"], horizontal=True)
    
    # 데이터 필터링
    if "1교시" in sel_sess:
        target_df = all_df[all_df['id'] < 200]
    else:
        target_df = all_df[all_df['id'] >= 200]
    
    # 드롭다운 표시
    def format_func(idx):
        r_id = int(all_df.loc[idx, 'id'])
        d_id = r_id % 100
        return f"{d_id}번 문제"

    q_idx = st.selectbox("수정할 문항 선택", target_df.index, format_func=format_func)
    
    # (수정 중인 문제 정보 표시)
    r_id = int(all_df.loc[q_idx, 'id'])
    st.info(f"👉 수정 중: {'1교시' if r_id < 200 else '2교시'} {r_id % 100}번")
    st.divider()
    
    df = all_df.copy() # 편집용 복사본
    tab1, tab2 = st.tabs(["1. 문제 내용 및 메인 이미지", "2. 보기 및 보기 이미지"])

    with tab1:
        c1, c2 = st.columns([2, 1])
        with c1:
            df.at[q_idx, 'subject'] = st.text_input("과목명", value=clean_val(df.loc[q_idx, 'subject']), key=f"s_{q_idx}")
            df.at[q_idx, 'question'] = st.text_area("문제 지문", value=clean_val(df.loc[q_idx, 'question']), height=100, key=f"q_{q_idx}")
            df.at[q_idx, 'case_box'] = st.text_area("사례 박스 (|로 표 작성)", value=clean_val(df.loc[q_idx, 'case_box']), key=f"c_{q_idx}")
            df.at[q_idx, 'answer'] = st.number_input("정답 (1-5)", 1, 5, value=int(float(clean_val(df.loc[q_idx, 'answer']) or 1)), key=f"a_{q_idx}")
        
        with c2:
            st.write("🖼️ 메인 이미지")
            m_file = st.file_uploader("사진 업로드", type=['png','jpg','jpeg'], key=f"m_img_{q_idx}")
            if m_file:
                with open(os.path.join(IMAGE_DIR, m_file.name), "wb") as f: f.write(m_file.getbuffer())
                df.at[q_idx, 'img'] = f"images/{m_file.name}:C" # 자동 중앙정렬
                st.success("업로드됨!")
            if st.button("이미지 삭제", key=f"m_del_{q_idx}"): df.at[q_idx, 'img'] = ""; st.rerun()

    with tab2:
        st.markdown("💡 **보기별 이미지**를 올리려면 각 보기 아래의 **[Browse files]**를 누르세요.")
        for i in range(1, 6):
            col_t, col_i = st.columns([2, 1])
            with col_t:
                # 보기 텍스트
                df.at[q_idx, f'option{i}'] = st.text_input(f"보기 {i} 텍스트", value=clean_val(df.loc[q_idx, f'option{i}']), key=f"opt_t{i}_{q_idx}")
            
            with col_i:
                # 🌟 보기별 이미지 업로드 (복원됨)
                o_file = st.file_uploader(f"보기 {i} 이미지 업로드", type=['png','jpg','jpeg'], key=f"opt_u{i}_{q_idx}")
                if o_file:
                    with open(os.path.join(IMAGE_DIR, o_file.name), "wb") as f: f.write(o_file.getbuffer())
                    df.at[q_idx, f'opt_img{i}'] = f"images/{o_file.name}" # 자동정렬 옵션 없음
                    st.info(f"업로드 완료")
                if st.button(f"보기 {i} 이미지 삭제", key=f"opt_d{i}_{q_idx}"): df.at[q_idx, f'opt_img{i}'] = ""; st.rerun()
            st.markdown("---")

    if st.button("💾 이 문항 저장하기", use_container_width=True):
        st.session_state.df = df
        df.to_csv(DB_FILE, index=False)
        st.success("데이터베이스에 저장되었습니다! 시험 시작 메뉴에서 확인하세요.")
        st.rerun()
