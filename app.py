import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime

# 1. 페이지 설정
st.set_page_config(page_title="언어재활사 2급 통합 CBT", layout="wide")

DB_FILE = "quiz_db.csv"
RESULT_FILE = "results.csv"
HTML_FILE = "자동화.html"
IMAGE_DIR = "images"

if not os.path.exists(IMAGE_DIR): os.makedirs(IMAGE_DIR)

# [데이터 로드] 2급 규격 고정 (ID: 101~180, 201~270)
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

mode = st.sidebar.radio("메뉴 선택", ["📝 시험 시작", "🛠️ 문항 관리", "📊 성적 통계 센터"])

# ---------------------------------------------------------
# 모드 1: 시험 시작 (강력한 필터링 모달 스크립트 주입)
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
                "img": clean_val(row.get('img', '')),
                "options": [{"text": clean_val(row.get(f'option{i}', '')), "img": clean_val(row.get(f'opt_img{i}', ''))} for i in range(1, 6)]
            }
            if real_id < 200: s1_list.append(q_obj)
            else: s2_list.append(q_obj)
            concept_db[f"Q_{real_id:03d}"] = {"title": clean_val(row.get('concept_title', '')), "point": clean_val(row.get('concept_point', ''))}
        except: continue

    if os.path.exists(HTML_FILE):
        with open(HTML_FILE, "r", encoding="utf-8") as f:
            base_html = f.read()
        
        # 🌟 탭 분리 기능을 위한 HTML/JS 강제 주입
        # 이미지와 똑같은 디자인의 필터 모달과 클릭 이벤트를 생성합니다.
        data_inject = f"""
        <style>
            #filter-modal-custom {{ display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.5); z-index: 9999; align-items: center; justify-content: center; padding: 20px; }}
            .filter-win {{ background: white; width: 100%; max-width: 900px; height: 80vh; border-radius: 12px; display: flex; flex-direction: column; overflow: hidden; box-shadow: 0 20px 25px -5px rgba(0,0,0,0.1); }}
            .filter-header {{ background: #0055a5; color: white; padding: 15px 20px; display: flex; justify-content: space-between; align-items: center; }}
            .filter-tabs {{ display: flex; border-bottom: 1px solid #e2e8f0; }}
            .filter-tab {{ flex: 1; padding: 15px; text-align: center; font-weight: bold; cursor: pointer; border-bottom: 3px solid transparent; color: #64748b; }}
            .filter-tab.active {{ color: #0055a5; border-color: #0055a5; background: #f8fafc; }}
            .filter-content {{ flex: 1; overflow-y: auto; padding: 20px; background: #f1f5f9; grid-template-columns: repeat(2, 1fr); display: grid; gap: 12px; align-content: start; }}
            .q-card {{ background: white; padding: 15px; border-radius: 8px; border: 1px solid #e2e8f0; cursor: pointer; transition: 0.2s; text-align: left; }}
            .q-card:hover {{ border-color: #0055a5; transform: translateY(-2px); }}
            .q-badge {{ display: inline-block; background: #ef4444; color: white; padding: 2px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; margin-bottom: 8px; }}
            .solved-badge {{ float: right; font-size: 12px; color: #0055a5; font-weight: bold; }}
        </style>

        <div id="filter-modal-custom">
            <div class="filter-win">
                <div class="filter-header">
                    <h2 style="margin:0; font-size:18px;">문제 보기</h2>
                    <button onclick="closeFilterModal()" style="background:none; border:none; color:white; font-size:24px; cursor:pointer;">&times;</button>
                </div>
                <div class="filter-tabs">
                    <div id="tab-all" class="filter-tab active" onclick="updateFilter('all')">전체 문제</div>
                    <div id="tab-checked" class="filter-tab" onclick="updateFilter('checked')">체크 문제</div>
                    <div id="tab-unsolved" class="filter-tab" onclick="updateFilter('unsolved')">안 푼 문제</div>
                </div>
                <div id="filter-content-area" class="filter-content"></div>
            </div>
        </div>

        <script>
            window.QUESTIONS_S1 = {json.dumps(s1_list, ensure_ascii=False)};
            window.QUESTIONS_S2 = {json.dumps(s2_list, ensure_ascii=False)};
            window.CONCEPT_DATABASE = {json.dumps(concept_db, ensure_ascii=False)};
            window.checkList = window.checkList || new Set();

            function openFilterModal(type) {{
                document.getElementById('filter-modal-custom').style.display = 'flex';
                updateFilter(type);
            }}

            function closeFilterModal() {{
                document.getElementById('filter-modal-custom').style.display = 'none';
            }}

            function updateFilter(type) {{
                // 탭 스타일 변경
                document.querySelectorAll('.filter-tab').forEach(t => t.classList.remove('active'));
                document.getElementById('tab-' + type).classList.add('active');

                const questions = (window.currentSession === 2) ? window.QUESTIONS_S2 : window.QUESTIONS_S1;
                const content = document.getElementById('filter-content-area');
                content.innerHTML = '';

                let filtered = questions;
                if(type === 'checked') filtered = questions.filter(q => window.checkList && window.checkList.has(q.id));
                if(type === 'unsolved') filtered = questions.filter(q => !window.userAns[window.currentSession][q.id]);

                filtered.forEach(q => {{
                    const isSolved = window.userAns[window.currentSession][q.id] ? "✅ 풀음" : "❓ 미풀이";
                    const card = document.createElement('div');
                    card.className = "q-card";
                    card.onclick = () => {{ 
                        window.currIdx = questions.findIndex(item => item.id === q.id); 
                        window.render(); 
                        closeFilterModal(); 
                    }};
                    card.innerHTML = `
                        <div class="q-badge">${{q.id}}</div>
                        <span class="solved-badge">${{isSolved}}</span>
                        <div style="font-size:14px; font-weight:500; color:#1e293b; overflow: hidden; text-overflow: ellipsis; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;">${{q.text}}</div>
                    `;
                    content.appendChild(card);
                }});
            }}

            // 하단 버튼 강제 연결 (HTML의 버튼들이 이 함수를 호출하게 함)
            document.addEventListener('DOMContentLoaded', () => {{
                // 기존 HTML 버튼이 있다면 이벤트를 덮어씌움
                const btnAll = document.querySelector('button[onclick*="전체"]');
                const btnCheck = document.querySelector('button[onclick*="체크"]');
                const btnUnsolved = document.querySelector('button[onclick*="안푼"]');
                
                if(btnAll) btnAll.onclick = () => openFilterModal('all');
                if(btnCheck) btnCheck.onclick = () => openFilterModal('checked');
                if(btnUnsolved) btnUnsolved.onclick = () => openFilterModal('unsolved');
            }});
        </script>
        """
        final_html = base_html.replace('<script src="questions1.js"></script>', '').replace('<script src="questions2.js"></script>', '').replace('<script src="database.js"></script>', data_inject)
        st.components.v1.html(final_html, height=1200, scrolling=True)

# ---------------------------------------------------------
# 모드 2: 문항 관리 (기존 입력 폼 및 엑셀 도우미 전체 유지)
# ---------------------------------------------------------
elif mode == "🛠️ 문항 관리":
    st.header("🛠️ 문항 관리 및 엑셀 표 도우미")
    all_df = st.session_state.df
    sel_sess = st.radio("교시 선택", ["1교시", "2교시"], horizontal=True)
    target_df = all_df[all_df['id'] < 200] if "1교시" in sel_sess else all_df[all_df['id'] >= 200]
    q_idx = st.selectbox("문항 선택", target_df.index, format_func=lambda x: f"{int(all_df.loc[x, 'id']) % 100}번 문제")
    
    df = all_df.copy()
    tab1, tab2, tab3 = st.tabs(["📄 문제 내용", "🔢 보기 및 이미지", "💡 엑셀 표 도우미"])
    with tab1:
        c1, c2 = st.columns([2, 1])
        with c1:
            df.at[q_idx, 'subject'] = st.text_input("과목명", value=clean_val(df.loc[q_idx, 'subject']), key=f"s_{q_idx}")
            df.at[q_idx, 'question'] = st.text_area("문제 지문", value=clean_val(df.loc[q_idx, 'question']), height=100, key=f"q_{q_idx}")
            df.at[q_idx, 'case_box'] = st.text_area("사례 박스", value=clean_val(df.loc[q_idx, 'case_box']), height=150, key=f"c_{q_idx}")
        with c2:
            m_f = st.file_uploader("메인 이미지", type=['png','jpg','jpeg'], key=f"m_{q_idx}")
            if m_f:
                with open(os.path.join(IMAGE_DIR, m_f.name), "wb") as f: f.write(m_f.getbuffer())
                df.at[q_idx, 'img'] = f"images/{m_f.name}:C"
    with tab2:
        df.at[q_idx, 'answer'] = st.number_input("정답", 1, 5, value=int(float(clean_val(df.loc[q_idx, 'answer']) or 1)))
        for i in range(1, 6):
            col_t, col_i = st.columns([2, 1])
            df.at[q_idx, f'option{i}'] = col_t.text_input(f"보기 {i}", value=clean_val(df.loc[q_idx, f'option{i}']), key=f"ot{i}_{q_idx}")
            o_f = col_i.file_uploader(f"보기{i}이미지", type=['png','jpg','jpeg'], key=f"ou{i}_{q_idx}")
            if o_f:
                with open(os.path.join(IMAGE_DIR, o_f.name), "wb") as f: f.write(o_f.getbuffer())
                df.at[q_idx, f'opt_img{i}'] = f"images/{o_f.name}"
    with tab3:
        excel_in = st.text_area("엑셀 내용 복사/붙여넣기")
        if excel_in:
            md = ""
            for l in excel_in.strip().split('\n'): md += "| " + " | ".join(l.split('\t')) + " |\n"
            st.code(md)
            if st.button("사례 박스에 적용"): df.at[q_idx, 'case_box'] = md; st.success("적용 완료")
    if st.button("💾 저장하기", use_container_width=True):
        st.session_state.df = df
        df.to_csv(DB_FILE, index=False); st.success("저장 성공!"); st.rerun()

# ---------------------------------------------------------
# 모드 3: 📊 성적 통계 센터
# ---------------------------------------------------------
else:
    st.header("📊 성적 분석 대시보드")
    if os.path.exists(RESULT_FILE):
        res_df = pd.read_csv(RESULT_FILE)
        res_df['timestamp'] = pd.to_datetime(res_df['timestamp'])
        c1, c2, c3 = st.columns(3)
        c1.metric("총 응시 인원", f"{len(res_df)}명")
        c2.metric("전체 평균 점수", f"{res_df['score'].mean():.1f}점")
        if len(res_df) > 1:
            diff = res_df.iloc[-1]['score'] - res_df.iloc[-2]['score']
            c3.metric("최근 시험 대비", f"{res_df.iloc[-1]['score']}점", f"{diff:+.1f}점")
        st.line_chart(res_df.set_index('timestamp')['score'])
    else: st.info("기록이 없습니다.")
    with st.expander("📝 수동 기록 추가"):
        s = st.number_input("점수", 0, 100, 80)
        if st.button("추가"):
            new = pd.DataFrame([{"timestamp": datetime.now(), "score": s}])
            new.to_csv(RESULT_FILE, mode='a', header=not os.path.exists(RESULT_FILE), index=False); st.rerun()
