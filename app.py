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
            # 엑셀 파일 읽기
            df = pd.read_excel("국시_3문항_테스트결과.xlsx")
            # 필요한 컬럼이 없을 경우를 대비해 기본값 채우기
            for col in ["case_box", "image_path", "is_image_option"]:
                if col not in df.columns:
                    df[col] = ""
            # 데이터를 저장하여 이후부터는 CSV를 사용
            df.to_csv("quiz_db.csv", index=False)
            return df
        except Exception as e:
            st.error(f"데이터 로드 중 오류 발생: {e}")
            return pd.DataFrame(columns=["번호", "question", "case_box", "image_path", "option1", "option2", "option3", "option4", "option5", "answer"])

# 사이드바 메뉴
st.sidebar.title("🎮 메뉴 선택")
mode = st.sidebar.radio("원하는 작업을 선택하세요", ["📝 시험 풀기", "🛠️ 문항별 개별 수정"])

# 데이터 불러오기
df = load_data()

# ---------------------------------------------------------
# 모드 1: 문항별 개별 수정 (관리자 기능)
# ---------------------------------------------------------
if mode == "🛠️ 문항별 개별 수정":
    st.header("🛠️ 문항별 개별 수정 및 보완")
    
    if df.empty:
        st.warning("수정할 데이터가 없습니다.")
    else:
        # 1. 수정할 문제 번호 선택
        q_numbers = df.index.tolist()
        selected_idx = st.selectbox("수정할 문제 번호를 선택하세요", q_numbers, format_func=lambda x: f"{x+1}번 문제")
        
        curr_q = df.iloc[selected_idx]

        # 2. 편집 영역 (2컬럼 배치)
        col1, col2 = st.columns([1, 1])

        with col1:
            st.subheader("📝 문제 및 내용 수정")
            new_question = st.text_area("문제 내용", value=str(curr_q['question']), height=100)
            
            # NaN 값 처리 포함
            case_val = str(curr_q['case_box']) if pd.notna(curr_q['case_box']) else ""
            new_case = st.text_area("사례 박스 (표나 긴 지문)", value=case_val, height=150)
            
            st.subheader("🔢 정답 및 보기 수정")
            opt1 = st.text_input("보기 1", value=str(curr_q['option1']))
            opt2 = st.text_input("보기 2", value=str(curr_q['option2']))
            opt3 = st.text_input("보기 3", value=str(curr_q['option3']))
            opt4 = st.text_input("보기 4", value=str(curr_q['option4']))
            opt5 = st.text_input("보기 5", value=str(curr_q['option5']))
            
            # --- 에러 수정 및 안전한 정답 처리 부분 ---
            q_answer_raw = str(curr_q['answer']) if pd.notna(curr_q['answer']) else "1"
            # 숫자만 추출 (실수형 1.0 등 대응)
            try:
                # 점(.)이 포함된 경우를 위해 float으로 먼저 변환 후 int 처리
                default_ans = int(float(''.join(filter(lambda x: x.isdigit() or x == '.', q_answer_raw))))
                if not (1 <= default_ans <= 5): default_ans = 1
            except:
                default_ans = 1

            new_ans = st.number_input("정답 번호 (1-5)", min_value=1, max_value=5, value=default_ans)

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
    st.header("🎓 언어재활사 국가시험 CBT")
    
    quiz_data = df.to_dict('records')
    
    if not quiz_data:
        st.error("데이터가 비어 있습니다. 수정 모드에서 문제를 먼저 확인해주세요!")
    else:
        if 'questions' not in st.session_state:
            # 전체 데이터 중 랜덤 추출
            st.session_state.questions = random.sample(quiz_data, min(140, len(quiz_data)))
            st.session_state.current_idx = 0
            st.session_state.score = 0

        if st.session_state.current_idx < len(st.session_state.questions):
            q = st.session_state.questions[st.session_state.current_idx]
            
            st.subheader(f"문제 {st.session_state.current_idx + 1}")
            st.progress(st.session_state.current_idx / len(st.session_state.questions))

            # 사례 박스 출력
            if pd.notna(q['case_box']) and str(q['case_box']).strip() != "":
                st.info(q['case_box'])

            # 이미지 출력
            if pd.notna(q['image_path']) and str(q['image_path']).strip() != "":
                img_path = os.path.join("images", str(q['image_path']))
                if os.path.exists(img_path):
                    st.image(img_path)

            st.markdown(f"### {q['question']}")
            
            # 보기 리스트
            opts = [str(q['option1']), str(q['option2']), str(q['option3']), str(q['option4']), str(q['option5'])]
            choice = st.radio("정답을 선택하세요", opts, key=f"play_{st.session_state.current_idx}")

            if st.button("다음 문제로"):
                # 정답 비교 (숫자로 변환 후 인덱스 비교)
                try:
                    correct_idx = int(float(str(q['answer'])))
                    if choice == opts[correct_idx-1]:
                        st.session_state.score += 1
                except:
                    pass # 정답 데이터 오류 시 무시
                
                st.session_state.current_idx += 1
                st.rerun()
        else:
            st.balloons()
            st.header("🎊 결과 발표")
            total_q = len(st.session_state.questions)
            st.metric("최종 점수", f"{st.session_state.score} / {total_q}")
            
            if total_q > 0 and (st.session_state.score / total_q) >= 0.6:
                st.success("합격 기준을 통과하셨습니다! 축하합니다!")
            else:
                st.error("아쉽지만 합격 기준에 미달했습니다.")
                
            if st.button("다시 풀기"):
                if 'questions' in st.session_state:
                    del st.session_state['questions']
                st.rerun()
