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
        # 구글 시트 읽기 (캐시 0초)
        df = conn.read(ttl=0)
        if df is None or df.empty:
            return pd.DataFrame()
        
        # 데이터 타입을 문자로 통일 (TypeError 방지)
        df = df.astype(str)
        # ID를 숫자로 변환하여 정렬
        df['id'] = pd.to_numeric(df['id'], errors='coerce').fillna(0).astype(int)
        return df.sort_values('id').reset_index(drop=True)
    except Exception as e:
        st.error(f"시트 로드 오류: {e}")
        return pd.DataFrame()

if 'df' not in st.session_state:
    st.session_state.df = load_data()

def clean_val(x):
    if pd.isna(x) or str(x).lower() in ['nan', 'none']: return ""
    return str(x).strip()

# 🖼️ 구글 드라이브 링크 -> 이미지 직링크 변환 함수
def get_display_image(url):
    if not url or "http" not in str(url): return ""
    if "drive.google.com" in url:
        # 링크에서 파일 ID 추출
        match = re.search(r'file/d/(.*?)/', url)
        if match:
            return f"https://drive.google.com/uc?export=view&id={match.group(1)}"
    return url

mode = st.sidebar.radio("메뉴 선택", ["📝 시험 시작", "🛠️ 문항 관리"])

# ---------------------------------------------------------
# 모드 1: 시험 시작 (구글 시트 데이터 -> HTML 시험지)
# ---------------------------------------------------------
if mode == "📝 시험 시작":
    st.header("📝 실전 CBT 시험장")
    df = st.session_state.df
    s1_list, s2_list = [], []
    
    for _, row in df.iterrows():
        try:
            rid = int(row['id'])
            # 시험지에 보낼 문항 객체 생성
            q_obj = {
                "id": rid % 100,
                "subject": clean_val(row.get('subject')),
                "text": clean_val(row.get('question')),
                "passage": clean_val(row.get('case_box')),
                "answer": int(float(clean_val(row.get('answer', 1)))),
                "img": get_display_image(clean_val(row.get('img'))),
                "options": [
                    {"text": clean_val(row.get(f'option{i}'))} for i in range(1, 6)
                ]
            }
            if 100 < rid < 200: s1_list.append(q_obj)
            elif rid > 200: s2_list.append(q_obj)
        except: continue

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

# ---------------------------------------------------------
# 모드 2: 문항 관리
# ---------------------------------------------------------
elif mode == "🛠️ 문항 관리":
    st.header("🛠️ 문항 관리 센터")
    all_df = st.session_state.df
    
    col_s, col_n = st.columns(2)
    sel_sess = col_s.selectbox("교시 선택", ["1교시 (101~)", "2교시 (201~)"])
    start_id = 101 if "1교시" in sel_sess else 201
    sel_num = col_n.selectbox("문항 선택", range(start_id, start_id+80), format_func=lambda x: f"{x%100}번")

    # 해당 ID의 행 찾기 없으면 생성
    idx_list = all_df.index[all_df['id'] == sel_num].tolist()
    if not idx_list:
        new_row = {c: "" for c in all_df.columns}
        new_row['id'] = sel_num
        all_df = pd.concat([all_df, pd.DataFrame([new_row])], ignore_index=True)
        q_idx = all_df.index[-1]
    else:
        q_idx = idx_list[0]

    tab1, tab2, tab3 = st.tabs(["📄 지문/이미지", "🔢 보기/정답", "💡 엑셀 표 편집"])
    
    with tab1:
        all_df.at[q_idx, 'subject'] = st.text_input("과목명", clean_val(all_df.loc[q_idx, 'subject']), key=f"s_{sel_num}")
        all_df.at[q_idx, 'question'] = st.text_area("문제 지문", clean_val(all_df.loc[q_idx, 'question']), key=f"q_{sel_num}")
        all_df.at[q_idx, 'img'] = st.text_input("이미지 주소 (구글 드라이브 공유 링크)", clean_val(all_df.loc[q_idx, 'img']), key=f"i_{sel_num}")
        img_url = get_display_image(all_df.at[q_idx, 'img'])
        if img_url: st.image(img_url, width=300)

    with tab2:
        # 정답 안전 변환
        try:
            curr_ans = int(float(clean_val(all_df.loc[q_idx, 'answer']) or 1))
        except: curr_ans = 1
        all_df.at[q_idx, 'answer'] = st.number_input("정답 (1-5)", 1, 5, curr_ans, key=f"a_{sel_num}")
        for i in range(1, 6):
            all_df.at[q_idx, f'option{i}'] = st.text_input(f"보기 {i}", clean_val(all_df.loc[q_idx, f'option{i}']), key=f"o{i}_{sel_num}")

    with tab3:
        # 기존 표 편집 로직 유지 (생략 가능하나 사용자 편의 위해 포함)
        all_df.at[q_idx, 'case_box'] = st.text_area("사례 박스 마크다운", clean_val(all_df.loc[q_idx, 'case_box']), height=200, key=f"cb_{sel_num}")
        if all_df.at[q_idx, 'case_box']: st.markdown(all_df.at[q_idx, 'case_box'], unsafe_allow_html=True)

    st.divider()
    if st.button("💾 이 모든 내용을 구글 시트에 영구 저장하기", use_container_width=True):
        conn.update(data=all_df)
        st.session_state.df = all_df
        st.success("🎉 구글 시트에 저장이 완료되었습니다!")
        time.sleep(1); st.rerun()
