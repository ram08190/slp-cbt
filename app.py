import streamlit as st
import pandas as pd
import json
import os

# 1. 페이지 설정
st.set_page_config(page_title="언어재활사 통합 CBT 관리시스템", layout="wide")

DB_FILE = "quiz_db.csv"
HTML_FILE = "자동화.html"

# 데이터 로드 및 필수 컬럼(표 파싱, 오답분석용) 보장 함수
def load_data():
    required_cols = [
        "id", "session", "subject", "question", "case_box", "answer", 
        "option1", "option2", "option3", "option4", "option5",
        "img", "opt_img1", "opt_img2", "opt_img3", "opt_img4", "opt_img5",
        "concept_title", "concept_point", "concept_mindmap", "concept_video"
    ]
    if os.path.exists(DB_FILE):
        df = pd.read_csv(DB_FILE)
        for col in required_cols:
            if col not in df.columns: df[col] = ""
        return df
    else:
        # 데이터가 없을 경우 140번까지 기본 틀 자동 생성
        initial_data = [{"id": i, "session": "1" if i<=70 else "2"} for i in range(1, 141)]
        df = pd.DataFrame(initial_data)
        for col in required_cols:
            if col not in df.columns: df[col] = ""
        return df

if 'df' not in st.session_state:
    st.session_state.df = load_data()

# 사이드바 메뉴
mode = st.sidebar.radio("메뉴 선택", ["📝 시험 시작 (통합 인터페이스)", "🛠️ 140문항 직접 수정/관리"])

# ---------------------------------------------------------
# 모드 1: 시험 시작 (자동화.html 엔진 사용)
# ---------------------------------------------------------
if mode == "📝 시험 시작 (통합 인터페이스)":
    df = st.session_state.df
    s1_list, s2_list, concept_db = [], [], {}

    for _, row in df.iterrows():
        try:
            if pd.isna(row['id']) or str(row['id']).strip() == "": continue
            q_id = int(float(row['id']))
            
            # 정답값 안전하게 정수로 변환
            raw_ans = str(row['answer']).strip()
            safe_ans = int(float(raw_ans)) if raw_ans and raw_ans.lower() != 'nan' else 1
            
            # 자동화.html의 JS 엔진이 요구하는 객체 구조로 변환
            q_obj = {
                "id": q_id,
                "subject": str(row.get('subject', '미지정')),
                "text": str(row.get('question', '')),
                "passage": str(row.get('case_box', '')), # 표(|) 파싱 보존
                "answer": safe_ans,
                "img": str(row.get('img', '')),
                "options": [
                    {"text": str(row.get('option1', '')), "img": str(row.get('opt_img1', ''))},
                    {"text": str(row.get('option2', '')), "img": str(row.get('opt_img2', ''))},
                    {"text": str(row.get('option3', '')), "img": str(row.get('opt_img3', ''))},
                    {"text": str(row.get('option4', '')), "img": str(row.get('opt_img4', ''))},
                    {"text": str(row.get('option5', '')), "img": str(row.get('opt_img5', ''))}
                ]
            }
            
            if str(row.get('session')) == "2": s2_list.append(q_obj)
            else: s1_list.append(q_obj)

            # 오답 분석용 CONCEPT_DATABASE 생성 (Q_001 형식)
            f_id = f"Q_{q_id:03d}"
            concept_db[f_id] = {
                "title": str(row.get('concept_title', '')),
                "point": str(row.get('concept_point', '')),
                "mindmap": str(row.get('concept_mindmap', '')),
                "video": str(row.get('concept_video', ''))
            }
        except: continue

    # HTML 템플릿 읽기 및 데이터 주입
    if os.path.exists(HTML_FILE):
        with open(HTML_FILE, "r", encoding="utf-8") as f:
            base_html = f.read()
        
        # 외부 JS 호출 태그를 파이썬의 최신 JSON 데이터로 치환
        final_html = base_html.replace(
            '<script src="questions1.js"></script>', 
            f'<script>window.QUESTIONS_S1 = {json.dumps(s1_list, ensure_ascii=False)};</script>'
        ).replace(
            '<script src="questions2.js"></script>', 
            f'<script>window.QUESTIONS_S2 = {json.dumps(s2_list, ensure_ascii=False)};</script>'
        ).replace(
            '<script src="database.js"></script>', 
            f'<script>window.CONCEPT_DATABASE = {json.dumps(concept_db, ensure_ascii=False)};</script>'
        )
        
        import streamlit.components.v1 as components
        components.html(final_html, height=900, scrolling=False)
    else:
        st.error(f"'{HTML_FILE}' 파일이 같은 폴더에 없습니다.")

# ---------------------------------------------------------
# 모드 2: 140문항 직접 수정/관리
# ---------------------------------------------------------
else:
    st.header("🛠️ 문항 및 오답분석 DB 관리")
    df = st.session_state.df

    # 수정할 문제 선택
    q_idx = st.selectbox("수정할 문항 선택", df.index, 
                         format_func=lambda x: f"[{df.loc[x, 'id']}번] {str(df.loc[x, 'question'])[:30]}...")

    tab1, tab2, tab3 = st.tabs(["1. 문제 및 사례(표)", "2. 보기 및 이미지 옵션", "3. 오답 분석 정보"])

    with tab1:
        c1, c2 = st.columns([1, 4])
        df.at[q_idx, 'session'] = c1.selectbox("교시", ["1", "2"], index=0 if str(df.loc[q_idx, 'session'])=="1" else 1)
        df.at[q_idx, 'subject'] = c2.text_input("과목명", value=df.loc[q_idx, 'subject'])
        df.at[q_idx, 'question'] = st.text_area("문제 지문", value=df.loc[q_idx, 'question'], height=100)
        df.at[q_idx, 'case_box'] = st.text_area("사례 박스 (표 작성 시 | 사용)", value=df.loc[q_idx, 'case_box'], height=200, help="예: |제목|제목|\n|내용|내용|")
        df.at[q_idx, 'img'] = st.text_input("메인 이미지 (파일명:옵션)", value=df.loc[q_idx, 'img'], placeholder="pic1.png:C")

    with tab2:
        # 1. 화면에 보여줄 숫자 입력창 (변수에 먼저 담습니다)
        try:
            current_ans_val = int(float(df.loc[q_idx, 'answer'] or 1))
        except:
            current_ans_val = 1
            
        new_ans_val = st.number_input("정답 번호 (1-5)", 1, 5, value=current_ans_val, key=f"ans_input_{q_idx}")
        
        # 2. 데이터프레임에 저장할 때는 문자열로 변환하여 에러 방지
        # df.at 대신 컬럼 전체의 타입을 object로 미리 바꿔주는 것이 더 안전합니다.
        df['answer'] = df['answer'].astype(object)
        df.at[q_idx, 'answer'] = str(new_ans_val)

        for i in range(1, 6):
            st.markdown(f"**보기 {i}**")
            col_t, col_i = st.columns([2, 1])
            df.at[q_idx, f'option{i}'] = col_t.text_input(f"보기 {i} 텍스트", value=str(df.loc[q_idx, f'option{i}']), key=f"t{i}_{q_idx}")
            df.at[q_idx, f'opt_img{i}'] = col_i.text_input(f"보기 {i} 이미지", value=str(df.loc[q_idx, f'opt_img{i}']), key=f"i{i}_{q_idx}")

    with tab3:
        st.info("시험 제출 후 표시될 오답 분석 데이터입니다.")
        df.at[q_idx, 'concept_title'] = st.text_input("개념 타이틀", value=df.loc[q_idx, 'concept_title'])
        df.at[q_idx, 'concept_point'] = st.text_area("출제 포인트", value=df.loc[q_idx, 'concept_point'])
        df.at[q_idx, 'concept_mindmap'] = st.text_input("마인드맵(이미지경로 또는 태그)", value=df.loc[q_idx, 'concept_mindmap'])
        df.at[q_idx, 'concept_video'] = st.text_input("영상(유튜브 링크/MP4)", value=df.loc[q_idx, 'concept_video'])

    if st.button("💾 현재 문항 저장하기", use_container_width=True):
        df.to_csv(DB_FILE, index=False)
        st.session_state.df = df
        st.success(f"{df.loc[q_idx, 'id']}번 문항 저장 완료!")
