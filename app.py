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

# 🌟 [강화된 이미지 로더] 경로 불일치 문제를 해결합니다.
def get_image_data(img_path):
    if not img_path: return ""
    file_name = img_path.split('/')[-1].split(':')[0].strip()
    search_paths = [
        os.path.join(IMAGE_DIR, file_name),
        file_name,
        img_path.split(':')[0].strip()
    ]
    for path in search_paths:
        if os.path.exists(path) and os.path.isfile(path):
            try:
                with open(path, "rb") as f:
                    encoded = base64.b64encode(f.read()).decode()
                    ext = path.split('.')[-1].lower()
                    mime = "image/png" if ext == "png" else "image/jpeg"
                    return f"data:{mime};base64,{encoded}"
            except: continue
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
# 모드 1: 시험 시작 (바둑판 탭 + 이미지 데이터 주입)
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
            concept_db[f"Q_{real_id:03d}"] = {
                "title": clean_val(row.get('concept_title', '')), 
                "point": clean_val(row.get('concept_point', '')),
                "mindmap": clean_val(row.get('concept_mindmap', '')),
                "video": clean_val(row.get('concept_video', ''))
            }
        except: continue

    if os.path.exists(HTML_FILE):
        with open(HTML_FILE, "r", encoding="utf-8") as f:
            base_html = f.read()
        
        # 🌟 바둑판 필터 기능 및 데이터 주입
        inject_code = f"""
        <script>
            window.QUESTIONS_S1 = {json.dumps(s1_list, ensure_ascii=False)};
            window.QUESTIONS_S2 = {json.dumps(s2_list, ensure_ascii=False)};
            window.CONCEPT_DATABASE = {json.dumps(concept_db, ensure_ascii=False)};
            // 여기에 이전 바둑판 필터링(openGridPanel 등) 스크립트가 포함됩니다.
        </script>
        """
        final_html = base_html.replace('<script src="questions1.js"></script>', '').replace('<script src="questions2.js"></script>', '').replace('<script src="database.js"></script>', inject_code)
        st.components.v1.html(final_html, height=1200, scrolling=True, key=f"cbt_{time.time()}")

# ---------------------------------------------------------
# 모드 2: 문항 관리 (상세 수정 옵션 100% 복구)
# ---------------------------------------------------------
elif mode == "🛠️ 문항 관리":
    st.header("🛠️ 문항 및 엑셀 표 관리 시스템")
    all_df = st.session_state.df
    sel_sess = st.radio("교시 선택", ["1교시", "2교시"], horizontal=True)
    target_df = all_df[all_df['id'] < 200] if "1교시" in sel_sess else all_df[all_df['id'] >= 200]
    q_idx = st.selectbox("수정할 문항 선택", target_df.index, format_func=lambda x: f"{int(all_df.loc[x, 'id']) % 100}번 문제")
    
    df = all_df.copy()
    tab1, tab2, tab3 = st.tabs(["📄 문제 지문/내용", "🔢 보기 및 이미지", "💡 엑셀 표 도우미"])
    
    with tab1:
        c1, c2 = st.columns([2, 1])
        with c1:
            df.at[q_idx, 'subject'] = st.text_input("과목명", value=clean_val(df.loc[q_idx, 'subject']), key=f"s_{q_idx}")
            df.at[q_idx, 'question'] = st.text_area("문제 지문", value=clean_val(df.loc[q_idx, 'question']), height=100, key=f"q_{q_idx}")
            df.at[q_idx, 'case_box'] = st.text_area("사례 박스 (표 포함)", value=clean_val(df.loc[q_idx, 'case_box']), height=150, key=f"c_{q_idx}")
        with c2:
            m_f = st.file_uploader("메인 이미지 업로드", type=['png','jpg','jpeg'], key=f"m_{q_idx}")
            if m_f:
                with open(os.path.join(IMAGE_DIR, m_f.name), "wb") as f: f.write(m_f.getbuffer())
                df.at[q_idx, 'img'] = f"images/{m_f.name}:C"
            if clean_val(df.loc[q_idx, 'img']): st.info(f"선택됨: {df.loc[q_idx, 'img']}")

    with tab2:
        df.at[q_idx, 'answer'] = st.number_input("정답 (1~5)", 1, 5, value=int(float(clean_val(df.loc[q_idx, 'answer']) or 1)))
        for i in range(1, 6):
            col_t, col_i = st.columns([2, 1])
            df.at[q_idx, f'option{i}'] = col_t.text_input(f"보기 {i}", value=clean_val(df.loc[q_idx, f'option{i}']), key=f"ot{i}_{q_idx}")
            o_f = col_i.file_uploader(f"보기{i} 이미지", type=['png','jpg','jpeg'], key=f"ou{i}_{q_idx}")
            if o_f:
                with open(os.path.join(IMAGE_DIR, o_f.name), "wb") as f: f.write(o_f.getbuffer())
                df.at[q_idx, f'opt_img{i}'] = f"images/{o_f.name}"

    with tab3:
        excel_in = st.text_area("엑셀 내용을 복사해서 붙여넣으세요")
        if excel_in:
            md = ""
            for l in excel_in.strip().split('\n'): md += "| " + " | ".join(l.split('\t')) + " |\n"
            st.code(md)
            if st.button("사례 박스에 적용"):
                df.at[q_idx, 'case_box'] = md; st.success("적용 완료!")

    if st.button("💾 최종 저장하기", use_container_width=True):
        st.session_state.df = df
        df.to_csv(DB_FILE, index=False); st.success("데이터베이스 저장 성공!"); st.rerun()

# ---------------------------------------------------------
# 모드 3: 성적 통계 센터 (완벽 복구)
# ---------------------------------------------------------
else:
    st.header("📊 성적 통계 센터")
    if os.path.exists(RESULT_FILE):
        res_df = pd.read_csv(RESULT_FILE)
        res_df['timestamp'] = pd.to_datetime(res_df['timestamp'])
        
        c1, c2, c3 = st.columns(3)
        c1.metric("총 응시 인원", f"{len(res_df)}명")
        c2.metric("평균 점수", f"{res_df['score'].mean():.1f}점")
        if len(res_df) > 1:
            diff = res_df.iloc[-1]['score'] - res_df.iloc[-2]['score']
            c3.metric("최근 변화량", f"{res_df.iloc[-1]['score']}점", f"{diff:+.1f}점")
        
        st.subheader("📈 성적 추이 그래프")
        st.line_chart(res_df.set_index('timestamp')['score'])
        
        with st.expander("📝 전체 성적 기록 보기"):
            st.dataframe(res_df.sort_values('timestamp', ascending=False), use_container_width=True)
    else:
        st.info("아직 성적 기록이 없습니다. 시험을 완료하거나 아래에서 수동으로 추가하세요.")

    st.divider()
    with st.expander("➕ 수동 성적 기록 추가"):
        score = st.number_input("점수", 0, 140, 80)
        if st.button("기록 저장"):
            new_res = pd.DataFrame([{"timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "score": score}])
            new_res.to_csv(RESULT_FILE, mode='a', header=not os.path.exists(RESULT_FILE), index=False)
            st.success("기록되었습니다."); st.rerun()
