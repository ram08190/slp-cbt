import streamlit as st
import pandas as pd
import json
import os
import base64
import time
from datetime import datetime

# 1. 페이지 설정 (반드시 코드 최상단에 독립적으로 있어야 합니다)
st.set_page_config(page_title="언어재활사 2급 통합 CBT", layout="wide")

DB_FILE = "quiz_db.csv"
RESULT_FILE = "results.csv"
HTML_FILE = "자동화.html"
IMAGE_DIR = "images"

if not os.path.exists(IMAGE_DIR): 
    os.makedirs(IMAGE_DIR)

# 🖼️ 이미지 로더 (D드라이브 경로 세척 + Base64 변환)
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
        return pd.read_csv(DB_FILE, keep_default_na=False).astype(object)
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
    st.write("시험 모드 로딩 중...")
    # (시험 시작 로직 생략 없이 기존 코드를 유지하세요)

# ---------------------------------------------------------
# 모드 2: 문항 관리 (여기에 with t3가 들어가야 합니다)
# ---------------------------------------------------------
elif mode == "🛠️ 문항 관리":
    st.header("🛠️ 문항 관리 시스템")
    all_df = st.session_state.df
    q_idx = st.selectbox("수정 문항 선택", all_df.index, format_func=lambda x: f"{all_df.loc[x, 'id']}번")
    
    t1, t2, t3 = st.tabs(["📄 지문/이미지", "🔢 보기/정답", "💡 엑셀 표 실시간 편집기"])
    
    with t1:
        all_df.at[q_idx, 'question'] = st.text_area("문제 지문", clean_val(all_df.loc[q_idx, 'question']), key=f"q_{q_idx}")
        all_df.at[q_idx, 'case_box'] = st.text_area("사례 박스 내용", clean_val(all_df.loc[q_idx, 'case_box']), key=f"c_{q_idx}", height=200)

    with t2:
        for i in range(1, 6):
            all_df.at[q_idx, f'option{i}'] = st.text_input(f"보기 {i}", clean_val(all_df.loc[q_idx, f'option{i}']), key=f"o_{i}_{q_idx}")

    # 🌟 드디어 정상 위치에 온 with t3!
    with t3:
        st.subheader("💡 엑셀 표 실시간 편집기")
        excel_in = st.text_area("1. 엑셀 데이터를 여기에 붙여넣으세요", height=100, key="ex_input")
        
        md_init = ""
        if excel_in:
            raw = excel_in.replace('"', '').strip()
            lines = raw.split('\n')
            if lines:
                md_list = []
                for i, line in enumerate(lines):
                    cols = [c.strip() for c in line.split('\t')]
                    md_list.append("| " + " | ".join(cols) + " |")
                    if i == 0: md_list.append("| " + " | ".join(["---"] * len(cols)) + " |")
                md_init = "\n".join(md_list)

        edited_md = st.text_area("2. 변환된 마크다운 코드를 직접 수정하세요:", value=md_init, height=200, key="md_editor")
        
        st.write("▼ 현재 표 모양 (실시간 미리보기)")
        if edited_md:
            st.markdown(edited_md)
            if st.button("🚀 이 결과물을 사례 박스에 최종 적용"):
                all_df.at[q_idx, 'case_box'] = edited_md
                st.success("사례 박스에 적용되었습니다!")

    if st.button("💾 모든 수정사항 최종 저장하기", use_container_width=True):
        all_df.to_csv(DB_FILE, index=False)
        st.success("저장 완료!")
        st.rerun()

# ---------------------------------------------------------
# 모드 3: 성적 통계 센터
# ---------------------------------------------------------
else:
    st.header("📊 성적 통계 센터")
    # (통계 로직 유지)
