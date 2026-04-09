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

# [데이터 로드] 2급 규격 (1교시 80, 2교시 70)
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
# 모드 1: 시험 시작 (바둑판 범주화 모달 주입)
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
        
        # 🌟 바둑판(Grid) 디자인과 개수 자동 계산 로직 주입
        final_inject = f"""
        <style>
            #exam-filter-modal {{ display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.7); z-index: 9999; align-items: center; justify-content: center; padding: 20px; font-family: 'Pretendard', sans-serif; }}
            .f-win {{ background: #f1f5f9; width: 100%; max-width: 1050px; height: 85vh; border-radius: 24px; display: flex; flex-direction: column; overflow: hidden; box-shadow: 0 25px 50px -12px rgba(0,0,0,0.5); }}
            .f-header {{ background: #002855; color: white; padding: 20px 30px; display: flex; justify-content: space-between; align-items: center; }}
            .f-tabs {{ display: flex; background: white; border-bottom: 2px solid #e2e8f0; }}
            .f-tab {{ flex: 1; padding: 18px; text-align: center; cursor: pointer; font-weight: 800; color: #94a3b8; border-bottom: 5px solid transparent; transition: 0.3s; }}
            .f-tab.active {{ color: #002855; border-bottom-color: #002855; background: #f0f7ff; }}
            .f-body {{ flex: 1; overflow-y: auto; padding: 25px; display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 15px; align-content: start; }}
            .f-card {{ background: white; padding: 18px; border-radius: 12px; border: 1.5px solid #e2e8f0; cursor: pointer; position: relative; transition: 0.2s; }}
            .f-card:hover {{ border-color: #002855; transform: translateY(-3px); box-shadow: 0 10px 15px rgba(0,0,0,0.1); }}
            .f-badge {{ background: #e11d48; color: white; padding: 3px 10px; border-radius: 6px; font-size: 13px; font-weight: bold; margin-bottom: 10px; display: inline-block; }}
            .f-status {{ float: right; font-size: 13px; font-weight: bold; color: #002855; }}
            .f-text {{ font-size: 14px; color: #334155; line-height: 1.5; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }}
        </style>

        <div id="exam-filter-modal">
            <div class="f-win">
                <div class="f-header"><h2 style="margin:0; font-size:22px;">문제 보기</h2><button onclick="closeExamFilter()" style="color:white; background:none; border:none; font-size:32px; cursor:pointer;">&times;</button></div>
                <div class="f-tabs">
                    <div id="tab-all" class="f-tab active" onclick="updateExamFilter('all')">전체 문제 (<span id="cnt-all">0</span>)</div>
                    <div id="tab-checked" class="f-tab" onclick="updateExamFilter('checked')">체크 문제 (<span id="cnt-checked">0</span>)</div>
                    <div id="tab-unsolved" class="f-tab" onclick="updateExamFilter('unsolved')">안 푼 문제 (<span id="cnt-unsolved">0</span>)</div>
                </div>
                <div id="f-list-area" class="f-body"></div>
            </div>
        </div>

        <script>
            window.QUESTIONS_S1 = {json.dumps(s1_list, ensure_ascii=False)};
            window.QUESTIONS_S2 = {json.dumps(s2_list, ensure_ascii=False)};
            window.CONCEPT_DATABASE = {json.dumps(concept_db, ensure_ascii=False)};
            window.checkList = window.checkList || new Set();

            function openExamFilter(type) {{
                const modal = document.getElementById('exam-filter-modal');
                modal.style.display = 'flex';
                
                const qs = (window.currentSession === 2) ? window.QUESTIONS_S2 : window.QUESTIONS_S1;
                document.getElementById('cnt-all').innerText = qs.length;
                document.getElementById('cnt-checked').innerText = window.checkList ? window.checkList.size : 0;
                document.getElementById('cnt-unsolved').innerText = qs.filter(q => !window.userAns[window.currentSession][q.id]).length;
                
                updateExamFilter(type);
            }}

            function closeExamFilter() {{ document.getElementById('exam-filter-modal').style.display = 'none'; }}

            function updateExamFilter(type) {{
                document.querySelectorAll('.f-tab').forEach(t => t.classList.remove('active'));
                document.getElementById('tab-' + type).classList.add('active');
                
                const qs = (window.currentSession === 2) ? window.QUESTIONS_S2 : window.QUESTIONS_S1;
                const area = document.getElementById('f-list-area');
                area.innerHTML = '';

                let filtered = qs;
                if(type === 'checked') filtered = qs.filter(q => window.checkList && window.checkList.has(q.id));
                if(type === 'unsolved') filtered = qs.filter(q => !window.userAns[window.currentSession][q.id]);

                filtered.forEach(q => {{
                    const solved = window.userAns[window.currentSession][q.id] ? "✅ 풀음" : "❓ 안품";
                    const card = document.createElement('div');
                    card.className = 'f-card';
                    card.onclick = () => {{ window.currIdx = qs.findIndex(x => x.id === q.id); window.render(); closeExamFilter(); }};
                    card.innerHTML = `<div class="f-badge">${{q.id}}</div><span class="f-status">${{solved}}</span><div class="f-text">${{q.text}}</div>`;
                    area.appendChild(card);
                }});
            }}

            // 🌟 푸터 버튼들에 필터 함수 강제 주입 (0.8초 후 실행하여 우선권 선점)
            window.addEventListener('load', () => {{
                setTimeout(() => {{
                    document.querySelectorAll('button').forEach(b => {{
                        const t = b.innerText;
                        if(t.includes('전체 문제')) b.onclick = () => openExamFilter('all');
                        if(t.includes('체크 문제')) b.onclick = () => openExamFilter('checked');
                        if(t.includes('안 푼 문제')) b.onclick = () => openExamFilter('unsolved');
                    }});
                }}, 800);
            }});
        </script>
        """
        # 기존 스크립트 파일 호출 태그를 완전히 제거하여 충돌 방지
        clean_html = base_html.replace('<script src="questions1.js"></script>', '')\
                              .replace('<script src="questions2.js"></script>', '')\
                              .replace('<script src="database.js"></script>', '')
        
        final_html = clean_html.replace('</body>', final_inject + '</body>')
        st.components.v1.html(final_html, height=1300, scrolling=True)

# ---------------------------------------------------------
# 모드 2: 문항 관리
# ---------------------------------------------------------
elif mode == "🛠️ 문항 관리":
    st.header("🛠️ 문항 및 엑셀 표 관리")
    all_df = st.session_state.df
    sel_sess = st.radio("교시 선택", ["1교시", "2교시"], horizontal=True)
    target_df = all_df[all_df['id'] < 200] if "1교시" in sel_sess else all_df[all_df['id'] >= 200]
    q_idx = st.selectbox("문항 선택", target_df.index, format_func=lambda x: f"{int(all_df.loc[x, 'id']) % 100}번 문제")
    
    df = all_df.copy()
    tab1, tab2, tab3 = st.tabs(["📄 문제 내용", "🔢 보기 및 이미지", "💡 엑셀 표 도우미"])
    with tab1:
        df.at[q_idx, 'subject'] = st.text_input("과목명", value=clean_val(df.loc[q_idx, 'subject']), key=f"s_{q_idx}")
        df.at[q_idx, 'question'] = st.text_area("문제 지문", value=clean_val(df.loc[q_idx, 'question']), key=f"q_{q_idx}")
        df.at[q_idx, 'case_box'] = st.text_area("사례 박스", value=clean_val(df.loc[q_idx, 'case_box']), height=150, key=f"c_{q_idx}")
    with tab2:
        df.at[q_idx, 'answer'] = st.number_input("정답", 1, 5, value=int(float(clean_val(df.loc[q_idx, 'answer']) or 1)))
        for i in range(1, 6):
            col_t, col_i = st.columns([2, 1])
            df.at[q_idx, f'option{i}'] = col_t.text_input(f"보기 {i}", value=clean_val(df.loc[q_idx, f'option{i}']), key=f"ot{i}_{q_idx}")
            o_f = col_i.file_uploader(f"이미지{i}", type=['png','jpg','jpeg'], key=f"ou{i}_{q_idx}")
            if o_f:
                with open(os.path.join(IMAGE_DIR, o_f.name), "wb") as f: f.write(o_f.getbuffer())
                df.at[q_idx, f'opt_img{i}'] = f"images/{o_f.name}"
    with tab3:
        excel_in = st.text_area("엑셀 붙여넣기")
        if excel_in:
            md = ""
            for l in excel_in.strip().split('\n'): md += "| " + " | ".join(l.split('\t')) + " |\n"
            st.code(md)
            if st.button("적용"): df.at[q_idx, 'case_box'] = md; st.success("적용!")
    if st.button("💾 저장하기", use_container_width=True):
        st.session_state.df = df
        df.to_csv(DB_FILE, index=False); st.rerun()

# ---------------------------------------------------------
# 모드 3: 성적 통계
# ---------------------------------------------------------
else:
    st.header("📊 성적 통계 센터")
    if os.path.exists(RESULT_FILE):
        res_df = pd.read_csv(RESULT_FILE)
        st.metric("총 응시 인원", f"{len(res_df)}명")
        st.line_chart(res_df['score'])
    else: st.info("데이터가 없습니다.")
