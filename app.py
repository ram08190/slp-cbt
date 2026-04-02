import streamlit as st
import pandas as pd
import random
import os

# 페이지 설정
st.set_page_config(page_title="언어재활사 국시 CBT 관리자툴", layout="wide")

# 이미지 저장 폴더 생성
if not os.path.exists("images"):
    os.makedirs("images")

# 1. 데이터 불러오기 함수 (CSV 기반으로 변경하여 웹 수정 지원)
def load_data():
    if os.path.exists("quiz_db.csv"):
        df = pd.read_csv("quiz_db.csv")
    else:
        # 파일이 없으면 엑셀에서 가져오거나 빈 데이터 생성
        try:
            df = pd.read_excel("국시_3문항_테스트결과.xlsx")
            df.to_csv("quiz_db.csv", index=False)
        except:
            df = pd.DataFrame(columns=["번호", "question", "case_box", "image_path", "option1", "option2", "option3", "option4", "option5", "answer", "is_image_option"])
    return df

# 사이드바 메뉴 (관리자 기능 추가)
st.sidebar.title("MENU")
mode = st.sidebar.radio("모드 선택", ["📖 시험 보기", "⚙️ 문제 및 이미지 관리"])

# ---------------------------------------------------------
# 모드 1: 문제 및 이미지 관리 (수정 툴)
# ---------------------------------------------------------
if mode == "⚙️ 문제 및 이미지 관리":
    st.header("⚙️ 문제 은행 및 이미지 관리자")
    
    # 1. 웹에서 바로 표 수정하기
    st.subheader("1. 문제 데이터 편집")
    st.caption("아래 표의 칸을 더블클릭하여 내용을 수정하고 행을 추가할 수 있습니다.")
    current_df = load_data()
    edited_df = st.data_editor(current_df, num_rows="dynamic", use_container_width=True)
    
    if st.button("💾 모든 변경사항 저장"):
        edited_df.to_csv("quiz_db.csv", index=False)
        st.success("데이터베이스가 업데이트되었습니다!")

    st.divider()

    # 2. 이미지 파일 업로드
    st.subheader("2. 시험용 이미지 업로드")
    st.write("뇌 구조, 조영술 사진 등 문제에 들어갈 파일을 선택하세요.")
    up_file = st.file_uploader("파일 선택", type=['png', 'jpg', 'jpeg'])
    if up_file:
        with open(os.path.join("images", up_file.name), "wb") as f:
            f.write(up_file.getbuffer())
        st.success(f"성공: {up_file.name} 이미지가 업로드되었습니다.")
        st.info(f"이 이름을 표의 'image_path' 칸에 입력하세요.")

# ---------------------------------------------------------
# 모드 2: 시험 보기 (기존 CBT 기능)
# ---------------------------------------------------------
else:
    all_data_df = load_data()
    all_data = all_data_df.to_dict('records')

    if not all_data:
        st.warning("데이터가 없습니다. 관리 모드에서 문제를 추가해주세요.")
    else:
        if 'questions' not in st.session_state:
            st.session_state.questions = random.sample(all_data, min(140, len(all_data)))
            st.session_state.current_idx = 0
            st.session_state.score = 0
            st.session_state.user_answers = []

        st.title("🎓 언어재활사 국가고시 CBT")
        progress = st.session_state.current_idx / len(st.session_state.questions)
        st.progress(progress)

        if st.session_state.current_idx < len(st.session_state.questions):
            q = st.session_state.questions[st.session_state.current_idx]
            st.subheader(f"문제 {st.session_state.current_idx + 1} / {len(st.session_state.questions)}")

            # 사례 박스
            if pd.notna(q.get('case_box')) and str(q.get('case_box')).strip() != "":
                st.info(q['case_box'])

            # 이미지 표시 기능 (추가됨!)
            if pd.notna(q.get('image_path')):
                img_path = os.path.join("images", str(q['image_path']))
                if os.path.exists(img_path):
                    st.image(img_path, caption="문제 참고 이미지")

            st.write(f"**{q['question']}**")

            options = [str(q['option1']), str(q['option2']), str(q['option3']), str(q['option4']), str(q['option5'])]
            
            # 보기 선택
            user_choice = st.radio("정답을 선택하세요:", options, key=f"q_{st.session_state.current_idx}")

            if st.button("다음 문제로"):
                try:
                    correct_num = int(''.join(filter(str.isdigit, str(q['answer']))))
                except:
                    correct_num = 0
                
                user_choice_idx = options.index(user_choice) + 1
                is_correct = (user_choice_idx == correct_num)
                if is_correct: st.session_state.score += 1

                st.session_state.user_answers.append({
                    'question': q['question'],
                    'user_choice': user_choice,
                    'correct_answer': options[correct_num - 1] if 0 < correct_num <= 5 else "확인 불가",
                    'is_correct': is_correct
                })
                st.session_state.current_idx += 1
                st.rerun()
        else:
            # 결과 화면 (기존과 동일)
            st.balloons()
            st.header("🎊 시험 종료!")
            st.metric("최종 점수", f"{st.session_state.score} / {len(st.session_state.questions)}")
            if st.button("다시 풀기"):
                st.session_state.clear()
                st.rerun()
