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

# 🌟 [이미지 긴급 복구] D드라이브 경로가 적혀있어도 파일명만 뽑아 깃허브 images 폴더에서 가져옴
def get_image_data(img_path):
    if not img_path: return ""
    # 경로 정제 (역슬래시를 슬래시로 바꾸고 파일명만 추출)
    file_name = img_path.replace("\\", "/").split('/')[-1].split(':')[0].strip()
    target_path = os.path.join(IMAGE_DIR, file_name)
    
    if os.path.exists(target_path) and os.path.isfile(target_path):
        try:
            with open(target_path, "rb") as f:
                encoded = base64.b64encode(f.read()).decode()
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
# 모드 1: 시험 시작 (TypeError 해결 버전)
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
                "img": get_image_data(clean_val(row.get('img', ''))),
                "options": [{"text": clean_val(row.get(f'option{i}', '')), "img": get_image_data(clean_val(row.get(f'opt_img{i}', '')))} for i in range(1, 6)]
            }
            if real_id < 200: s1_list.append(q_obj)
            else: s2_list.append(q_obj)
            concept_db[f"Q_{real_id:03d}"] = {"title": clean_val(row.get('concept_title', '')), "point": clean_val(row.get('concept_point', ''))}
        except: continue

    if os.path.exists(HTML_FILE):
        with open(HTML_FILE, "r", encoding="utf-8") as f:
            base_html = f.read()
        
        inject_code = f"""
        <script>
            window.QUESTIONS_S1 = {json.dumps(s1_list, ensure_ascii=False)};
            window.QUESTIONS_S2 = {json.dumps(s2_list, ensure_ascii=False)};
            window.CONCEPT_DATABASE = {json.dumps(concept_db, ensure_ascii=False)};
            setTimeout(() => {{ if(window.render) window.render(); }}, 500);
        </script>
        """
        # TypeError를 유발할 수 있는 복잡한 치환 대신 안전하게 결합
        final_html = base_html.replace('</body>', f'{inject_code}</body>')
        
        # 🌟 핵심: key를 고정 문자열로 지정하여 에러 원천 차단
        st.components.v1.html(final_html, height=1200, scrolling=True, key="main_cbt_frame")

# ---------------------------------------------------------
# 모드 2: 문항 관리 (기존 모든 기능 복구)
# ---------------------------------------------------------
elif mode == "🛠️ 문항 관리":
    st.header("🛠️ 문항 관리")
    all_df = st.session_state.df
    sel_sess = st.radio("교시 선택", ["1교시", "2교시"], horizontal=True)
    target_df = all_df[all_df['id'] < 200] if "1교시" in sel_sess else all_df[all_df['id'] >= 200]
    q_idx = st.selectbox("문항 선택", target_df.index, format_func=lambda x: f"{int(all_df.loc[x, 'id']) % 100}번")
    
    tab1, tab2, tab3 = st.tabs(["📄 문제 내용", "🔢 보기/이미지", "💡 엑셀 도우미"])
    with tab1:
        all_df.at[q_idx, 'subject'] = st.text_input("과목명", clean_val(all_df.loc[q_idx, 'subject']), key=f"s_{q_idx}")
        all_df.at[q_idx, 'question'] = st.text_area("문제 지문", clean_val(all_df.loc[q_idx, 'question']), key=f"q_{q_idx}")
        all_df.at[q_idx, 'case_box'] = st.text_area("사례 박스", clean_val(all_df.loc[q_idx, 'case_box']), key=f"c_{q_idx}")
        m_f = st.file_uploader("이미지 업로드", type=['png','jpg','jpeg'], key=f"m_{q_idx}")
        if m_f:
            with open(os.path.join(IMAGE_DIR, m_f.name), "wb") as f: f.write(m_f.getbuffer())
            all_df.at[q_idx, 'img'] = f"images/{m_f.name}:C"
    with tab2:
        all_df.at[q_idx, 'answer'] = st.number_input("정답", 1, 5, int(float(clean_val(all_df.loc[q_idx, 'answer']) or 1)))
        for i in range(1, 6):
            all_df.at[q_idx, f'option{i}'] = st.text_input(f"보기 {i}", clean_val(all_df.loc[q_idx, f'option{i}']), key=f"ot{i}_{q_idx}")
    with tab3:
        excel_in = st.text_area("엑셀 붙여넣기")
        if excel_in:
            md = "".join(["| " + " | ".join(l.split('\t')) + " |\n" for l in excel_in.strip().split('\n')])
            st.code(md); st.button("사례 박스 적용", on_click=lambda: all_df.update({'case_box': md}))

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
    with st.expander("➕ 수동 기록"):
        score = st.number_input("점수", 0, 140, 80)
        if st.button("저장"):
            new = pd.DataFrame([{"timestamp": datetime.now(), "score": score}])
            new.to_csv(RESULT_FILE, mode='a', header=not os.path.exists(RESULT_FILE), index=False); st.rerun()
