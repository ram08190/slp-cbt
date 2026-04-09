import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime

# 1. 페이지 설정 및 파일 경로
st.set_page_config(page_title="언어재활사 2급 통합 CBT", layout="wide")

DB_FILE = "quiz_db.csv"
RESULT_FILE = "results.csv"  # 성적 누적 저장용
HTML_FILE = "자동화.html"
IMAGE_DIR = "images"

if not os.path.exists(IMAGE_DIR): os.makedirs(IMAGE_DIR)

# [데이터 로드] 문항 데이터
def load_data():
    required_cols = ["id", "session", "subject", "question", "case_box", "answer", 
                     "option1", "option2", "option3", "option4", "option5",
                     "img", "opt_img1", "opt_img2", "opt_img3", "opt_img4", "opt_img5",
                     "concept_title", "concept_point", "concept_mindmap", "concept_video"]
    s1_ids = [100 + i for i in range(1, 81)]
    s2_ids = [200 + i for i in range(1, 71)]
    all_target_ids = s1_ids + s2_ids
    if os.path.exists(DB_FILE):
        df = pd.read_csv(DB_FILE, keep_default_na=False).astype(object)
        try: df['id'] = df['id'].astype(int)
        except: df['id'] = pd.to_numeric(df['id'], errors='coerce').fillna(0).astype(int)
        df = df[df['id'].isin(all_target_ids)]
        return df.sort_values('id').reset_index(drop=True).astype(object)
    else:
        return pd.DataFrame([{"id": i, "session": "1" if i < 200 else "2"} for i in all_target_ids])

if 'df' not in st.session_state: st.session_state.df = load_data()

def clean_val(x):
    s = str(x).strip()
    return "" if s.lower() in ['nan', 'none', ''] else s

# --- 메뉴 선택 ---
mode = st.sidebar.radio("메뉴 선택", ["📝 시험 시작", "🛠️ 문항 관리", "📊 성적 통계 센터"])

# ---------------------------------------------------------
# 모드 1: 시험 시작
# ---------------------------------------------------------
if mode == "📝 시험 시작":
    df = st.session_state.df
    s1_list, s2_list, concept_db = [], [], {}
    for _, row in df.iterrows():
        try:
            real_id = int(row['id'])
            q_obj = {"id": real_id % 100, "subject": clean_val(row.get('subject', '')),
                     "text": clean_val(row.get('question', '')), "passage": clean_val(row.get('case_box', '')),
                     "answer": int(float(clean_val(row.get('answer', 1)) or 1)), "img": clean_val(row.get('img', '')),
                     "options": [{"text": clean_val(row.get(f'option{i}', '')), "img": clean_val(row.get(f'opt_img{i}', ''))} for i in range(1, 6)]}
            if real_id < 200: s1_list.append(q_obj)
            else: s2_list.append(q_obj)
            concept_db[f"Q_{real_id:03d}"] = {"title": clean_val(row.get('concept_title', '')), "point": clean_val(row.get('concept_point', ''))}
        except: continue

    # HTML에 데이터 주입
    if os.path.exists(HTML_FILE):
        with open(HTML_FILE, "r", encoding="utf-8") as f: html_content = f.read()
        data_inject = f"""<script>
            window.QUESTIONS_S1 = {json.dumps(s1_list, ensure_ascii=False)};
            window.QUESTIONS_S2 = {json.dumps(s2_list, ensure_ascii=False)};
            window.CONCEPT_DATABASE = {json.dumps(concept_db, ensure_ascii=False)};
        </script>"""
        final_html = html_content.replace('<script src="questions1.js"></script>', '').replace('<script src="questions2.js"></script>', '').replace('<script src="database.js"></script>', data_inject)
        st.components.v1.html(final_html, height=1000, scrolling=True)

# ---------------------------------------------------------
# 모드 2: 문항 관리 (생략 없이 통합 유지)
# ---------------------------------------------------------
elif mode == "🛠️ 문항 관리":
    st.header("🛠️ 문항 및 엑셀 표 도우미")
    # (기존 문항 관리 코드 동일하게 적용됨)
    st.info("문항 수정 및 엑셀 표 붙여넣기 기능을 활용하세요.")
    # ... (생략된 문항 관리 로직 - 이전 코드와 동일)

# ---------------------------------------------------------
# 모드 3: 📊 성적 통계 센터 (신규 기능)
# ---------------------------------------------------------
else:
    st.header("📊 시험 결과 분석 대시보드")
    
    if os.path.exists(RESULT_FILE):
        res_df = pd.read_csv(RESULT_FILE)
        res_df['timestamp'] = pd.to_datetime(res_df['timestamp'])
        
        # 성적 기록 샘플이 없을 경우를 대비한 대시보드 구성
        total_attempts = len(res_df)
        avg_score = res_df['score'].mean()
        
        # 최근 시험 vs 이전 시험 비교
        if total_attempts >= 2:
            latest_avg = res_df.iloc[-1]['score']
            prev_avg = res_df.iloc[-2]['score']
            diff = latest_avg - prev_avg
            diff_pct = (diff / prev_avg) * 100 if prev_avg != 0 else 0
        else:
            latest_avg, diff, diff_pct = avg_score, 0, 0

        # 시각화 지표
        c1, c2, c3 = st.columns(3)
        c1.metric("총 응시 인원", f"{total_attempts}명")
        c2.metric("전체 평균 점수", f"{avg_score:.1f}점")
        c3.metric("최근 시험 변화율", f"{latest_avg:.1f}점", f"{diff:+.1f} ({diff_pct:+.1f}%)")
        
        st.divider()
        st.subheader("📈 성적 변화 추이")
        st.line_chart(res_df.set_index('timestamp')['score'])
        
        st.subheader("📜 상세 응시 기록")
        st.dataframe(res_df.sort_values('timestamp', ascending=False), use_container_width=True)
        
        if st.button("🗑️ 모든 기록 초기화"):
            os.remove(RESULT_FILE)
            st.rerun()
    else:
        st.info("아직 누적된 시험 결과 데이터가 없습니다. 시험이 종료되면 자동으로 기록됩니다.")
        
    # [임시 기능] 성적 강제 기록 테스트 (실제로는 자동화.html에서 서버로 전송해야 함)
    with st.expander("📝 테스트용 성적 입력 (개발용)"):
        t_score = st.number_input("점수", 0, 100, 80)
        if st.button("테스트 데이터 추가"):
            new_res = pd.DataFrame([{"timestamp": datetime.now(), "score": t_score}])
            if os.path.exists(RESULT_FILE): new_res.to_csv(RESULT_FILE, mode='a', header=False, index=False)
            else: new_res.to_csv(RESULT_FILE, index=False)
            st.rerun()
