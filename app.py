import streamlit as st
import pandas as pd
import random
import os

# 페이지 설정
st.set_page_config(page_title="언어재활사 국시 CBT 관리도구", layout="wide")

# 이미지 저장 폴더 생성
if not os.path.exists("images"):
    os.makedirs("images")

# 데이터 로드 함수 (CSV 우선, 없으면 엑셀 로드)
def load_data():
    if os.path.exists("quiz_db.csv"):
        return pd.read_csv("quiz_db.csv")
    else:
        try:
            df = pd.read_excel("국시_3문항_테스트결과.xlsx")
            # 필요한 컬럼이 없을 경우를 대비해 기본값 채우기
            for col in ["case_box", "image_path", "is_image_option"]:
                if col not in df.columns:
                    df[col] = ""
            df.to_csv("quiz_db.csv", index=False)
            return df
        except:
            # 완전 빈 데이터셋 생성
            return pd.DataFrame(columns=["번호", "question", "case_box", "image_path", "option1", "option2", "option3", "option4", "option5", "answer"])

# 사이드바 메뉴
st.sidebar.title("🎮 메뉴 선택")
mode = st.sidebar.radio("원하는 작업을 선택하세요", ["📝 시험 풀기", "🛠️ 문항별 개별 수정"])

# 데이터 불러오기
df = load_data()

# ---------------------------------------------------------
# 모드 1: 문항별 개별 수정 (사용자 요청 핵심 기능)
# ---------------------------------------------------------
if mode == "🛠️ 문항별 개별 수정":
    st.header("🛠️ 문항별 개별 수정 및 보완")
    
    # 1. 수정할 문제 번호 선택
    q_numbers = df.index.tolist()
    selected_idx = st.selectbox("수정할 문제 번호를 선택하세요", q_numbers, format_func=lambda x: f"{x+1}번 문제")
    
    curr_q = df.iloc[selected_idx]

    # 2. 편집 영역 (2컬럼 배치)
    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("📝 문제 및 내용 수정")
        new_question = st.text_area("문제 내용", value=curr_q['question'], height=100)
        new_case = st.text_area("사례 박스 (표나 긴 지문)", value=str(curr_q['case_box']) if pd.notna(curr_q['case_box']) else "", height=150)
        
        st.subheader("🔢 정답 및 보기 수정")
        opt1 = st.text_input("보기 1", value=curr_q['option1'])
        opt2 = st.text_input("보기 2", value=curr_q['option2'])
        opt3 = st.text_input("보기 3", value=curr_q['option3'])
        opt4 = st.text_input("보기 4", value=curr_q['option4'])
        opt5 = st.text_input("보기 5", value=curr_q['option5'])
        new_ans = st.number_input("정답 번호 (1-5)", min_value=1, max_value=5, value=int(curr_q['answer']) if pd.isdigit(str(curr_q['answer'])) else 1)

    with col2:
        st.subheader("🖼️ 이미지 관리")
        # 현재 이미지 표시
        if pd.notna(curr_q['image_path']) and str(curr_q['image_path']).strip() != "":
            st.write(f"현재 파일: {curr_q['image_path']}")
            img_path = os.path.join("images", str(curr_q['image_path']))
            if os.path.exists(img_path):
                st.image(img_path, width=300)
        else:
            st.warning("등록된 이미지가 없습니다.")

        # 새 이미지 업로드
        up_file = st.file_uploader("이 문항에 새 이미지 등록", type=['png', 'jpg', 'jpeg'], key=f"up_{selected_idx}")
        new_img_name = curr_q['image_path']
        if up_file:
            new_img_name = up_file.name
            with open(os.path.join("images", new_img_name), "wb") as f:
                f.write(up_file.getbuffer())
            st.success("새 이미지가 업로드되었습니다!")

    # 3. 저장 버튼
    if st.button("✅ 현재 문항 수정사항 저장", use_container_width=True):
        df.at[selected_idx, 'question'] = new_question
        df.at[selected_idx, 'case_box'] = new_case
        df.at[selected_idx, 'option1'] = opt1
        df.at[selected_idx, 'option2'] = opt2
        df.at[selected_idx, 'option3'] = opt3
        df.at[selected_idx, 'option4'] = opt4
        df.at[selected_idx, 'option5'] = opt5
        df.at[selected_idx, 'answer'] = new_ans
        df.at[selected_idx, 'image_path'] = new_img_name
        
        df.to_csv("quiz_db.csv", index=False)
        st.balloons()
        st.success(f"{selected_idx+1}번 문제가 성공적으로 수정되었습니다!")

# ---------------------------------------------------------
# 모드 2: 시험 풀기 (CBT)
# ---------------------------------------------------------
else:
    st.header("🎓 언어재활사 국가고시 CBT")
    
    quiz_data = df.to_dict('records')
    
    if not quiz_data:
        st.error("수정 모드에서 문제를 먼저 등록해주세요!")
    else:
        if 'questions' not in st.session_state:
            st.session_state.questions = random.sample(quiz_data, min(140, len(quiz_data)))
            st.session_state.current_idx = 0
            st.session_state.score = 0

        if st.session_state.current_idx < len(st.session_state.questions):
            q = st.session_state.questions[st.session_state.current_idx]
            
            st.subheader(f"문제 {st.session_state.current_idx + 1}")
            st.progress(st.session_state.current_idx / len(st.session_state.questions))

            if pd.notna(q['case_box']) and str(q['case_box']).strip() != "":
                st.info(q['case_box'])

            if pd.notna(q['image_path']) and str(q['image_path']).strip() != "":
                img_path = os.path.join("images", str(q['image_path']))
                if os.path.exists(img_path):
                    st.image(img_path)

            st.markdown(f"### {q['question']}")
            
            opts = [str(q['option1']), str(q['option2']), str(q['option3']), str(q['option4']), str(q['option5'])]
            choice = st.radio("정답을 선택하세요", opts, key=f"play_{st.session_state.current_idx}")

            if st.button("다음 문제로"):
                # 정답 비교
                correct_idx = int(q['answer'])
                if choice == opts[correct_idx-1]:
                    st.session_state.score += 1
                
                st.session_state.current_idx += 1
                st.rerun()
        else:
            st.balloons()
            st.header("🎊 결과 발표")
            st.metric("최종 점수", f"{st.session_state.score} / {len(st.session_state.questions)}")
            if st.button("다시 풀기"):
                del st.session_state['questions']
                st.rerun()
