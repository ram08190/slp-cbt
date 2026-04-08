import streamlit as st
import pandas as pd
import json
import os

# 1. 페이지 설정
st.set_page_config(page_title="언어재활사 전문 CBT", layout="wide")

# 2. 데이터 로드 및 초기화
DB_FILE = "quiz_db.csv"

def load_data():
    if os.path.exists(DB_FILE):
        df = pd.read_csv(DB_FILE)
        # 만약 'id' 컬럼이 없으면 인덱스 번호를 기준으로 새로 만듭니다.
        if 'id' not in df.columns:
            df['id'] = range(1, len(df) + 1)
        # 다른 필수 컬럼들이 없는 경우를 대비해 빈 값으로 채워줍니다.
        for col in ["question", "case_box", "option1", "option2", "option3", "option4", "option5", "answer", "image_path"]:
            if col not in df.columns:
                df[col] = ""
        return df
    else:
        # 파일이 아예 없는 경우 기본 예시 데이터 생성
        df = pd.DataFrame({
            "id": [1],
            "question": ["문제를 입력해주세요."],
            "case_box": ["사례를 입력해주세요."],
            "option1": ["보기1"], "option2": ["보기2"], "option3": ["보기3"], "option4": ["보기4"], "option5": ["보기5"],
            "answer": ["1"],
            "image_path": [""]
        })
        df.to_csv(DB_FILE, index=False)
        return df

# 데이터 불러오기
df = load_data()

# 사이드바 메뉴
st.sidebar.title("🎮 CBT 관리자")
mode = st.sidebar.radio("메뉴 선택", ["📝 시험 시작 (CBT)", "🛠️ 문항 수정/관리"])

# ---------------------------------------------------------
# 모드 1: 시험 시작
# ---------------------------------------------------------
if mode == "📝 시험 시작 (CBT)":
    st.subheader("🎓 언어재활사 국가고시 실전 시뮬레이션")
    
    if df.empty:
        st.warning("수정 모드에서 문제를 먼저 입력해주세요!")
    else:
        questions_list = []
        for _, row in df.iterrows():
            # 안전하게 데이터를 추출 (KeyError 방지)
            try:
                questions_list.append({
                    "id": int(row.get('id', 0)),
                    "text": str(row.get('question', '')),
                    "passage": str(row.get('case_box', '')) if pd.notna(row.get('case_box')) else "",
                    "options": [
                        str(row.get('option1', '')), 
                        str(row.get('option2', '')), 
                        str(row.get('option3', '')), 
                        str(row.get('option4', '')), 
                        str(row.get('option5', ''))
                    ],
                    "answer": int(float(row.get('answer', 1))) if row.get('answer') != "" else 1,
                    "img": str(row.get('image_path', '')) if pd.notna(row.get('image_path')) else ""
                })
            except:
                continue # 오류 있는 문항은 건너뜀

        json_data = json.dumps(questions_list, ensure_ascii=False)

        cbt_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <script src="https://cdn.tailwindcss.com"></script>
            <style>
                @import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@400;600;700&display=swap');
                body {{ font-family: 'Pretendard', sans-serif; background-color: #ffffff; color: #1e293b; overflow: hidden; }}
                .passage-box-container {{ 
                    margin-bottom: 1.25rem; border: 2px solid black; background-color: white; 
                    padding: 1.5rem; white-space: pre-wrap; word-wrap: break-word; line-height:1.6;
                }}
                .opt-item {{ cursor: pointer; padding: 10px; border-radius: 8px; transition: 0.2s; border: 1px solid transparent; }}
                .opt-item:hover {{ background-color: #f1f5f9; }}
                .selected {{ background-color: #eff6ff; border-color: #3b82f6; }}
                .opt-num {{ width: 28px; height: 28px; border-radius: 50%; border: 1.5px solid #cbd5e1; display: flex; align-items: center; justify-content: center; font-weight: bold; flex-shrink: 0; }}
            </style>
        </head>
        <body class="flex flex-col h-screen">
            <header class="bg-[#002855] text-white h-14 flex items-center justify-between px-6 shadow-md shrink-0">
                <h1 class="font-bold text-lg">언어재활사 CBT 실전모드</h1>
                <div id="timer" class="font-mono text-xl font-bold text-emerald-400">75:00</div>
                <button onclick="alert('제출되었습니다. 점수 계산 로직을 확인하세요.')" class="bg-red-600 px-4 py-1 rounded font-bold text-sm">제출</button>
            </header>
            
            <main class="flex-1 flex overflow-hidden">
                <div id="question-area" class="flex-1 overflow-y-auto p-10 bg-white"></div>
                <aside class="w-64 bg-slate-50 border-l p-4 flex flex-col overflow-hidden">
                    <div class="font-bold mb-4 text-slate-700">답안 표기란 (OMR)</div>
                    <div id="omr-grid" class="grid grid-cols-4 gap-2 overflow-y-auto pr-2"></div>
                </aside>
            </main>

            <footer class="h-16 border-t flex items-center justify-center gap-10 bg-slate-50 shrink-0">
                <button onclick="prev()" class="px-8 py-2 bg-white border rounded-xl font-bold hover:bg-slate-100">◀ 이전</button>
                <div class="font-bold text-lg"><span id="curr-idx">1</span> / <span id="total-idx">0</span></div>
                <button onclick="next()" class="px-8 py-2 bg-[#002855] text-white rounded-xl font-bold hover:bg-[#003a7a]">다음 ▶</button>
            </footer>

            <script>
                const QUESTIONS = {json_data};
                let currIdx = 0;
                let userAns = {{}};

                function render() {{
                    if(QUESTIONS.length === 0) return;
                    const q = QUESTIONS[currIdx];
                    const area = document.getElementById('question-area');
                    const selected = userAns[q.id];

                    let html = `
                        <div class="max-w-3xl mx-auto">
                            <div class="text-blue-600 font-bold mb-2">문제 ${{q.id}}</div>
                            <div class="text-xl font-bold mb-6" style="white-space: pre-wrap;">${{q.text}}</div>
                            ${{q.passage ? `<div class="passage-box-container">${{q.passage}}</div>` : ''}}
                            <div class="space-y-3 mt-8">
                    `;

                    q.options.forEach((opt, i) => {{
                        const num = i + 1;
                        html += `
                            <div onclick="selectAns(${{q.id}}, ${{num}})" class="opt-item flex items-center gap-4 ${{selected === num ? 'selected' : ''}}">
                                <div class="opt-num ${{selected === num ? 'bg-blue-600 text-white border-blue-600' : 'bg-white text-slate-400'}}">${{num}}</div>
                                <div class="font-medium ${{selected === num ? 'text-blue-700' : ''}}">${{opt}}</div>
                            </div>
                        `;
                    }});

                    html += `</div></div>`;
                    area.innerHTML = html;
                    document.getElementById('curr-idx').innerText = currIdx + 1;
                    document.getElementById('total-idx').innerText = QUESTIONS.length;
                    renderOMR();
                }}

                function selectAns(qId, num) {{ userAns[qId] = num; render(); }}
                function next() {{ if(currIdx < QUESTIONS.length - 1) {{ currIdx++; render(); }} }}
                function prev() {{ if(currIdx > 0) {{ currIdx--; render(); }} }}
                
                function renderOMR() {{
                    const grid = document.getElementById('omr-grid');
                    grid.innerHTML = '';
                    QUESTIONS.forEach((q, idx) => {{
                        const ans = userAns[q.id] || '';
                        grid.innerHTML += `
                            <button onclick="currIdx=${{idx}};render();" class="h-10 border rounded font-bold text-xs ${{idx===currIdx ? 'ring-2 ring-blue-500' : ''}} ${{ans ? 'bg-[#002855] text-white' : 'bg-white text-slate-300'}}">
                                ${{q.id}}<br>${{ans}}
                            </button>`;
                    }});
                }}

                window.onload = render;
            </script>
        </body>
        </html>
        """
        import streamlit.components.v1 as components
        components.html(cbt_html, height=850, scrolling=False)

# ---------------------------------------------------------
# 모드 2: 문항 수정/관리
# ---------------------------------------------------------
else:
    st.header("🛠️ 문항 개별 수정 및 보완")
    
    if st.button("➕ 새로운 문제 추가"):
        new_row = {"id": len(df) + 1, "question": "새 문제", "case_box": "", "option1": "", "option2": "", "option3": "", "option4": "", "option5": "", "answer": "1", "image_path": ""}
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        df.to_csv(DB_FILE, index=False)
        st.rerun()

    selected_idx = st.selectbox("수정할 문제를 선택하세요", df.index, format_func=lambda x: f"{df.loc[x, 'id']}번 문제")
    curr_q = df.loc[selected_idx]

    col1, col2 = st.columns(2)
    with col1:
        new_id = st.number_input("문제 번호(ID)", value=int(curr_q['id']))
        new_q = st.text_area("문제 지문", value=str(curr_q['question']), height=100)
        new_case = st.text_area("사례(Box) 내용", value=str(curr_q['case_box']), height=200)
    
    with col2:
        o1 = st.text_input("보기 1", value=str(curr_q['option1']))
        o2 = st.text_input("보기 2", value=str(curr_q['option2']))
        o3 = st.text_input("보기 3", value=str(curr_q['option3']))
        o4 = st.text_input("보기 4", value=str(curr_q['option4']))
        o5 = st.text_input("보기 5", value=str(curr_q['option5']))
        
        # 정답 값 처리 (오류 방지)
        try:
            val_ans = int(float(curr_q['answer']))
        except:
            val_ans = 1
        new_ans = st.number_input("정답 (1-5)", min_value=1, max_value=5, value=val_ans)

    if st.button("💾 변경사항 저장하기", use_container_width=True):
        df.at[selected_idx, 'id'] = new_id
        df.at[selected_idx, 'question'] = new_q
        df.at[selected_idx, 'case_box'] = new_case
        df.at[selected_idx, 'option1'] = o1
        df.at[selected_idx, 'option2'] = o2
        df.at[selected_idx, 'option3'] = o3
        df.at[selected_idx, 'option4'] = o4
        df.at[selected_idx, 'option5'] = o5
        df.at[selected_idx, 'answer'] = str(new_ans)
        
        df.to_csv(DB_FILE, index=False)
        st.success("저장되었습니다!")
        st.rerun()
