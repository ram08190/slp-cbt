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

# 🖼️ 이미지 출력 해결 (Base64 변환 로더)
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
        df['id'] = pd.to_numeric(df['id'], errors='coerce').fillna(0).astype(int)
        return df.sort_values('id').reset_index(drop=True)
    return pd.DataFrame()

if 'df' not in st.session_state: 
    st.session_state.df = load_data()

def clean_val(x):
    s = str(x).strip().replace('"', '')
    return "" if s.lower() in ['nan', 'none', ''] else s

mode = st.sidebar.radio("메뉴 선택", ["📝 시험 시작", "🛠️ 문항 관리", "📊 성적 통계 센터"])

# ---------------------------------------------------------
# 모드 1: 시험 시작
# ---------------------------------------------------------
if mode == "📝 시험 시작":
    df = st.session_state.df
    s1_list, s2_list = [], []
    for _, row in df.iterrows():
        try:
            rid = int(row['id'])
            q_obj = {
                "id": rid % 100,
                "subject": clean_val(row.get('subject', '')),
                "text": clean_val(row.get('question', '')),
                "passage": clean_val(row.get('case_box', '')),
                "answer": int(float(clean_val(row.get('answer', 1)) or 1)),
                "img": get_image_data(clean_val(row.get('img', ''))),
                "options": [{"text": clean_val(row.get(f'option{i}', '')), "img": get_image_data(clean_val(row.get(f'opt_img{i}', '')))} for i in range(1, 6)]
            }
            if 100 < rid < 200: s1_list.append(q_obj)
            elif rid > 200: s2_list.append(q_obj)
        except: continue

    if os.path.exists(HTML_FILE):
        with open(HTML_FILE, "r", encoding="utf-8") as f:
            base_html = f.read()
        payload = json.dumps({"s1": s1_list, "s2": s2_list}, ensure_ascii=False)
        inject = f"<script id='data' type='application/json'>{payload}</script><script>const d=JSON.parse(document.getElementById('data').textContent); window.QUESTIONS_S1=d.s1; window.QUESTIONS_S2=d.s2; setTimeout(()=>{{if(window.render)window.render();}},500);</script>"
        st.components.v1.html(base_html.replace('</body>', inject + '</body>'), height=1200, scrolling=True)

# ---------------------------------------------------------
# 모드 2: 문항 관리
# ---------------------------------------------------------
elif mode == "🛠️ 문항 관리":
    st.header("🛠️ 문항 관리 시스템")
    all_df = st.session_state.df
    
    c1, c2 = st.columns(2)
    with c1:
        sel_sess = st.selectbox("교시 선택", ["1교시 (1-80번)", "2교시 (1-70번)"], key="sess_box")
    with c2:
        start_id = 101 if "1교시" in sel_sess else 201
        end_id = 181 if "1교시" in sel_sess else 271
        target_ids = list(range(start_id, end_id))
        sel_num = st.selectbox("문항 선택", target_ids, format_func=lambda x: f"{x % 100}번", key="num_box")

    q_row = all_df[all_df['id'] == sel_num]
    if not q_row.empty:
        q_idx = q_row.index[0]
        tab1, tab2, tab3 = st.tabs(["📄 지문/이미지", "🔢 보기/정답", "💡 엑셀 실시간 편집기"])
        
        with tab1:
            all_df.at[q_idx, 'subject'] = st.text_input("과목명", clean_val(all_df.loc[q_idx, 'subject']), key=f"s_in_{sel_num}")
            all_df.at[q_idx, 'question'] = st.text_area("문제 지문", clean_val(all_df.loc[q_idx, 'question']), key=f"q_in_{sel_num}")
            all_df.at[q_idx, 'case_box'] = st.text_area("사례 박스", clean_val(all_df.loc[q_idx, 'case_box']), key=f"c_in_{sel_num}", height=200)
            m_f = st.file_uploader("이미지 업로드", type=['png','jpg','jpeg'], key=f"m_up_{sel_num}")
            if m_f:
                with open(os.path.join(IMAGE_DIR, m_f.name), "wb") as f: f.write(m_f.getbuffer())
                all_df.at[q_idx, 'img'] = f"images/{m_f.name}:C"
        
        with tab2:
            all_df.at[q_idx, 'answer'] = st.number_input("정답", 1, 5, int(float(clean_val(all_df.loc[q_idx, 'answer']) or 1)), key=f"ans_{sel_num}")
            for i in range(1, 6):
                col_t, col_i = st.columns([3, 1])
                all_df.at[q_idx, f'option{i}'] = col_t.text_input(f"보기 {i}", clean_val(all_df.loc[q_idx, f'option{i}']), key=f"o{i}_{sel_num}")
                o_f = col_i.file_uploader(f"사진{i}", type=['png','jpg'], key=f"oi{i}_{sel_num}")
                if o_f:
                    with open(os.path.join(IMAGE_DIR, o_f.name), "wb") as f: f.write(o_f.getbuffer())
                    all_df.at[q_idx, f'opt_img{i}'] = f"images/{o_f.name}"

        with tab3:
            st.subheader("💡 엑셀 표 편집 프로세스")
            ex_in = st.text_area("1. 엑셀 데이터를 여기에 붙여넣으세요", height=100, key=f"ex_ar_{sel_num}")
            
            if st.button("🔄 마크다운 표 코드로 변환하기", key=f"btn_conv_{sel_num}", use_container_width=True):
                if ex_in:
                    raw = ex_in.strip()
                    processed_text = ""; in_quotes = False
                    for char in raw:
                        if char == '"': in_quotes = not in_quotes; continue 
                        if char == '\n' and in_quotes: processed_text += "<br>" 
                        else: processed_text += char
                    lines = [l for l in processed_text.split('\n') if l.strip()]
                    md_rows = []
                    for i, line in enumerate(lines):
                        cols = [c.strip() for c in line.split('\t')]
                        md_rows.append("| " + " | ".join(cols) + " |")
                        if i == 0: md_rows.append("| " + " | ".join(["---"] * len(cols)) + " |")
                    st.session_state[f"temp_md_{sel_num}"] = "\n".join(md_rows)
                    st.rerun()

            initial_md = st.session_state.get(f"temp_md_{sel_num}", clean_val(all_df.loc[q_idx, 'case_box']))
            final_md = st.text_area("2. 마크다운 수정 (여기서 고치면 아래 실시간 반영)", value=initial_md, height=250, key=f"edt_box_{sel_num}")
            st.session_state[f"temp_md_{sel_num}"] = final_md
            
            st.markdown("---")
            st.write("▼ 실시간 미리보기")
            if final_md: st.markdown(final_md, unsafe_allow_html=True)
            
            if st.button("🚀 이 표를 사례 박스에 최종 적용", key=f"btn_app_{sel_num}", use_container_width=True):
                all_df.at[q_idx, 'case_box'] = final_md
                st.success("사례 박스에 적용되었습니다!")

    st.divider()
    # 🌟 고유 key를 부여하여 Duplicate ID 에러 방지
    if st.button("💾 모든 수정사항 최종 저장하기", key="final_save_button", use_container_width=True):
        all_df.to_csv(DB_FILE, index=False)
        st.success("저장 완료!"); time.sleep(1); st.rerun()

else:
    st.header("📊 성적 통계 센터")
    # (통계 로직 생략)
