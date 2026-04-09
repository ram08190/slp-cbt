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

if not os.path.exists(IMAGE_DIR): 
    os.makedirs(IMAGE_DIR)

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
        try:
            df = pd.read_csv(DB_FILE, keep_default_na=False).astype(object)
            df['id'] = pd.to_numeric(df['id'], errors='coerce').fillna(0).astype(int)
            # 유효한 ID만 필터링
            df = df[df['id'].isin(all_target_ids)]
            # 부족한 ID 채우기
            existing_ids = df['id'].tolist()
            missing_ids = [i for i in all_target_ids if i not in existing_ids]
            if missing_ids:
                new_rows = []
                for m_id in missing_ids:
                    row = {col: "" for col in required_cols}
                    row["id"] = m_id
                    row["session"] = "1" if m_id < 200 else "2"
                    new_rows.append(row)
                df = pd.concat([df, pd.DataFrame(new_rows)], ignore_index=True)
            return df.sort_values('id').reset_index(drop=True).astype(object)
        except:
            return pd.DataFrame([{"id": i, "session": "1" if i < 200 else "2"} for i in all_target_ids])
    else:
        return pd.DataFrame([{"id": i, "session": "1" if i < 200 else "2"} for i in all_target_ids])

if 'df' not in st.session_state:
    st.session_state.df = load_data()

def clean_val(x):
    s = str(x).strip()
    return "" if s.lower() in ['nan', 'none', ''] else s

# --- 사이드바 메뉴 ---
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
            q_obj = {
                "id": real_id % 100,
                "subject": clean_val(row.get('subject', '')),
                "text": clean_val(row.get('question', '')),
                "passage": clean_val(row.get('case_box', '')),
                "answer": int(float(clean_val(row.get('answer', 1)) or 1)),
                "img": clean_val(row.get('img', '')),
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
        
        # 🌟 바둑판 필터 스크립트 강제 주입
        inject_code = f"""
        <style>
            #custom-grid-panel {{ display: none !important; position: fixed; inset: 0; background: rgba(0,0,0,0.8); z-index: 99999; align-items: center; justify-content: center; padding: 20px; }}
            .g-win {{ background: #f1f5f9; width: 100%; max-width: 1000px; height: 80vh; border-radius: 20px; display: flex; flex-direction: column; overflow: hidden; }}
            .g-header {{ background: #002855; color: white; padding: 15px 25px; display: flex; justify-content: space-between; align-items: center; }}
            .g-tabs {{ display: flex; background: white; border-bottom: 2px solid #cbd5e1; }}
            .g-tab {{ flex: 1; padding: 15px; text-align: center; font-weight: 800; color: #94a3b8; cursor: pointer; }}
            .g-tab.active {{ color: #002855; border-bottom: 5px solid #002855; background: #f0f9ff; }}
            .g-body {{ flex: 1; overflow-y: auto; padding: 25px; display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 15px; align-content: start; }}
            .g-card {{ background: white; padding: 15px; border-radius: 12px; border: 1.5px solid #e2e8f0; cursor: pointer; text-align: left; }}
            .g-card:hover {{ border-color: #002855; transform: translateY(-3px); }}
        </style>
        <div id="custom-grid-panel">
            <div class="g-win">
                <div class="g-header"><h3 style="margin:0">문제 전체보기</h3><button onclick="closeG()" style="background:none; border:none; color:white; font-size:30px; cursor:pointer;">&times;</button></div>
                <div class="g-tabs">
                    <div id="gt-all" class="g-tab active" onclick="updateG('all')">전체 문제 (<span id="gc-all">0</span>)</div>
                    <div id="gt-chk" class="g-tab" onclick="updateG('chk')">체크 문제 (<span id="gc-chk">0</span>)</div>
                    <div id="gt-un" class="g-tab" onclick="updateG('un')">안 푼 문제 (<span id="gc-un">0</span>)</div>
                </div>
                <div id="g-list" class="g-body"></div>
            </div>
        </div>
        <script>
            window.QUESTIONS_S1 = {json.dumps(s1_list, ensure_ascii=False)};
            window.QUESTIONS_S2 = {json.dumps(s2_list, ensure_ascii=False)};
            window.CONCEPT_DATABASE = {json.dumps(concept_db, ensure_ascii=False)};
            window.checkList = window.checkList || new Set();

            function openG(type) {{
                document.getElementById('custom-grid-panel').style.display = 'flex';
                const qs = (window.currentSession === 2) ? window.QUESTIONS_S2 : window.QUESTIONS_S1;
                document.getElementById('gc-all').innerText = qs.length;
                document.getElementById('gc-chk').innerText = window.checkList.size;
                document.getElementById('gc-un').innerText = qs.filter(q => !window.userAns[window.currentSession][q.id]).length;
                updateG(type);
            }}
            function closeG() {{ document.getElementById('custom-grid-panel').style.display = 'none'; }}
            function updateG(type) {{
                document.querySelectorAll('.g-tab').forEach(t => t.classList.remove('active'));
                const tid = type === 'all' ? 'gt-all' : (type === 'chk' ? 'gt-chk' : 'gt-un');
                document.getElementById(tid).classList.add('active');
                const qs = (window.currentSession === 2) ? window.QUESTIONS_S2 : window.QUESTIONS_S1;
                const area = document.getElementById('g-list'); area.innerHTML = '';
                let filtered = qs;
                if(type === 'chk') filtered = qs.filter(q => window.checkList.has(q.id));
                if(type === 'un') filtered = qs.filter(q => !window.userAns[window.currentSession][q.id]);
                filtered.forEach(q => {{
                    const card = document.createElement('div'); card.className = 'g-card';
                    card.onclick = () => {{ window.currIdx = qs.findIndex(x => x.id === q.id); window.render(); closeG(); }};
                    card.innerHTML = `<span style="background:#e11d48; color:white; padding:2px 6px; border-radius:4px; font-size:12px; margin-right:8px;">${{q.id}}</span><span style="font-size:14px; font-weight:600;">${{q.text.substring(0,30)}}...</span>`;
                    area.appendChild(card);
                }});
            }}
            setTimeout(() => {{
                document.querySelectorAll('button').forEach(b => {{
                    const t = b.innerText;
                    if(t.includes('전체 문제')) b.onclick = () => openG('all');
                    if(t.includes('체크 문제')) b.onclick = () => openG('chk');
                    if(t.includes('안 푼 문제')) b.onclick = () => openG('un');
                }});
                window.render();
            }}, 1000);
        </script>
        """
        # TypeError 방지를 위해 final_html을 문자열로 확실히 보장
        final_html = str(base_html).replace('</body>', inject_code + '</body>')
        st.components.v1.html(final_html, height=1200, scrolling=True)

# ---------------------------------------------------------
# 모드 2: 문항 관리 (탭 및 엑셀 도우미 전체 복구)
# ---------------------------------------------------------
elif mode == "🛠️ 문항 관리":
    st.header("🛠️ 문항 관리 도구")
    all_df = st.session_state.df
    sel_sess = st.radio("교시 선택", ["1교시", "2교시"], horizontal=True)
    target_df = all_df[all_df['id'] < 200] if "1교시" in sel_sess else all_df[all_df['id'] >= 200]
    q_idx = st.selectbox("수정할 문항", target_df.index, format_func=lambda x: f"{int(all_df.loc[x, 'id']) % 100}번 문제")
    
    df = all_df.copy()
    tab1, tab2, tab3 = st.tabs(["📄 지문 수정", "🔢 보기/이미지", "💡 엑셀 도우미"])
    with tab1:
        df.at[q_idx, 'subject'] = st.text_input("과목명", clean_val(df.loc[q_idx, 'subject']), key=f"s_{q_idx}")
        df.at[q_idx, 'question'] = st.text_area("문제 지문", clean_val(df.loc[q_idx, 'question']), key=f"q_{q_idx}")
        df.at[q_idx, 'case_box'] = st.text_area("사례 박스", clean_val(df.loc[q_idx, 'case_box']), key=f"c_{q_idx}")
    with tab2:
        df.at[q_idx, 'answer'] = st.number_input("정답", 1, 5, int(float(clean_val(df.loc[q_idx, 'answer']) or 1)))
        m_f = st.file_uploader("메인 이미지", type=['png','jpg','jpeg'], key=f"m_{q_idx}")
        if m_f:
            with open(os.path.join(IMAGE_DIR, m_f.name), "wb") as f: f.write(m_f.getbuffer())
            df.at[q_idx, 'img'] = f"images/{m_f.name}:C"
        for i in range(1, 6):
            df.at[q_idx, f'option{i}'] = st.text_input(f"보기 {i}", clean_val(df.loc[q_idx, f'option{i}']), key=f"ot{i}_{q_idx}")
    with tab3:
        excel_in = st.text_area("엑셀 내용 복사/붙여넣기")
        if excel_in:
            md = ""
            for l in excel_in.strip().split('\n'): md += "| " + " | ".join(l.split('\t')) + " |\n"
            st.code(md)
            if st.button("사례 박스에 적용"):
                df.at[q_idx, 'case_box'] = md; st.success("적용 완료")
    
    if st.button("💾 이 문항 저장하기", use_container_width=True):
        st.session_state.df = df
        df.to_csv(DB_FILE, index=False); st.success("저장 성공!"); st.rerun()

# ---------------------------------------------------------
# 모드 3: 성적 통계
# ---------------------------------------------------------
else:
    st.header("📊 성적 대시보드")
    if os.path.exists(RESULT_FILE):
        rdf = pd.read_csv(RESULT_FILE)
        st.metric("총 응시 인원", f"{len(rdf)}명")
        st.line_chart(rdf['score'])
    else: st.info("데이터가 없습니다.")
