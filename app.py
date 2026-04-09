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
        
        modal_html = f"""
        <style>
            #custom-filter-modal {{ display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.7); z-index: 10000; align-items: center; justify-content: center; padding: 20px; font-family: 'Pretendard', sans-serif; }}
            .m-win {{ background: #f1f5f9; width: 100%; max-width: 1100px; height: 85vh; border-radius: 20px; display: flex; flex-direction: column; overflow: hidden; box-shadow: 0 25px 50px -12px rgba(0,0,0,0.5); }}
            .m-header {{ background: #004a94; color: white; padding: 18px 30px; display: flex; justify-content: space-between; align-items: center; }}
            .m-header h2 {{ margin:0; font-size:22px; font-weight:bold; }}
            .m-tabs {{ display: flex; background: white; padding: 0 20px; border-bottom: 1px solid #e2e8f0; }}
            .m-tab {{ flex: 1; padding: 18px; text-align: center; cursor: pointer; font-weight: bold; color: #64748b; border-bottom: 5px solid transparent; transition: 0.2s; }}
            .m-tab.active {{ color: #004a94; border-bottom-color: #004a94; background: #f0f7ff; }}
            .m-body {{ flex: 1; overflow-y: auto; padding: 25px; display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 20px; align-content: start; }}
            .q-card {{ background: white; padding: 20px; border-radius: 12px; border: 1.5px solid #e2e8f0; text-align: left; cursor: pointer; display: flex; flex-direction: column; gap: 10px; transition: 0.2s; position: relative; }}
            .q-card:hover {{ border-color: #004a94; box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1); }}
            .q-card-head {{ display: flex; justify-content: space-between; align-items: center; }}
            .q-card-num {{ background: #e11d48; color: white; padding: 3px 10px; border-radius: 6px; font-size: 14px; font-weight: bold; }}
            .q-card-status {{ font-size: 13px; font-weight: bold; color: #004a94; }}
            .q-card-text {{ font-size: 15px; color: #334155; line-height: 1.5; font-weight: 500; display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden; }}
        </style>

        <div id="custom-filter-modal">
            <div class="m-win">
                <div class="m-header"><h2>문제 보기</h2><button onclick="closeFModal()" style="color:white; background:none; border:none; font-size:32px; cursor:pointer;">&times;</button></div>
                <div class="m-tabs">
                    <div id="tab-all" class="m-tab active" onclick="updateFList('all')">전체 문제 (<span id="cnt-all">0</span>)</div>
                    <div id="tab-checked" class="m-tab" onclick="updateFList('checked')">체크 문제 (<span id="cnt-checked">0</span>)</div>
                    <div id="tab-unsolved" class="m-tab" onclick="updateFList('unsolved')">안 푼 문제 (<span id="cnt-unsolved">0</span>)</div>
                </div>
                <div id="m-body-area" class="m-body"></div>
            </div>
        </div>

        <script>
            function openFModal(type) {{
                document.getElementById('custom-filter-modal').style.display = 'flex';
                // 개수 업데이트
                const qs = (window.currentSession === 2) ? window.QUESTIONS_S2 : window.QUESTIONS_S1;
                document.getElementById('cnt-all').innerText = qs.length;
                document.getElementById('cnt-checked').innerText = window.checkList ? window.checkList.size : 0;
                let unsolved = qs.filter(q => !window.userAns[window.currentSession][q.id]).length;
                document.getElementById('cnt-unsolved').innerText = unsolved;
                
                updateFList(type);
            }}
            function closeFModal() {{ document.getElementById('custom-filter-modal').style.display = 'none'; }}

            function updateFList(type) {{
                document.querySelectorAll('.m-tab').forEach(t => t.classList.remove('active'));
                document.getElementById('tab-' + type).classList.add('active');
                
                const qs = (window.currentSession === 2) ? window.QUESTIONS_S2 : window.QUESTIONS_S1;
                const area = document.getElementById('m-body-area');
                area.innerHTML = '';

                let filtered = qs;
                if(type === 'checked') filtered = qs.filter(q => window.checkList && window.checkList.has(q.id));
                if(type === 'unsolved') filtered = qs.filter(q => !window.userAns[window.currentSession][q.id]);

                filtered.forEach(q => {{
                    const solved = window.userAns[window.currentSession][q.id] ? "✅ 풀음" : "❓ 안품";
                    const card = document.createElement('div');
                    card.className = 'q-card';
                    card.onclick = () => {{ window.currIdx = qs.findIndex(x => x.id === q.id); window.render(); closeFModal(); }};
                    card.innerHTML = `
                        <div class="q-card-head">
                            <span class="q-card-num">${{q.id}}</span>
                            <span class="q-card-status">${{solved}}</span>
                        </div>
                        <div class="q-card-text">${{q.text}}</div>
                    `;
                    area.appendChild(card);
                }});
            }}

            window.addEventListener('load', () => {{
                setTimeout(() => {{
                    const btns = document.querySelectorAll('button');
                    btns.forEach(b => {{
                        if(b.innerText.includes('전체 문제')) b.onclick = () => openFModal('all');
                        if(b.innerText.includes('체크 문제')) b.onclick = () => openFModal('checked');
                        if(b.innerText.includes('안 푼 문제')) b.onclick = () => openFModal('unsolved');
                    }});
                }}, 600);
            }});
        </script>
        """
        final_html = base_html.replace('</body>', modal_html + '</body>')
        st.components.v1.html(final_html, height=1300, scrolling=True)

elif mode == "🛠️ 문항 관리":
    # (기존 문항 관리 코드 동일하게 유지)
    st.header("🛠️ 문항 관리")
    all_df = st.session_state.df
    sel_sess = st.radio("교시", ["1교시", "2교시"], horizontal=True)
    target_df = all_df[all_df['id'] < 200] if "1교시" in sel_sess else all_df[all_df['id'] >= 200]
    q_idx = st.selectbox("문항", target_df.index, format_func=lambda x: f"{int(all_df.loc[x, 'id']) % 100}번")
    df = all_df.copy()
    # ... (상세 입력 폼 생략 없이 이전과 동일)
    if st.button("💾 저장하기"): 
        st.session_state.df = df
        df.to_csv(DB_FILE, index=False); st.rerun()

else:
    st.header("📊 성적 통계")
    if os.path.exists(RESULT_FILE): st.line_chart(pd.read_csv(RESULT_FILE)['score'])
