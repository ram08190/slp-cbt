import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime

# 1. 페이지 설정
st.set_page_config(page_title="언어재활사 2급 통합 CBT", layout="wide")

DB_FILE = "quiz_db.csv"
RESULT_FILE = "results.csv"
HTML_FILE = "자동화.html"
# 🌟 중요: Streamlit에서 이미지를 직접 접근하려면 리포지토리 최상단에 images 폴더가 있어야 합니다.
IMAGE_DIR = "images" 

if not os.path.exists(IMAGE_DIR): 
    os.makedirs(IMAGE_DIR)

def load_data():
    s1_ids = [100 + i for i in range(1, 81)]
    s2_ids = [200 + i for i in range(1, 71)]
    all_target_ids = s1_ids + s2_ids
    if os.path.exists(DB_FILE):
        df = pd.read_csv(DB_FILE, keep_default_na=False).astype(object)
        df['id'] = pd.to_numeric(df['id'], errors='coerce').fillna(0).astype(int)
        df = df[df['id'].isin(all_target_ids)]
        return df.sort_values('id').reset_index(drop=True).astype(object)
    else:
        return pd.DataFrame([{"id": i, "session": "1" if i < 200 else "2"} for i in all_target_ids])

if 'df' not in st.session_state: 
    st.session_state.df = load_data()

def clean_val(x):
    s = str(x).strip()
    return "" if s.lower() in ['nan', 'none', ''] else s

# 🌟 [경로 복구 함수] D드라이브 경로를 깃허브 상대 경로로 강제 전환
def fix_img_path(img_path):
    if not img_path: return ""
    # D:\사진\01.png:C -> 01.png
    file_name = img_path.replace("\\", "/").split('/')[-1].split(':')[0].strip()
    if file_name:
        # 깃허브/서버의 images/파일명 주소 반환
        return f"images/{file_name}"
    return ""

mode = st.sidebar.radio("메뉴 선택", ["📝 시험 시작", "🛠️ 문항 관리", "📊 성적 통계 센터"])

# ---------------------------------------------------------
# 모드 1: 시험 시작 (HTML 데이터 최소화로 TypeError 해결)
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
                "img": fix_img_path(clean_val(row.get('img', ''))), # 👈 Base64가 아닌 경로만 전달
                "options": [{"text": clean_val(row.get(f'option{i}', '')), "img": fix_img_path(clean_val(row.get(f'opt_img{i}', '')))} for i in range(1, 6)]
            }
            if real_id < 200: s1_list.append(q_obj)
            else: s2_list.append(q_obj)
        except: continue

    if os.path.exists(HTML_FILE):
        with open(HTML_FILE, "r", encoding="utf-8") as f:
            base_html = f.read()
        
        # 데이터 주입용 자바스크립트 생성
        inject_code = f"""
        <script>
            window.QUESTIONS_S1 = {json.dumps(s1_list, ensure_ascii=False)};
            window.QUESTIONS_S2 = {json.dumps(s2_list, ensure_ascii=False)};
            window.render();
        </script>
        """
        final_html = base_html.replace('</body>', f'{inject_code}</body>')
        
        # 🌟 핵심: key를 제거하고 HTML 데이터 용량을 줄여 TypeError 방지
        st.components.v1.html(final_html, height=1200, scrolling=True)

# ---------------------------------------------------------
# 모드 2: 문항 관리 (상세 수정 복구)
# ---------------------------------------------------------
elif mode == "🛠️ 문항 관리":
    st.header("🛠️ 문항 관리")
    all_df = st.session_state.df
    sel_sess = st.radio("교시", ["1교시", "2교시"], horizontal=True)
    target_df = all_df[all_df['id'] < 200] if "1교시" in sel_sess else all_df[all_df['id'] >= 200]
    q_idx = st.selectbox("문항 선택", target_df.index, format_func=lambda x: f"{int(all_df.loc[x, 'id']) % 100}번")
    
    tab1, tab2 = st.tabs(["📄 지문/사례/이미지", "🔢 보기/정답"])
    with tab1:
        all_df.at[q_idx, 'subject'] = st.text_input("과목명", clean_val(all_df.loc[q_idx, 'subject']), key=f"s_{q_idx}")
        all_df.at[q_idx, 'question'] = st.text_area("지문", clean_val(all_df.loc[q_idx, 'question']), key=f"q_{q_idx}")
        all_df.at[q_idx, 'case_box'] = st.text_area("사례", clean_val(all_df.loc[q_idx, 'case_box']), key=f"c_{q_idx}")
        m_f = st.file_uploader("이미지", type=['png','jpg','jpeg'], key=f"m_{q_idx}")
        if m_f:
            with open(os.path.join(IMAGE_DIR, m_f.name), "wb") as f: f.write(m_f.getbuffer())
            all_df.at[q_idx, 'img'] = f"images/{m_f.name}:C"
    with tab2:
        all_df.at[q_idx, 'answer'] = st.number_input("정답", 1, 5, int(float(clean_val(all_df.loc[q_idx, 'answer']) or 1)))
        for i in range(1, 6):
            all_df.at[q_idx, f'option{i}'] = st.text_input(f"보기 {i}", clean_val(all_df.loc[q_idx, f'option{i}']), key=f"o_{i}_{q_idx}")

    if st.button("💾 저장하기", use_container_width=True):
        all_df.to_csv(DB_FILE, index=False); st.success("저장 완료!"); st.rerun()

# ---------------------------------------------------------
# 모드 3: 성적 통계 센터 (복구)
# ---------------------------------------------------------
else:
    st.header("📊 성적 통계 센터")
    if os.path.exists(RESULT_FILE):
        rdf = pd.read_csv(RESULT_FILE)
        st.metric("총 응시 인원", f"{len(rdf)}명")
        st.line_chart(rdf['score'])
    else: st.info("기록이 없습니다.")
