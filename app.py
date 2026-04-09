import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import json
import os
import re
import time

# 1. 페이지 설정
st.set_page_config(page_title="언어재활사 2급 통합 CBT", layout="wide")

# 🌟 구글 시트 연결
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        # 구글 시트에서 데이터 읽기 (캐시 없음)
        df = conn.read(ttl=0)
        if df is None or df.empty:
            return pd.DataFrame(columns=['id', 'subject', 'question', 'case_box', 'img', 'option1', 'option2', 'option3', 'option4', 'option5', 'answer'])
        
        # ID와 정답을 숫자로 변환
        df['id'] = pd.to_numeric(df['id'], errors='coerce').fillna(0).astype(int)
        df['answer'] = pd.to_numeric(df['answer'], errors='coerce').fillna(1).astype(int)
        return df.sort_values('id').reset_index(drop=True)
    except Exception as e:
        st.error(f"시트 연결 오류: {e}")
        return pd.DataFrame()

# 세션 상태 초기화
if 'df' not in st.session_state:
    st.session_state.df = load_data()

def clean_val(x):
    if pd.isna(x): return ""
    return str(x).strip()

# 🖼️ 구글 드라이브 이미지 변환 함수
def get_display_image(url):
    if not url or "http" not in str(url): return ""
    if "drive.google.com" in url:
        match = re.search(r'file/d/(.*?)/', url)
        if match:
            return f"https://drive.google.com/uc?export=view&id={match.group(1)}"
    return url

# 사이드바 메뉴
mode = st.sidebar.radio("메뉴 선택", ["📝 시험 시작", "🛠️ 문항 관리"])

# ---------------------------------------------------------
# 모드 1: 시험 시작 (HTML CBT 연동)
# ---------------------------------------------------------
if mode == "📝 시험 시작":
    st.title("📝 언어재활사 2급 실전 CBT")
    df = st.session_state.df
    s1_list, s2_list = [], []
    
    for _, row in df.iterrows():
        try:
            rid = int(row['id'])
            q_obj = {
                "id": rid % 100,
                "subject": clean_val(row['subject']),
                "text": clean_val(row['question']),
                "passage": clean_val(row['case_box']),
                "answer": int(row['answer']),
                "img": get_display_image(clean_val(row['img'])),
                "options": [{"text": clean_val(row[f'option{i}'])} for i in range(1, 6)]
            }
            if 100 < rid < 200: s1_list.append(q_obj)
            elif rid > 200: s2_list.append(q_obj)
        except: continue

    # HTML 파일 로드 및 데이터 주입
    if os.path.exists("자동화.html"):
        with open("자동화.html", "r", encoding="utf-8") as f:
            base_html = f.read()
        
        payload = json.dumps({"s1": s1_list, "s2": s2_list}, ensure_ascii=False)
        inject = f"""
        <script id='data' type='application/json'>{payload}</script>
        <script>
            const d = JSON.parse(document.getElementById('data').textContent);
            window.QUESTIONS_S1 = d.s1;
            window.QUESTIONS_S2 = d.s2;
            setTimeout(() => {{ if(window.render) window.render(); }}, 500);
        </script>
        """
        st.components.v1.html(base_html.replace('</body>', inject + '</body>'), height=1000, scrolling=True)
    else:
        st.error("자동화.html 파일을 찾을 수 없습니다.")

# ---------------------------------------------------------
# 모드 2: 문항 관리
# ---------------------------------------------------------
elif mode == "🛠️ 문항 관리":
    st.header("🛠️ 문항 관리 (Google Sheets)")
    all_df = st.session_state.df
    
    c1, c2 = st.columns(2)
    with c1:
        sel_sess = st.selectbox("교시 선택", ["1교시 (101-180)", "2교시 (201-270)"])
    with c2:
        start_id = 101 if "1교시" in sel_sess else 201
        sel_num = st.selectbox("문항 선택", range(start_id, start_id + 80), format_func=lambda x: f"{x % 100}번")

    q_row = all_df[all_df['id'] == sel_num]
    if q_row.empty:
        # 데이터가 없으면 새 행 생성
        new_data = {col: "" for col in all_df.columns}
        new_data['id'] = sel_num
        all_df = pd.concat([all_df, pd.DataFrame([new_data])], ignore_index=True)
        q_idx = all_df.index[-1]
    else:
        q_idx = q_row.index[0]

    tab1, tab2 = st.tabs(["📄 문제/이미지 편집", "🔢 정답/보기 편집"])
    
    with tab1:
        all_df.at[q_idx, 'subject'] = st.text_input("과목명", clean_val(all_df.loc[q_idx, 'subject']))
        all_df.at[q_idx, 'question'] = st.text_area("문제 지문", clean_val(all_df.loc[q_idx, 'question']))
        all_df.at[q_idx, 'case_box'] = st.text_area("사례 박스 (마크다운 표)", clean_val(all_df.loc[q_idx, 'case_box']), height=150)
        all_df.at[q_idx, 'img'] = st.text_input("이미지 구글 드라이브 링크", clean_val(all_df.loc[q_idx, 'img']))
        
        img_url = get_display_image(all_df.loc[q_idx, 'img'])
        if img_url: st.image(img_url, width=300)

    with tab2:
        all_df.at[q_idx, 'answer'] = st.number_input("정답 (1-5)", 1, 5, int(all_df.loc[q_idx, 'answer']))
        for i in range(1, 6):
            all_df.at[q_idx, f'option{i}'] = st.text_input(f"보기 {i}", clean_val(all_df.loc[q_idx, f'option{i}']))

    st.divider()
    if st.button("💾 이 문항 구글 시트에 즉시 저장", use_container_width=True):
        conn.update(data=all_df)
        st.session_state.df = all_df
        st.success("✅ 구글 시트에 저장되었습니다!")
        time.sleep(1)
        st.rerun()
