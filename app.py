import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import json
import os
import re
import time

# 1. 페이지 설정
st.set_page_config(page_title="언어재활사 2급 통합 CBT", layout="wide")

# 🌟 구글 시트 연결 설정 (Secrets에 등록된 정보를 사용)
conn = st.connection("gsheets", type=GSheetsConnection)

HTML_FILE = "자동화.html"

def load_data():
    # 구글 시트에서 최신 데이터를 실시간으로 읽어옴
    df = conn.read(ttl=0)
    # ID를 숫자로 변환
    df['id'] = pd.to_numeric(df['id'], errors='coerce').fillna(0).astype(int)
    return df.sort_values('id').reset_index(drop=True)

if 'df' not in st.session_state: 
    st.session_state.df = load_data()

def clean_val(x):
    s = str(x).strip().replace('"', '')
    return "" if s.lower() in ['nan', 'none', ''] else s

# 🖼️ 구글 드라이브 공유 링크를 이미지 주소로 자동 변환하는 함수
def get_display_image(url):
    if not url or "http" not in str(url): return ""
    # 구글 드라이브 링크인 경우 직링크로 변환
    if "drive.google.com" in url:
        match = re.search(r'file/d/(.*?)/', url)
        if match:
            file_id = match.group(1)
            return f"https://drive.google.com/uc?export=view&id={file_id}"
    return url # 일반 URL인 경우 그대로 반환

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
                # 🌟 이미지 링크 처리
                "img": get_display_image(clean_val(row.get('img', ''))),
                "options": [
                    {"text": clean_val(row.get(f'option{i}', '')), 
                     "img": get_display_image(clean_val(row.get(f'opt_img{i}', '')))} 
                    for i in range(1, 6)
                ]
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
    st.header("🛠️ 문항 관리 (Google Sheets 연동)")
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
            
            # 🖼️ 이미지 링크 관리
            st.divider()
            st.write("🖼️ 이미지 관리")
            img_val = clean_val(all_df.loc[q_idx, 'img'])
            new_img = st.text_input("이미지 주소 (구글 드라이브 공유 링크)", value=img_val, key=f"img_in_{sel_num}")
            all_df.at[q_idx, 'img'] = new_img
            
            display_url = get_display_image(new_img)
            if display_url:
                st.image(display_url, caption="미리보기", width=300)
                st.caption(f"이미지 소스: {display_url}")
        
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

            initial_md = st.session_state.get(f"temp_md_{sel_num}", clean_val(all_df.loc[q_idx, 'case_box']))
            final_md = st.text_area("2. 마크다운 수정", value=initial_md, height=200, key=f"edt_box_{sel_num}")
            st.session_state[f"temp_md_{sel_num}"] = final_md
            
            st.markdown("---")
            if final_md: st.markdown(final_md, unsafe_allow_html=True)
            
            if st.button("🚀 사례 박스 적용", key=f"btn_app_{sel_num}", use_container_width=True):
                all_df.at[q_idx, 'case_box'] = final_md
                st.session_state.df.at[q_idx, 'case_box'] = final_md
                st.success("✅ 사례 박스에 반영되었습니다.")
                time.sleep(0.5)
                st.rerun()

    st.divider()
    if st.button("💾 모든 수정사항 구글 시트에 영구 저장하기", key="final_save_gs", use_container_width=True):
        try:
            # 구글 시트 업데이트
            conn.update(data=all_df)
            st.session_state.df = all_df
            st.success("🎉 구글 스프레드시트에 영구 저장되었습니다!")
            time.sleep(1)
            st.rerun()
        except Exception as e:
            st.error(f"저장 실패: {e}")

# ---------------------------------------------------------
# 모드 3: 성적 통계 센터
# ---------------------------------------------------------
else:
    st.header("📊 성적 통계 센터")
    st.info("성적 데이터는 브라우저 혹은 별도 DB 설정을 통해 관리됩니다.")
