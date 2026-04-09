import streamlit as st
import pandas as pd
import json
import os
import base64
import time
from datetime import datetime

# 1. 페이지 설정
st.set_page_config(page_title="언어재활사 2급 통합 CBT", layout="wide")

DB_FILE = "quiz_db.csv"
RESULT_FILE = "results.csv"
HTML_FILE = "자동화.html"
IMAGE_DIR = "images"

if not os.path.exists(IMAGE_DIR): 
    os.makedirs(IMAGE_DIR)

# 🖼️ 이미지 로더 (D드라이브 경로 무시 + 깃허브 images 폴더에서 강제 호출)
def get_image_data(img_path):
    if not img_path: return ""
    # D:\사진\01.png:C -> 01.png 파일명만 추출
    file_name = str(img_path).replace("\\", "/").split('/')[-1].split(':')[0].strip()
    target_path = os.path.join(IMAGE_DIR, file_name)
    
    if os.path.exists(target_path) and os.path.isfile(target_path):
        try:
            with open(target_path, "rb") as f:
                encoded = base64.b64encode(f.read()).decode('utf-8')
                return f"data:image/png;base64,{encoded}"
        except: return ""
    return ""

def load_data():
    if os.path.exists(DB_FILE):
        df = pd.read_csv(DB_FILE, keep_default_na=False).astype(object)
        # ID 순서대로 정렬
        if 'id' in df.columns:
            df['id'] = pd.to_numeric(df['id'], errors='coerce').fillna(0).astype(int)
            df = df.sort_values('id')
        return df
    return pd.DataFrame()

if 'df' not in st.session_state: 
    st.session_state.df = load_data()

def clean_val(x):
    s = str(x).strip().replace('"', '')
    return "" if s.lower() in ['nan', 'none', ''] else s

mode = st.sidebar.radio("메뉴 선택", ["📝 시험 시작", "🛠️ 문항 관리", "📊 성적 통계 센터"])

# ---------------------------------------------------------
# 모드 1: 시험 시작 (복구 완료!)
# ---------------------------------------------------------
if mode == "📝 시험 시작":
    df = st.session_state.df
    if df.empty:
        st.warning("데이터베이스(quiz_db.csv)가 비어있습니다.")
    else:
        s1_list, s2_list = [], []
        for _, row in df.iterrows():
            try:
                real_id = int(row['id'])
                q_obj = {
                    "id": real_id % 100,
                    "subject": clean_val(row.get('subject', '')),
                    "text": clean_val(row.get('question', '')),
                    "passage": clean_val(row.get('case_box', '')),
                    "answer": int(float(clean_val(row.get('answer', 1)) or 1)),
                    "img": get_image_data(clean_val(row.get('img', ''))), # 지문 사진
                    "options": [
                        {"text": clean_val(row.get(f'option{i}', '')), "img": get_image_data(clean_val(row.get(f'opt_img{i}', '')))} 
                        for i in range(1, 6)
                    ] # 보기 사진 포함
                }
                if real_id < 200: s1_list.append(q_obj)
                else: s2_list.append(q_obj)
            except: continue

        if os.path.exists(HTML_FILE):
            with open(HTML_FILE, "r", encoding="utf-8") as f:
                base_html = f.read()
            
            # 자바스크립트에 데이터 주입
            inject_code = f"""
            <script>
                window.QUESTIONS_S1 = {json.dumps(s1_list, ensure_ascii=False)};
                window.QUESTIONS_S2 = {json.dumps(s2_list, ensure_ascii=False)};
                setTimeout(() => {{ if(window.render) window.render(); }}, 500);
            </script>
            """
            final_html = base_html.replace('</body>', f'{inject_code}</body>')
            st.components.v1.html(final_html, height=1200, scrolling=True, key="cbt_viewer")
        else:
            st.error("자동화.html 파일이 없습니다. 깃허브에 업로드했는지 확인해주세요.")

# ---------------------------------------------------------
# 모드 2: 문항 관리 (실시간 편집기 포함)
# ---------------------------------------------------------
elif mode == "🛠️ 문항 관리":
    st.header("🛠️ 문항 관리 및 실시간 표 편집기")
    all_df = st.session_state.df
    q_idx = st.selectbox("수정 문항 선택", all_df.index, format_func=lambda x: f"{all_df.loc[x, 'id']}번")
    
    t1, t2, t3 = st.tabs(["📄 지문/이미지", "🔢 보기/정답", "💡 엑셀 표 실시간 편집기"])
    
    with t1:
        all_df.at[q_idx, 'subject'] = st.text_input("과목명", clean_val(all_df.loc[q_idx, 'subject']), key=f"s_{q_idx}")
        all_df.at[q_idx, 'question'] = st.text_area("문제 지문", clean_val(all_df.loc[q_idx, 'question']), key=f"q_{q_idx}")
        all_df.at[q_idx, 'case_box'] = st.text_area("사례 박스 (수정됨)", clean_val(all_df.loc[q_idx, 'case_box']), key=f"c_{q_idx}", height=200)
        m_f = st.file_uploader("메인 이미지 선택", type=['png','jpg','jpeg'], key=f"m_{q_idx}")
        if m_f:
            with open(os.path.join(IMAGE_DIR, m_f.name), "wb") as f: f.write(m_f.getbuffer())
            all_df.at[q_idx, 'img'] = f"images/{m_f.name}:C"

    with t2:
        all_df.at[q_idx, 'answer'] = st.number_input("정답(1-5)", 1, 5, int(float(clean_val(all_df.loc[q_idx, 'answer']) or 1)))
        for i in range(1, 6):
            all_df.at[q_idx, f'option{i}'] = st.text_input(f"보기 {i}", clean_val(all_df.loc[q_idx, f'option{i}']), key=f"o_{i}_{q_idx}")

    with t3:
        st.subheader("💡 엑셀 표 실시간 편집기")
        ex_in = st.text_area("1. 엑셀 붙여넣기", height=100, key="ex_in")
        md_init = ""
        if ex_in:
            raw = ex_in.replace('"', '').strip()
            lines = raw.split('\n')
            if lines:
                md_list = []
                for i, l in enumerate(lines):
                    cols = [c.strip() for c in l.split('\t')]
                    md_list.append("| " + " | ".join(cols) + " |")
                    if i == 0: md_list.append("| " + " | ".join(["---"] * len(cols)) + " |")
                md_init = "\n".join(md_list)
        
        ed_md = st.text_area("2. 마크다운 수정", value=md_init, height=200, key="ed_md")
        st.write("▼ 미리보기")
        if ed_md:
            st.markdown(ed_md)
            if st.button("🚀 사례 박스에 적용"):
                all_df.at[q_idx, 'case_box'] = ed_md
                st.success("적용 완료!")

    if st.button("💾 최종 저장", use_container_width=True):
        all_df.to_csv(DB_FILE, index=False)
        st.success("저장 완료!"); st.rerun()

# ---------------------------------------------------------
# 모드 3: 성적 통계 센터
# ---------------------------------------------------------
else:
    st.header("📊 성적 통계 센터")
    if os.path.exists(RESULT_FILE):
        rdf = pd.read_csv(RESULT_FILE)
        st.metric("총 응시 인원", f"{len(rdf)}명")
        st.line_chart(rdf['score'])
    else: st.info("기록이 없습니다.")
