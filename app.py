import streamlit as st
import pandas as pd
import json
import os
import base64
from datetime import datetime

# 1. 페이지 설정
st.set_page_config(page_title="언어재활사 2급 통합 CBT", layout="wide")with t3:
DB_FILE = "quiz_db.csv"
RESULT_FILE = "results.csv"
HTML_FILE = "자동화.html"
IMAGE_DIR = "images"

if not os.path.exists(IMAGE_DIR): 
    os.makedirs(IMAGE_DIR)

# 🌟 이미지 데이터를 안전하게 추출하는 함수 (D드라이브 경로 세척 포함)
def get_image_data(img_path):
    if not img_path: return ""
    # 파일명만 추출 (D:\사진\01.png:C -> 01.png)
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
# 모드 1: 시험 시작 (TypeError 해결을 위한 안전한 HTML 주입)
# ---------------------------------------------------------
if mode == "📝 시험 시작":
    df = st.session_state.df
    s1_list, s2_list = [], []
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
        except: continue

    if os.path.exists(HTML_FILE):
        with open(HTML_FILE, "r", encoding="utf-8") as f:
            base_html = f.read()
        
        # 데이터를 JSON으로 직렬화한 후 HTML 하단에 안전하게 삽입
        data_json = json.dumps({"s1": s1_list, "s2": s2_list}, ensure_ascii=False)
        inject_script = f"""
        <script>
            const data = {data_json};
            window.QUESTIONS_S1 = data.s1;
            window.QUESTIONS_S2 = data.s2;
            setTimeout(() => {{ if(window.render) window.render(); }}, 500);
        </script>
        """
        # TypeError 방지를 위해 문자열 결합 방식을 가장 단순화
        final_html_str = base_html.replace('</body>', f'{inject_script}</body>')
        
        # 🌟 핵심: 명시적으로 str 타입으로 전달
        st.components.v1.html(str(final_html_str), height=1200, scrolling=True)

# ---------------------------------------------------------
# 모드 2: 문항 관리 (보기 이미지 업로드 기능 포함)
# ---------------------------------------------------------
# ---------------------------------------------------------
# 모드 2: 문항 관리 (들여쓰기 및 엑셀 도우미 완벽 수정)
# ---------------------------------------------------------
elif mode == "🛠️ 문항 관리":
    st.header("🛠️ 문항 관리 시스템")
    all_df = st.session_state.df
    sel_sess = st.radio("교시 선택", ["1교시", "2교시"], horizontal=True)
    target_df = all_df[all_df['id'] < 200] if "1교시" in sel_sess else all_df[all_df['id'] >= 200]
    q_idx = st.selectbox("수정할 문항 선택", target_df.index, format_func=lambda x: f"{int(all_df.loc[x, 'id']) % 100}번 문제")
    
    # 탭 생성
    t1, t2, t3 = st.tabs(["📄 문제 지문/이미지", "🔢 보기 및 정답", "💡 엑셀 표 도우미"])
    
    with t1:
        st.subheader("문제 기본 정보")
        all_df.at[q_idx, 'subject'] = st.text_input("과목명", clean_val(all_df.loc[q_idx, 'subject']), key=f"s_{q_idx}")
        all_df.at[q_idx, 'question'] = st.text_area("문제 지문 (질문)", clean_val(all_df.loc[q_idx, 'question']), height=100, key=f"q_{q_idx}")
        
        st.write("---")
        st.subheader("사례 박스 (표/지문 추가 수정)")
        all_df.at[q_idx, 'case_box'] = st.text_area("사례 박스 내용", clean_val(all_df.loc[q_idx, 'case_box']), height=200, key=f"c_{q_idx}", help="엑셀 도우미에서 보낸 표가 여기로 들어옵니다. 여기서 직접 수정하세요!")
        
        st.write("---")
        st.subheader("🖼️ 메인 이미지 설정")
        m_f = st.file_uploader("사진 선택 (PC의 images 폴더 안의 파일을 선택하세요)", type=['png','jpg','jpeg'], key=f"m_{q_idx}")
        if m_f:
            # 서버 임시 폴더에 저장
            with open(os.path.join(IMAGE_DIR, m_f.name), "wb") as f:
                f.write(m_f.getbuffer())
            all_df.at[q_idx, 'img'] = f"images/{m_f.name}:C"
            st.success(f"현재 선택된 파일: {m_f.name}")

    with t2:
        st.subheader("정답 및 보기 관리")
        all_df.at[q_idx, 'answer'] = st.number_input("정답 번호 (1-5)", 1, 5, value=int(float(clean_val(all_df.loc[q_idx, 'answer']) or 1)))
        
        st.write("---")
        for i in range(1, 6):
            col_t, col_i = st.columns([3, 1])
            all_df.at[q_idx, f'option{i}'] = col_t.text_input(f"보기 {i} 텍스트", clean_val(all_df.loc[q_idx, f'option{i}']), key=f"ot{i}_{q_idx}")
            o_f = col_i.file_uploader(f"보기{i} 사진", type=['png','jpg','jpeg'], key=f"ou{i}_{q_idx}")
            if o_f:
                with open(os.path.join(IMAGE_DIR, o_f.name), "wb") as f:
                    f.write(o_f.getbuffer())
                all_df.at[q_idx, f'opt_img{i}'] = f"images/{o_f.name}"

   with t3:
        st.subheader("💡 엑셀 표 실시간 편집기")
        st.write("엑셀 내용을 붙여넣어 표를 만든 뒤, 아래 코드 창에서 직접 내용을 수정하며 결과를 확인하세요.")
        
        # 1. 엑셀 원본 붙여넣기 창
        excel_in = st.text_area("1. 엑셀 데이터를 여기에 붙여넣으세요", height=100, key="ex_input_box")
        
        # 🌟 로직 개선: 엑셀 내용이 바뀌면 마크다운 코드를 자동으로 생성함
        md_init_value = ""
        if excel_in:
            raw_text = excel_in.replace('"', '').strip()
            lines = raw_text.split('\n')
            if len(lines) > 0:
                md_list = []
                for i, line in enumerate(lines):
                    # 탭 또는 공백으로 분리
                    cols = [c.strip() for c in line.split('\t')]
                    md_list.append("| " + " | ".join(cols) + " |")
                    if i == 0:
                        md_list.append("| " + " | ".join(["---"] * len(cols)) + " |")
                md_init_value = "\n".join(md_list)

        st.write("---")
        
        # 2. 실시간 수정 창 (수정하는 즉시 아래 미리보기에 반영됨)
        # help: 엑셀 내용을 먼저 넣어야 아래 창에 코드가 나타납니다.
        edited_md = st.text_area(
            "2. 변환된 마크다운 코드를 직접 수정하세요:", 
            value=md_init_value, 
            height=250, 
            key="md_editor_box"
        )
        
        # 3. 실시간 결과 보기 (편집창 내용을 그대로 렌더링)
        st.write("▼ 현재 표 모양 (실시간 미리보기)")
        if edited_md:
            st.markdown(edited_md)
        else:
            st.info("엑셀 내용을 먼저 붙여넣어 주세요.")
            
        # 4. 최종 결정 버튼
        if st.button("🚀 이 결과물을 사례 박스에 최종 적용", use_container_width=True):
            if edited_md:
                all_df.at[q_idx, 'case_box'] = edited_md
                st.success("사례 박스에 적용되었습니다! '📄 지문/이미지' 탭에서 확인하세요.")
            else:
                st.warning("적용할 내용이 없습니다.")

    # 모든 탭 밖에서 공통 저장 버튼
    st.write("---")
    if st.button("💾 모든 수정사항 최종 저장하기", use_container_width=True):
        st.session_state.df = all_df
        all_df.to_csv(DB_FILE, index=False)
        st.success("데이터베이스(CSV) 파일이 성공적으로 저장되었습니다!")
        time.sleep(1)
        st.rerun()
# ---------------------------------------------------------
# 모드 3: 성적 통계 센터
# ---------------------------------------------------------
else:
    st.header("📊 성적 통계 센터")
    if os.path.exists(RESULT_FILE):
        rdf = pd.read_csv(RESULT_FILE)
        st.metric("총 응시 인원", f"{len(rdf)}명")
        st.line_chart(rdf['score'])
    else: st.info("기록이 없습니다.")
