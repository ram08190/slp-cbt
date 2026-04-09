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

# 🌟 이미지 데이터를 안전하게 추출하는 함수 (D드라이브 경로 세척 포함)
def get_image_data(img_path):
    if not img_path: return ""
    # 파일명만 추출 (D:\사진\01.png:C -> 01.png)
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

mode = st.sidebar.radio("메뉴 선택", ["📝 시험 시작", "🛠️ 문항 관리", "📊 성적 통계 센터"])

# ---------------------------------------------------------
# 모드 1: 시험 시작 (TypeError 해결을 위한 안전한 HTML 주입)
# ---------------------------------------------------------
if mode == "📝 시험 시작":
    df = st.session_state.df
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
                "options": [{"text": clean_val(row.get(f'option{i}', '')), "img": get_image_data(clean_val(row.get(f'opt_img{i}', '')))} for i in range(1, 6)]
            }
            if real_id < 200: s1_list.append(q_obj)
            else: s2_list.append(q_obj)
        except: continue

    if os.path.exists(HTML_FILE):
        with open(HTML_FILE, "r", encoding="utf-8") as f:
            base_html = f.read()
        
        # 데이터를 JSON으로 직렬화한 후 HTML 하단에 안전하게 삽입
        data_json = json.dumps({"s1": s1_list, "s2": s2_list}, ensure_ascii=False)
        inject_script = f"""
        <script>
            const data = {data_json};
            window.QUESTIONS_S1 = data.s1;
            window.QUESTIONS_S2 = data.s2;
            setTimeout(() => {{ if(window.render) window.render(); }}, 500);
        </script>
        """
        # TypeError 방지를 위해 문자열 결합 방식을 가장 단순화
        final_html_str = base_html.replace('</body>', f'{inject_script}</body>')
        
        # 🌟 핵심: 명시적으로 str 타입으로 전달
        st.components.v1.html(str(final_html_str), height=1200, scrolling=True)

# ---------------------------------------------------------
# 모드 2: 문항 관리 (보기 이미지 업로드 기능 포함)
# ---------------------------------------------------------
elif mode == "🛠️ 문항 관리":
    st.header("🛠️ 문항 및 이미지 관리")
    all_df = st.session_state.df
    sel_sess = st.radio("교시", ["1교시", "2교시"], horizontal=True)
    target_df = all_df[all_df['id'] < 200] if "1교시" in sel_sess else all_df[all_df['id'] >= 200]
    q_idx = st.selectbox("수정 문항", target_df.index, format_func=lambda x: f"{int(all_df.loc[x, 'id']) % 100}번")
    
    t1, t2, t3 = st.tabs(["📄 지문/이미지", "🔢 보기/보기이미지", "💡 엑셀 도우미"])
    with t1:
        all_df.at[q_idx, 'question'] = st.text_area("지문", clean_val(all_df.loc[q_idx, 'question']), key=f"q_{q_idx}")
        m_f = st.file_uploader("지문 사진", type=['png','jpg'], key=f"m_{q_idx}")
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
        excel_in = st.text_area("엑셀 붙여넣기")
        if excel_in:
            md = "".join(["| " + " | ".join(l.split('\t')) + " |\n" for l in excel_in.strip().split('\n')])
            st.code(md)
            if st.button("적용"): all_df.at[q_idx, 'case_box'] = md; st.success("적용됨")

    if st.button("💾 저장하기", use_container_width=True):
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
    else: st.info("기록이 없습니다.")
