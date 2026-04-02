import streamlit as st
import pandas as pd
import random

# 페이지 설정
st.set_page_config(page_title="언어재활사 국시 CBT", layout="centered")

# 1. 데이터 불러오기
@st.cache_data
def load_data():
    df = pd.read_excel("국시_3문항_테스트결과.xlsx") # 파일명 확인
    return df.to_dict('records')

if 'questions' not in st.session_state:
    all_data = load_data()
    # 140문제를 랜덤하게 추출 (문제수가 부족하면 전체 선택)
    st.session_state.questions = random.sample(all_data, min(140, len(all_data)))
    st.session_state.current_idx = 0
    st.session_state.score = 0
    st.session_state.answers = []

# UI 구성
st.title("🎓 언어재활사 국가고시 CBT 시스템")
st.progress(st.session_state.current_idx / len(st.session_state.questions))

if st.session_state.current_idx < len(st.session_state.questions):
    q = st.session_state.questions[st.session_state.current_idx]
    
    st.subheader(f"문제 {st.session_state.current_idx + 1}")
    
    # 사례 박스
    if pd.notna(q.get('case_box')):
        st.info(q['case_box'])
    
    st.write(q['question'])
    
    # 5지선다 라디오 버튼
    options = [q['option1'], q['option2'], q['option3'], q['option4'], q['option5']]
    user_choice = st.radio("정답을 선택하세요:", options, key=f"q_{st.session_state.current_idx}")
    
    if st.button("다음 문제로"):
        # 정답 체크 (데이터 형태에 따라 조정 필요)
        correct_num = int(''.join(filter(str.isdigit, str(q['answer']))))
        if options.index(user_choice) + 1 == correct_num:
            st.session_state.score += 1
        
        st.session_state.current_idx += 1
        st.rerun()

else:
    st.balloons()
    st.success(f"시험 종료! 총점: {st.session_state.score} / {len(st.session_state.questions)}")
    if st.button("다시 풀기"):
        st.session_state.clear()
        st.rerun()
