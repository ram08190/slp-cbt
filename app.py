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
        df = conn.read(ttl=0)
        if df is None or df.empty:
            cols = ['id', 'subject', 'question', 'case_box', 'img', 'option1', 'option2', 'option3', 'option4', 'option5', 'answer']
            return pd.DataFrame(columns=cols)
        
        # 🌟 [핵심] 모든 열을 'object' 타입으로 강제 변환하여 데이터 타입 충돌 방지
        df = df.astype(object)
        
        # ID와 정답을 숫자로 변환하되 에러는 무시
        df['id'] = pd.to_numeric(df['id'], errors='coerce').fillna(0).astype(int)
        df.columns = [str(c).strip() for c in df.columns]
        return df.sort_values('id').reset_index(drop=True)
    except Exception as e:
        st.error(f"데이터 로드 오류: {e}")
        return pd.DataFrame()

if 'df' not in st.session_state:
    st.session_state.df = load_data()

all_df = st.session_state.df

def clean_val(x):
    if pd.isna(x) or str(x).lower() in ['nan', 'none']: return ""
    return str(x).strip()

# 🖼️ 이미지 안 나오는 문제 해결용 변환 함수 (더 강력한 버전)
def get_display_image(url):
    if not url or "http" not in str(url): return ""
    if "drive.google.com" in url:
        # 공유 링크에서 ID 추출 패턴 보강
        file_id = ""
        if "/file/d/" in url:
            file_id = url.split("/file/d/")[1].split("/")[0]
        elif "id=" in url:
            file_id = url.split("id=")[1].split("&")[0]
        
        if file_id:
            # 🌟 구글 드라이브 '직접 보기' 주소로 리턴
            return f"https://drive.google.com/uc?export=view&id={file_id}"
    return url

mode = st.sidebar.radio("메뉴 선택", ["📝 시험 시작", "🛠️ 문항 관리"])

# ---------------------------------------------------------
# 모드 1: 시험 시작
# ---------------------------------------------------------
if mode == "📝 시험 시작":
    st.header("📝 언어재활사 CBT")
    s1_list, s2_list = [], []
    for _, row in all_df.iterrows():
        try:
            rid = int(row['id'])
            q_obj = {
                "id": rid % 100,
                "subject": clean_val(row.get('subject')),
                "text": clean_val(row.get('question')),
                "passage": clean_val(row.get('case_box')),
                "answer": int(float(clean_val(row.get('answer', 1)))),
                "img": get_display_image(clean_val(row.get('img'))),
                "options": [{"text": clean_val(row.get(f'option{i}'))} for i in range(1, 6)]
            }
            if 100 < rid < 200: s1_list.append(q_obj)
            elif rid > 200: s2_list.append(q_obj)
        except: continue

    if os.path.exists("자동화.html"):
        with open("자동화.html", "r", encoding="utf-8") as f:
            base_html = f.read()
        payload = json.dumps({"s1": s1_list, "s2": s2_list}, ensure_ascii=False)
        inject = f"<script id='data' type='application/json'>{payload}</script><script>const d=JSON.parse(document.getElementById('data').textContent); window.QUESTIONS_S1=d.s1; window.QUESTIONS_S2=d.s2; setTimeout(()=>{{if(window.render)window.render();}},500);</script>"
        st.components.v1.html(base_html.replace('</body>', inject + '</body>'), height=1000, scrolling=True)

# ---------------------------------------------------------
# 모드 2: 문항 관리
# ---------------------------------------------------------
elif mode == "🛠️ 문항 관리":
    st.header("🛠️ 문항 관리 센터")
    
    col_s, col_n = st.columns(2)
    sel_sess = col_s.selectbox("교시 선택", ["1교시 (101~)", "2교시 (201~)"])
    start_id = 101 if "1교시" in sel_sess else 201
    sel_num = col_n.selectbox("문항 선택", range(start_id, start_id+80), format_func=lambda x: f"{x%100}번")

    # 행 찾기 및 생성
    idx_list = all_df.index[all_df['id'] == sel_num].tolist()
    if not idx_list:
        new_row = pd.Series({c: "" for c in all_df.columns})
        new_row['id'] = sel_num
        all_df.loc[len(all_df)] = new_row
        q_idx = all_df.index[-1]
    else:
        q_idx = idx_list[0]

    tab1, tab2 = st.tabs(["📄 지문/이미지", "🔢 보기/정답"])
    
    with tab1:
        # 🌟 .at 대신 .loc를 사용하고 데이터를 명시적으로 문자열로 처리
        all_df.loc[q_idx, 'subject'] = st.text_input("과목명", clean_val(all_df.loc[q_idx, 'subject']), key=f"s_{sel_num}")
        all_df.loc[q_idx, 'question'] = st.text_area("문제 지문", clean_val(all_df.loc[q_idx, 'question']), key=f"q_{sel_num}")
        all_df.loc[q_idx, 'img'] = st.text_input("이미지 주소", clean_val(all_df.loc[q_idx, 'img']), key=f"i_{sel_num}")
        
        img_url = get_display_image(all_df.loc[q_idx, 'img'])
        if img_url:
            st.image(img_url, width=400)
            st.caption("위 이미지가 시험지에 출력됩니다.")

    with tab2:
        try: curr_ans = int(float(clean_val(all_df.loc[q_idx, 'answer']) or 1))
        except: curr_ans = 1
        
        # 🌟 여기서 발생하는 TypeError를 막기 위해 값을 .loc로 할당
        res_ans = st.number_input("정답 (1-5)", 1, 5, curr_ans, key=f"a_{sel_num}")
        all_df.loc[q_idx, 'answer'] = res_ans
        
        for i in range(1, 6):
            all_df.loc[q_idx, f'option{i}'] = st.text_input(f"보기 {i}", clean_val(all_df.loc[q_idx, f'option{i}']), key=f"o{i}_{sel_num}")

    st.divider()
    if st.button("💾 모든 수정사항 구글 시트에 최종 저장하기", use_container_width=True):
        # 저장 전 다시 한번 타입 정리
        save_df = all_df.copy().astype(str)
        conn.update(data=save_df)
        st.session_state.df = all_df
        st.success("🎉 구글 시트에 저장이 완료되었습니다!")
        time.sleep(1); st.rerun()
