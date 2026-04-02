import streamlit as st
import pandas as pd
import random

# 페이지 설정
st.set_page_config(page_title="언어재활사 국시 CBT", layout="centered")

# 1. 데이터 불러오기
@st.cache_data
def load_data():
    # 파일명이 정확한지 다시 한번 확인하세요!
    df = pd.read_excel("국시_3문항_테스트결과.xlsx") 
    return df.to_dict('records')

# 세션 상태 초기화
if 'questions' not in st.session_state:
    all_data = load_data()
    # 140문제를 랜덤하게 추출 (문제수가 부족하면 전체 선택)
    st.session_state.questions = random.sample(all_data, min(140, len(all_data)))
    st.session_state.current_idx = 0
    st.session_state.score = 0
    st.session_state.user_answers = [] # 사용자가 선택한 답 저장용

# UI 구성
st.title("🎓 언어재활사 국가고시 CBT")
progress = st.session_state.current_idx / len(st.session_state.questions)
st.progress(progress)

# 문제 풀이 단계
if st.session_state.current_idx < len(st.session_state.questions):
    q = st.session_state.questions[st.session_state.current_idx]
    
    st.subheader(f"문제 {st.session_state.current_idx + 1} / {len(st.session_state.questions)}")
    
    # 사례 박스 (내용이 있을 경우만 표시)
    if pd.notna(q.get('case_box')) and str(q.get('case_box')).strip() != "":
        st.info(q['case_box'])
    
    st.write(f"**{q['question']}**")
    
    # 5지선다 라디오 버튼
    options = [str(q['option1']), str(q['option2']), str(q['option3']), str(q['option4']), str(q['option5'])]
    user_choice = st.radio("정답을 선택하세요:", options, key=f"q_{st.session_state.current_idx}")
    
    if st.button("다음 문제로"):
        # 정답 번호 추출 (예: '1' 또는 '정답: 1' 등에서 숫자만 추출)
        try:
            correct_num = int(''.join(filter(str.isdigit, str(q['answer']))))
        except ValueError:
            correct_num = 0 # 에러 방지용
            
        user_choice_idx = options.index(user_choice) + 1
        
        # 정답 여부 저장
        is_correct = (user_choice_idx == correct_num)
        if is_correct:
            st.session_state.score += 1
        
        # 기록 저장
        st.session_state.user_answers.append({
            'question': q['question'],
            'user_choice': user_choice,
            'correct_answer': options[correct_num - 1] if 0 < correct_num <= 5 else "확인 불가",
            'is_correct': is_correct
        })
        
        st.session_state.current_idx += 1
        st.rerun()

# 결과 출력 단계
else:
    st.balloons()
    st.header("🎊 시험 종료!")
    
    # 점수 요약
    total = len(st.session_state.questions)
    score = st.session_state.score
    percent = int((score / total) * 100)
    
    col1, col2 = st.columns(2)
    col1.metric("최종 점수", f"{score} / {total}")
    col2.metric("정답률", f"{percent}%")
    
    if percent >= 60:
        st.success("합격 기준(60%)을 통과하셨습니다! 고생하셨습니다. 👍")
    else:
        st.error("합격 기준에 미달했습니다. 조금 더 힘내세요! 💪")

    # 오답 리스트 확인
    with st.expander("결과 상세 보기 (오답 노트)"):
        for i, res in enumerate(st.session_state.user_answers):
            icon = "✅" if res['is_correct'] else "❌"
            st.write(f"{icon} **문제 {i+1}.** {res['question']}")
            if not res['is_correct']:
                st.write(f"&nbsp;&nbsp;&nbsp;&nbsp;내 선택: {res['user_choice']}")
                st.write(f"&nbsp;&nbsp;&nbsp;&nbsp;**정답: {res['correct_answer']}**")
            st.divider()

    if st.button("다시 풀기"):
        # 세션 초기화 후 재시작
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
