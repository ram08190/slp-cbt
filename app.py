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

# ---------------------------------------------------------
# 모드 1: 시험 시작 (모달창 강제 주입 및 버튼 연결)
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
        
        # 🌟 필터 모달 HTML과 연동 스크립트를 body 태그 끝에 강제 삽입
        modal_html = f"""
        <style>
            #custom-filter-modal {{ display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.7); z-index: 10000; align-items: center; justify-content: center; padding: 20px; font-family: sans-serif; }}
            .m-win {{ background: white; width: 100%; max-width: 900px; height: 80vh; border-radius: 15px; display: flex; flex-direction: column; overflow: hidden; }}
            .m-header {{ background: #0055a5; color: white; padding: 15px 25px; display: flex; justify-content: space-between; align-items: center; font-weight: bold; font-size: 20px; }}
            .m-tabs {{ display: flex; background: #f8fafc; border-bottom: 1px solid #e2e8f0; }}
            .m-tab {{ flex: 1; padding: 15px; text-align: center; cursor: pointer; font-weight: bold; color: #64748b; border-bottom: 4px solid transparent; }}
            .m-tab.active {{ color: #0055a5; border-bottom-color: #0055a5; background: white; }}
            .m-body {{ flex: 1; overflow-y: auto; padding: 20px; background: #f1f5f9; display: grid; grid-template-columns: repeat(2, 1fr); gap: 15px; align-content: start; }}
            .q-item {{ background: white; padding: 15px; border-radius: 10px; border: 1px solid #e2e8f0; text-align: left; cursor: pointer; }}
            .q-item:hover {{ border-color: #0055a5; }}
            .q-num {{ background: #ef4444; color: white; padding: 2px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; margin-right: 10px; }}
        </style>

        <div id="custom-filter-modal">
            <div class="m-win">
                <div class="m-header"><span>문제 보기</span><button onclick="closeFModal()" style="color:white; background:none; border:none; font-size:30px; cursor:pointer;">&times;</button></div>
                <div class="m-tabs">
                    <div id="tab-all" class="m-tab active" onclick="updateFList('all')">전체 문제</div>
                    <div id="tab-checked" class="m-tab" onclick="updateFList('checked')">체크 문제</div>
                    <div id="tab-unsolved" class="m-tab" onclick="updateFList('unsolved')">안 푼 문제</div>
                </div>
                <div id="m-body-area" class="m-body"></div>
            </div>
        </div>

        <script>
            window.QUESTIONS_S1 = {json.dumps(s1_list, ensure_ascii=False)};
            window.QUESTIONS_S2 = {json.dumps(s2_list, ensure_ascii=False)};
            window.CONCEPT_DATABASE = {json.dumps(concept_db, ensure_ascii=False)};
            window.checkList = window.checkList || new Set();

            function openFModal(type) {{
                document.getElementById('custom-filter-modal').style.display = 'flex';
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
                if(type === 'checked') filtered = qs.filter(q => window.checkList.has(q.id));
                if(type === 'unsolved') filtered = qs.filter(q => !window.userAns[window.currentSession][q.id]);

                filtered.forEach(q => {{
                    const card = document.createElement('div');
                    card.className = 'q-item';
                    card.onclick = () => {{ window.currIdx = qs.findIndex(x => x.id === q.id); window.render(); closeFModal(); }};
                    card.innerHTML = `<span class="q-num">${{q.id}}</span><span style="font-weight:bold; font-size:14px; color:#334155;">${{q.text.substring(0,40)}}...</span>`;
                    area.appendChild(card);
                }});
            }}

            // 🌟 핵심: HTML 하단에 있는 기존 버튼들을 강제로 찾아 이벤트를 연결합니다.
            window.addEventListener('load', () => {{
                setTimeout(() => {{
                    const buttons = document.querySelectorAll('footer button, body button');
                    buttons.forEach(btn => {{
                        const txt = btn.innerText;
                        if(txt.includes('전체 문제')) btn.onclick = () => openFModal('all');
                        if(txt.includes('체크 문제')) btn.onclick = () => openFModal('checked');
                        if(txt.includes('안 푼 문제')) btn.onclick = () => openFModal('unsolved');
                    }});
                }}, 500);
            }});
        </script>
        """
        final_html = base_html.replace('</body>', modal_html + '</body>')\
                              .replace('<script src="questions1.js"></script>', '')\
                              .replace('<script src="questions2.js"></script>', '')\
                              .replace('<script src="database.js"></script>', '')
        
        st.components.v1.html(final_html, height=1300, scrolling=True)

# ---------------------------------------------------------
# 모드 2: 문항 관리 (생략 없이 통합 유지)
# ---------------------------------------------------------
elif mode == "🛠️ 문항 관리":
    st.header("🛠️ 문항 관리 시스템")
    all_df = st.session_state.df
    sel_sess = st.radio("교시 선택", ["1교시", "2교시"], horizontal=True)
    target_df = all_df[all_df['id'] < 200] if "1교시" in sel_sess else all_df[all_df['id'] >= 200]
    q_idx = st.selectbox("문항 선택", target_df.index, format_func=lambda x: f"{int(all_df.loc[x, 'id']) % 100}번 문제")
    df = all_df.copy()
    tab1, tab2, tab3 = st.tabs(["문제 내용", "보기 및 이미지", "엑셀 도우미"])
    with tab1:
        df.at[q_idx, 'subject'] = st.text_input("과목명", value=clean_val(df.loc[q_idx, 'subject']), key=f"s_{q_idx}")
        df.at[q_idx, 'question'] = st.text_area("문제 지문", value=clean_val(df.loc[q_idx, 'question']), key=f"q_{q_idx}")
        df.at[q_idx, 'case_box'] = st.text_area("사례 박스", value=clean_val(df.loc[q_idx, 'case_box']), key=f"c_{q_idx}")
    with tab2:
        df.at[q_idx, 'answer'] = st.number_input("정답", 1, 5, value=int(float(clean_val(df.loc[q_idx, 'answer']) or 1)))
        m_f = st.file_uploader("이미지", type=['png','jpg','jpeg'], key=f"m_{q_idx}")
        if m_f:
            with open(os.path.join(IMAGE_DIR, m_f.name), "wb") as f: f.write(m_f.getbuffer())
            df.at[q_idx, 'img'] = f"images/{m_f.name}:C"
        for i in range(1, 6):
            df.at[q_idx, f'option{i}'] = st.text_input(f"보기 {i}", value=clean_val(df.loc[q_idx, f'option{i}']), key=f"ot{i}_{q_idx}")
    with tab3:
        excel_in = st.text_area("엑셀 붙여넣기")
        if excel_in:
            md = ""
            for l in excel_in.strip().split('\n'): md += "| " + " | ".join(l.split('\t')) + " |\n"
            st.code(md)
            if st.button("적용"): df.at[q_idx, 'case_box'] = md; st.success("적용됨")
    if st.button("💾 저장하기", use_container_width=True):
        st.session_state.df = df
        df.to_csv(DB_FILE, index=False); st.success("저장 완료!"); st.rerun()

# ---------------------------------------------------------
# 모드 3: 성적 통계 센터
# ---------------------------------------------------------
else:
    st.header("📊 성적 통계 센터")
    if os.path.exists(RESULT_FILE):
        res_df = pd.read_csv(RESULT_FILE)
        st.metric("총 응시 인원", f"{len(res_df)}명")
        st.line_chart(res_df['score'])
    else: st.info("기록이 없습니다.")
