import streamlit as st
import pandas as pd
import json
import os
import base64
from datetime import datetime

# 1. 페이지 설정
st.set_page_config(page_title="언어재활사 2급 통합 CBT", layout="wide")

DB_FILE = "quiz_db.csv"
RESULT_FILE = "results.csv"
HTML_FILE = "자동화.html"
IMAGE_DIR = "images"

if not os.path.exists(IMAGE_DIR): 
    os.makedirs(IMAGE_DIR)

# 🖼️ 이미지 로더 (파일명만 추출하여 깃허브 images 폴더에서 호출)
def get_image_data(img_path):
    if not img_path: return ""
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
# 모드 1: 시험 시작 (용량 최적화로 TypeError 해결)
# ---------------------------------------------------------
if mode == "📝 시험 시작":
    df = st.session_state.df
    if df.empty:
        st.warning("데이터가 비어있습니다.")
    else:
        # 🌟 데이터를 최대한 작게 만듭니다.
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
                    "img": get_image_data(clean_val(row.get('img', ''))),
                    "options": [
                        {"text": clean_val(row.get(f'option{i}', '')), "img": get_image_data(clean_val(row.get(f'opt_img{i}', '')))} 
                        for i in range(1, 6)
                    ]
                }
                if real_id < 200: s1_list.append(q_obj)
                else: s2_list.append(q_obj)
            except: continue

        if os.path.exists(HTML_FILE):
            with open(HTML_FILE, "r", encoding="utf-8") as f:
                html_template = f.read()
            
            # 🌟 핵심: 대용량 데이터를 JSON 문자열로 변환하여 <body> 태그 끝에 안전하게 삽입
            data_payload = json.dumps({"s1": s1_list, "s2": s2_list}, ensure_ascii=False)
            
            script_payload = f"""
            <script id="cbt_data" type="application/json">
                {data_payload}
            </script>
            <script>
                // 데이터 로드 및 렌더링 호출
                document.addEventListener("DOMContentLoaded", function() {{
                    const payload = JSON.parse(document.getElementById('cbt_data').textContent);
                    window.QUESTIONS_S1 = payload.s1;
                    window.QUESTIONS_S2 = payload.s2;
                    if(window.render) window.render();
                    else setTimeout(() => {{ if(window.render) window.render(); }}, 500);
                }});
            </script>
            """
            # HTML 용량을 최소화하기 위해 데이터를 별도의 JSON 스크립트로 분리
            final_html = html_template.replace('</body>', script_payload + '</body>')
            
            # 🌟 [TypeError 방지] 문자열로 명시적 변환 및 key 제거
            st.components.v1.html(str(final_html), height=1200, scrolling=True)

# ---------------------------------------------------------
# 모드 2: 문항 관리 (실시간 표 편집기 유지)
# ---------------------------------------------------------
elif mode == "🛠️ 문항 관리":
    st.header("🛠️ 문항 및 이미지 관리")
    all_df = st.session_state.df
    q_idx = st.selectbox("수정 문항", all_df.index, format_func=lambda x: f"{all_df.loc[x, 'id']}번")
    
    t1, t2, t3 = st.tabs(["📄 지문/이미지", "🔢 보기/정답", "💡 엑셀 표 편집기"])
    
    with t1:
        all_df.at[q_idx, 'question'] = st.text_area("문제 지문", clean_val(all_df.loc[q_idx, 'question']), key=f"q_{q_idx}")
        all_df.at[q_idx, 'case_box'] = st.text_area("사례 박스", clean_val(all_df.loc[q_idx, 'case_box']), key=f"c_{q_idx}", height=150)
        m_f = st.file_uploader("사진 업로드", type=['png','jpg'], key=f"m_{q_idx}")
        if m_f:
            with open(os.path.join(IMAGE_DIR, m_f.name), "wb") as f: f.write(m_f.getbuffer())
            all_df.at[q_idx, 'img'] = f"images/{m_f.name}:C"

    with t2:
        for i in range(1, 6):
            col_t, col_i = st.columns([2, 1])
            all_df.at[q_idx, f'option{i}'] = col_t.text_input(f"보기 {i}", clean_val(all_df.loc[q_idx, f'option{i}']), key=f"o_{i}_{q_idx}")
            o_f = col_i.file_uploader(f"보기{i} 사진", type=['png','jpg'], key=f"ou{i}_{q_idx}")
            if o_f:
                with open(os.path.join(IMAGE_DIR, o_f.name), "wb") as f: f.write(o_f.getbuffer())
                all_df.at[q_idx, f'opt_img{i}'] = f"images/{o_f.name}"

    with t3:
        ex_in = st.text_area("엑셀 붙여넣기", key="ex_input")
        if ex_in:
            raw = ex_in.replace('"', '').strip()
            lines = raw.split('\n')
            md = []
            for i, l in enumerate(lines):
                cols = [c.strip() for c in l.split('\t')]
                md.append("| " + " | ".join(cols) + " |")
                if i == 0: md.append("| " + " | ".join(["---"] * len(cols)) + " |")
            res_md = "\n".join(md)
            edited = st.text_area("마크다운 수정", value=res_md, height=150, key="md_editor")
            st.markdown(edited)
            if st.button("🚀 사례 박스 적용"):
                all_df.at[q_idx, 'case_box'] = edited; st.success("적용됨")

    if st.button("💾 최종 저장하기", use_container_width=True):
        all_df.to_csv(DB_FILE, index=False); st.success("저장 완료!"); st.rerun()

# ---------------------------------------------------------
# 모드 3: 성적 통계 센터
# ---------------------------------------------------------
else:
    st.header("📊 성적 통계 센터")
    if os.path.exists(RESULT_FILE):
        rdf = pd.read_csv(RESULT_FILE)
        st.metric("총 응시 인원", f"{len(rdf)}명")
        st.line_chart(rdf['score'])
