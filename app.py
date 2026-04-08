import streamlit as st
import pandas as pd
import json
import os

# 1. 페이지 설정
st.set_page_config(page_title="언어재활사 통합 CBT 시스템", layout="wide")

DB_FILE = "quiz_db.csv"

# 2. 데이터 로드 함수 (필요한 모든 컬럼 보장)
def load_data():
    if os.path.exists(DB_FILE):
        df = pd.read_csv(DB_FILE)
        # 통합 시스템에 필요한 컬럼들 자동 생성
        cols = [
            "id", "session", "subject", "question", "case_box", "answer", 
            "option1", "option2", "option3", "option4", "option5",
            "img", "opt_img1", "opt_img2", "opt_img3", "opt_img4", "opt_img5",
            "concept_title", "concept_point", "concept_mindmap", "concept_video"
        ]
        for col in cols:
            if col not in df.columns: df[col] = ""
        return df
    else:
        return pd.DataFrame(columns=["id", "session", "subject", "question", "case_box", "answer", "option1", "option2", "option3", "option4", "option5"])

if 'df' not in st.session_state:
    st.session_state.df = load_data()

# 3. 사이드바 메뉴
mode = st.sidebar.radio("메뉴 선택", ["📝 시험 시작 (통합 시스템)", "🛠️ 문항 및 오답 DB 관리"])

# ---------------------------------------------------------
# 모드 1: 시험 시작 (제공해주신 고성능 HTML 시스템 적용)
# ---------------------------------------------------------
if mode == "📝 시험 시작 (통합 시스템)":
    df = st.session_state.df
    
    # 데이터를 HTML 변수 형식으로 변환
    s1_list = []
    s2_list = []
    concept_db = {}

    for _, row in df.iterrows():
        q_id = int(row['id'])
        # 문제 객체 생성
        q_obj = {
            "id": q_id,
            "subject": str(row['subject']),
            "text": str(row['question']),
            "passage": str(row['case_box']) if pd.notna(row['case_box']) else "",
            "answer": int(float(row['answer'])) if row['answer'] != "" else 1,
            "img": str(row['img']) if pd.notna(row['img']) else "",
            "options": [
                {"text": str(row['option1']), "img": str(row['opt_img1'])},
                {"text": str(row['option2']), "img": str(row['opt_img2'])},
                {"text": str(row['option3']), "img": str(row['opt_img3'])},
                {"text": str(row['option4']), "img": str(row['opt_img4'])},
                {"text": str(row['option5']), "img": str(row['opt_img5'])}
            ]
        }
        
        # 교시 구분
        if str(row['session']) == "2": 
            s2_list.append(q_obj)
        else: 
            s1_list.append(q_obj)

        # 오답 분석 데이터베이스 생성 (파이썬 zfill 사용)
        f_id = "Q_" + str(q_id).zfill(3)
        concept_db[f_id] = {
            "title": str(row['concept_title']),
            "point": str(row['concept_point']),
            "mindmap": str(row['concept_mindmap']),
            "video": str(row['concept_video'])
        }

    # JSON 주입
    s1_json = json.dumps(s1_list, ensure_ascii=False)
    s2_json = json.dumps(s2_list, ensure_ascii=False)
    db_json = json.dumps(concept_db, ensure_ascii=False)

    # 제공해주신 HTML 코드 (데이터 부분만 변수로 교체)
    # 아래 f-string 내부의 {s1_json}, {s2_json}, {db_json}이 핵심입니다.
    full_html = f"""
    {open("자동화.html", "r", encoding="utf-8").read().replace('<script src="questions1.js"></script>', f'<script>window.QUESTIONS_S1 = {s1_json};</script>').replace('<script src="questions2.js"></script>', f'<script>window.QUESTIONS_S2 = {s2_json};</script>').replace('<script src="database.js"></script>', f'<script>window.CONCEPT_DATABASE = {db_json};</script>')}
    """
    
    import streamlit.components.v1 as components
    components.html(full_html, height=900, scrolling=False)

# ---------------------------------------------------------
# 모드 2: 관리 도구 (문제 + 오답 분석 데이터 한꺼번에 수정)
# ---------------------------------------------------------
else:
    st.header("🛠️ 통합 데이터 관리")
    df = st.session_state.df

    with st.expander("➕ 새 문항 추가", expanded=False):
        # ... (이전 답변의 추가 양식과 동일하되 오답 DB 컬럼만 추가하면 됩니다)
        pass

    st.subheader("📝 문항 상세 수정")
    idx = st.selectbox("수정할 문항", df.index, format_func=lambda x: f"{df.loc[x, 'id']}번 ({df.loc[x, 'subject']})")
    
    tab1, tab2, tab3 = st.tabs(["기본 정보", "보기 및 이미지", "오답 분석(Database)"])
    
    with tab1:
        c1, c2, c3 = st.columns(3)
        df.at[idx, 'id'] = c1.number_input("ID", value=int(df.loc[idx, 'id']))
        df.at[idx, 'session'] = c2.selectbox("교시", ["1", "2"], index=0 if str(df.loc[idx, 'session'])=="1" else 1)
        df.at[idx, 'subject'] = c3.text_input("과목명", value=df.loc[idx, 'subject'])
        df.at[idx, 'question'] = st.text_area("문제 지문", value=df.loc[idx, 'question'])
        df.at[idx, 'case_box'] = st.text_area("사례(표 등)", value=df.loc[idx, 'case_box'], height=200)

    with tab2:
        # 보기와 이미지 경로 입력
        st.info("이미지 옵션 예시: test.png:300X200:C (300x200 크기, 중앙 정렬)")
        # ... (생략: 각 보기별 텍스트 및 이미지 입력 필드)

    with tab3:
        st.subheader("오답 노트 및 해설 데이터")
        df.at[idx, 'concept_title'] = st.text_input("핵심 개념 타이틀", value=df.loc[idx, 'concept_title'])
        df.at[idx, 'concept_point'] = st.text_area("출제 포인트/해설", value=df.loc[idx, 'concept_point'])
        df.at[idx, 'concept_mindmap'] = st.text_input("마인드맵(이미지 경로 또는 태그/구분)", value=df.loc[idx, 'concept_mindmap'])
        df.at[idx, 'concept_video'] = st.text_input("유튜브 링크 또는 MP4 경로", value=df.loc[idx, 'concept_video'])

    if st.button("💾 모든 변경사항 저장"):
        df.to_csv(DB_FILE, index=False)
        st.success("데이터가 통합 시스템에 반영되었습니다!")
        st.rerun()
