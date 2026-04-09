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
RESULT_FILE = "results.csv"  # 👈 통계 데이터가 저장되는 곳 (이 파일만 있으면 데이터 유지됨)
HTML_FILE = "자동화.html"
IMAGE_DIR = "images"

if not os.path.exists(IMAGE_DIR): 
    os.makedirs(IMAGE_DIR)

# 🖼️ 이미지 출력 해결 (Base64 로더)
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
                all_df.at[q_idx, f'option{i}'] = st.text_input(f"보기 {i}", clean_val(all_df.loc[q_idx, f'option{i}']), key=f"o{i}_{sel_num}")

        with tab3:
            st.subheader("💡 엑셀 표 편집 및 정렬")
            ex_in = st.text_area("1. 엑셀 붙여넣기", height=100, key=f"ex_ar_{sel_num}")
            align_opt = st.selectbox("정렬 설정", ["왼쪽 (| --- |)", "가운데 (| :---: |)"], key=f"align_{sel_num}")
            
            if st.button("🔄 표 코드로 변환", key=f"btn_conv_{sel_num}", use_container_width=True):
                if ex_in:
                    sep = ":---:" if "가운데" in align_opt else "---"
                    raw = ex_in.strip()
                    processed_text = ""; in_quotes = False
                    for char in raw:
                        if char == '"': in_quotes = not in_quotes; continue 
                        if char == '\n' and in_quotes: processed_text += "<br>" 
                        else: processed_text += char
                    lines = [l for l in processed_text.split('\n') if l.strip()]
                    md_rows = []
                    for i, l in enumerate(lines):
                        cols = [c.strip() for c in l.split('\t')]
                        md_rows.append("| " + " | ".join(cols) + " |")
                        if i == 0: md_rows.append("| " + " | ".join([sep] * len(cols)) + " |")
                    
                    st.session_state[f"temp_md_{sel_num}"] = "\n".join(md_rows)
                    st.rerun()

            # 2. 마크다운 수정 창
            initial_md = st.session_state.get(f"temp_md_{sel_num}", clean_val(all_df.loc[q_idx, 'case_box']))
            final_md = st.text_area("2. 마크다운 수정", value=initial_md, height=200, key=f"edt_box_{sel_num}")
            
            # [중요] 사용자가 수정창에서 타이핑한 내용을 즉시 세션에 동기화
            st.session_state[f"temp_md_{sel_num}"] = final_md
            
            st.markdown("---")
            if final_md: 
                st.markdown(final_md, unsafe_allow_html=True)
            
            if st.button("🚀 사례 박스 적용", key=f"btn_app_{sel_num}", use_container_width=True):
                # 🌟 데이터프레임 양쪽에 즉시 강제 반영
                all_df.at[q_idx, 'case_box'] = final_md
                st.session_state.df.at[q_idx, 'case_box'] = final_md
                st.success("✅ 사례 박스에 적용되었습니다! '📄 지문/이미지' 탭에서 확인하세요.")
                time.sleep(0.5)
                st.rerun() # 변경사항 전파를 위해 리런

    # 🌟 [매우 중요] 여기서부터는 탭(with tab3) 밖입니다. 
    # 문항 관리 모드(elif mode == "🛠️ 문항 관리")가 끝나기 전 최종 저장 버튼 위치입니다.
    st.divider()
    if st.button("💾 모든 수정사항 최종 저장하기", key="final_save_all", use_container_width=True):
        # 최종적으로 CSV 파일에 기록
        all_df.to_csv(DB_FILE, index=False)
        st.session_state.df = all_df
        st.success("🎉 데이터베이스에 영구 저장되었습니다!")
        time.sleep(1)
        st.rerun()
# ---------------------------------------------------------
# 모드 3: 성적 통계 센터 (데이터 보존 확인)
# ---------------------------------------------------------
else:
    st.header("📊 성적 통계 센터")
    if os.path.exists(RESULT_FILE):
        rdf = pd.read_csv(RESULT_FILE)
        st.subheader("📈 응시 결과 요약")
        c1, c2, c3 = st.columns(3)
        c1.metric("총 응시 횟수", f"{len(rdf)}회")
        c2.metric("평균 점수", f"{rdf['score'].mean():.1f}점")
        c3.metric("최고 점수", f"{rdf['score'].max()}점")
        
        st.write("---")
        st.write("▼ 점수 변화 추이")
        st.line_chart(rdf['score'])
        
        st.write("▼ 최근 기록 리스트")
        st.dataframe(rdf.sort_values(by=rdf.columns[0], ascending=False))
    else:
        st.info("아직 저장된 시험 결과(results.csv)가 없습니다. 시험을 마친 후 통계가 생성됩니다.")
