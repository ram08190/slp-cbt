import streamlit as st
import pandas as pd
import json
import os
import time
from datetime import datetime

# 1. 페이지 설정
st.set_page_config(page_title="언어재활사 2급 통합 CBT", layout="wide")

DB_FILE = "quiz_db.csv"
RESULT_FILE = "results.csv"
HTML_FILE = "자동화.html"
IMAGE_DIR = "images"

if not os.path.exists(IMAGE_DIR): os.makedirs(IMAGE_DIR)

# [데이터 로드]
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
# 모드 1: 시험 시작 (데이터 매핑 보정 및 바둑판 주입)
# ---------------------------------------------------------
if mode == "📝 시험 시작":
    df = st.session_state.df
    s1_list, s2_list, concept_db = [], [], {}
    for _, row in df.iterrows():
        try:
            real_id = int(row['id'])
            # 🌟 HTML이 기대하는 변수명(text, passage, options)에 정확히 매핑
            q_obj = {
                "id": real_id % 100,
                "subject": clean_val(row.get('subject', '')),
                "text": clean_val(row.get('question', '')), # 지문
                "passage": clean_val(row.get('case_box', '')), # 사례
                "answer": int(float(clean_val(row.get('answer', 1)) or 1)),
                "img": clean_val(row.get('img', '')),
                # 🌟 보기 구조 최적화 (텍스트가 없으면 '내용 없음' 방지)
                "options": [
                    {"text": clean_val(row.get(f'option{i}', '')), "img": clean_val(row.get(f'opt_img{i}', ''))} 
                    for i in range(1, 6)
                ]
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
        
        # 🌟 바둑판 모달 + 강제 렌더링 보정 스크립트
        inject_script = f"""
        <style>
            #custom-grid-panel {{ display: none !important; position: fixed; inset: 0; background: rgba(0,0,0,0.85); z-index: 999999; align-items: center; justify-content: center; padding: 40px; }}
            .grid-container {{ background: #f8fafc; width: 100%; max-width: 1200px; height: 80vh; border-radius: 24px; display: flex; flex-direction: column; overflow: hidden; }}
            .grid-header {{ background: #002855; color: white; padding: 20px 30px; display: flex; justify-content: space-between; align-items: center; }}
            .grid-tabs {{ display: flex; background: white; border-bottom: 2px solid #e2e8f0; }}
            .grid-tab {{ flex: 1; padding: 20px; text-align: center; font-weight: 800; cursor: pointer; color: #94a3b8; }}
            .grid-tab.active {{ color: #002855; border-bottom: 5px solid #002855; background: #f1f7ff; }}
            .grid-content {{ flex: 1; overflow-y: auto; padding: 30px; display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 20px; align-content: start; }}
            .q-box {{ background: white; padding: 20px; border-radius: 12px; border: 1px solid #dee2e6; cursor: pointer; text-align: left; transition: 0.2s; }}
            .q-box:hover {{ border-color: #002855; box-shadow: 0 10px 15px rgba(0,0,0,0.1); }}
            .q-badge {{ background: #e11d48; color: white; padding: 3px 10px; border-radius: 6px; font-size: 13px; font-weight: bold; }}
            .q-status {{ float: right; font-size: 13px; font-weight: bold; color: #002855; }}
        </style>

        <div id="custom-grid-panel">
            <div class="grid-container">
                <div class="grid-header"><h2 style="margin:0">시험 문항 전체보기</h2><button onclick="closeGridPanel()" style="background:none; border:none; color:white; font-size:40px; cursor:pointer;">&times;</button></div>
                <div class="grid-tabs">
                    <div id="gt-all" class="grid-tab active" onclick="refreshGrid('all')">전체 문제 (<span id="gc-all">0</span>)</div>
                    <div id="gt-chk" class="grid-tab" onclick="refreshGrid('chk')">체크 문제 (<span id="gc-chk">0</span>)</div>
                    <div id="gt-un" class="grid-tab" onclick="refreshGrid('un')">안 푼 문제 (<span id="gc-un">0</span>)</div>
                </div>
                <div id="grid-list" class="grid-content"></div>
            </div>
        </div>

        <script>
            window.QUESTIONS_S1 = {json.dumps(s1_list, ensure_ascii=False)};
            window.QUESTIONS_S2 = {json.dumps(s2_list, ensure_ascii=False)};
            window.CONCEPT_DATABASE = {json.dumps(concept_db, ensure_ascii=False)};
            window.checkList = window.checkList || new Set();

            function openGridPanel(type) {{
                document.getElementById('custom-grid-panel').style.display = 'flex';
                const qs = (window.currentSession === 2) ? window.QUESTIONS_S2 : window.QUESTIONS_S1;
                document.getElementById('gc-all').innerText = qs.length;
                document.getElementById('gc-chk').innerText = window.checkList.size;
                document.getElementById('gc-un').innerText = qs.filter(q => !window.userAns[window.currentSession][q.id]).length;
                refreshGrid(type);
            }}

            function closeGridPanel() {{ document.getElementById('custom-grid-panel').style.display = 'none'; }}

            function refreshGrid(type) {{
                document.querySelectorAll('.grid-tab').forEach(t => t.classList.remove('active'));
                const tabId = type === 'all' ? 'gt-all' : (type === 'chk' ? 'gt-chk' : 'gt-un');
                document.getElementById(tabId).classList.add('active');
                
                const qs = (window.currentSession === 2) ? window.QUESTIONS_S2 : window.QUESTIONS_S1;
                const area = document.getElementById('grid-list');
                area.innerHTML = '';

                let filtered = qs;
                if(type === 'chk') filtered = qs.filter(q => window.checkList.has(q.id));
                if(type === 'un') filtered = qs.filter(q => !window.userAns[window.currentSession][q.id]);

                filtered.forEach(q => {{
                    const card = document.createElement('div');
                    card.className = 'q-box';
                    card.onclick = () => {{ window.currIdx = qs.findIndex(x => x.id === q.id); window.render(); closeGridPanel(); }};
                    const status = window.userAns[window.currentSession][q.id] ? "✅ 완료" : "❓ 미완료";
                    card.innerHTML = `<div class="q-badge">${{q.id}}</div><span class="q-status">${{status}}</span><div style="margin-top:10px; font-size:14px; color:#475569; overflow:hidden; text-overflow:ellipsis; display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;">${{q.text}}</div>`;
                    area.appendChild(card);
                }});
            }}

            // 🌟 하단 버튼 이벤트 가로채기
            setTimeout(() => {{
                document.querySelectorAll('button').forEach(b => {{
                    const t = b.innerText.trim();
                    if(t.includes('전체 문제')) b.onclick = () => openGridPanel('all');
                    if(t.includes('체크 문제')) b.onclick = () => openGridPanel('chk');
                    if(t.includes('안 푼 문제')) b.onclick = () => openGridPanel('un');
                }});
                window.render(); // 🌟 초기 렌더링 강제 실행 (지문 실종 방지)
            }}, 800);
        </script>
        """
        # 기존 스크립트 태그 제거 및 강제 주입
        clean_html = base_html.replace('<script src="questions1.js"></script>', '').replace('<script src="questions2.js"></script>', '').replace('<script src="database.js"></script>', '')
        final_html = clean_html.replace('</body>', inject_script + '</body>')
        st.components.v1.html(final_html, height=1200, scrolling=True, key=f"v_{time.time()}")

# --- (문항 관리 및 성적 통계는 이전 코드와 동일하게 유지) ---
elif mode == "🛠️ 문항 관리":
    st.header("🛠️ 문항 관리")
    all_df = st.session_state.df
    sel_sess = st.radio("교시", ["1교시", "2교시"], horizontal=True)
    target_df = all_df[all_df['id'] < 200] if "1교시" in sel_sess else all_df[all_df['id'] >= 200]
    q_idx = st.selectbox("수정 문항", target_df.index, format_func=lambda x: f"{int(all_df.loc[x, 'id']) % 100}번")
    
    df = all_df.copy()
    tab1, tab2, tab3 = st.tabs(["📄 문제 지문", "🔢 보기/이미지", "💡 엑셀 도우미"])
    with tab1:
        df.at[q_idx, 'subject'] = st.text_input("과목", clean_val(df.loc[q_idx, 'subject']))
        df.at[q_idx, 'question'] = st.text_area("지문", clean_val(df.loc[q_idx, 'question']))
        df.at[q_idx, 'case_box'] = st.text_area("사례", clean_val(df.loc[q_idx, 'case_box']))
    with tab2:
        df.at[q_idx, 'answer'] = st.number_input("정답", 1, 5, int(float(clean_val(df.loc[q_idx, 'answer']) or 1)))
        for i in range(1, 6):
            df.at[q_idx, f'option{i}'] = st.text_input(f"보기{i}", clean_val(df.loc[q_idx, f'option{i}']))
    if st.button("💾 저장하기"):
        st.session_state.df = df
        df.to_csv(DB_FILE, index=False); st.rerun()
else:
    st.header("📊 성적 통계")
    if os.path.exists(RESULT_FILE): st.line_chart(pd.read_csv(RESULT_FILE)['score'])
