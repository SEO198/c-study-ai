import os
import random
import streamlit as st
from dotenv import load_dotenv
import google.generativeai as genai

st.set_page_config(page_title="정보처리기사 1:1 맞춤 과외", page_icon="🎓", layout="centered")
load_dotenv()

try:
    api_key = st.secrets.get("GEMINI_API_KEY", os.getenv("GEMINI_API_KEY"))
except Exception:
    api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    st.error("API 키가 없습니다!")
    st.stop()

genai.configure(api_key=api_key)

st.title("🎓 회장님 전용 1:1 정보처리기사 과외 튜터")
st.caption("초딩도 이해하는 쉬운 설명 + 오답 체크 및 복습 루틴 탑재!")

# 텍스트 파일에서 문제 단위로 쪼개기
@st.cache_data
def load_question_list():
    txt_path = "all_questions.txt"
    if not os.path.exists(txt_path):
        return None
    with open(txt_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # 문항별로 분리 후 리스트로 반환
    questions = [q.strip() for q in content.split("\n\n") if len(q.strip()) > 20]
    return questions

# 세션 상태 초기화
if "question_pool" not in st.session_state:
    pool = load_question_list()
    if not pool:
        st.error("'all_questions.txt' 파일이 없거나 내용이 비어있습니다!")
        st.stop()
    random.shuffle(pool)
    st.session_state.question_pool = pool
    st.session_state.currentIndex = 0
    st.session_state.review_list = [] # 다시 볼 오답/재학습 목록

if "chat" not in st.session_state:
    # 튜터 페르소나 설정
    system_instruction = """
너는 정보처리기사 필기 시험 합격을 돕는 1:1 전담 과외 선생님이야.
학생(회장님)은 코딩과 이론 초보 단계이므로, 절대 어렵게 설명하지 말고 **초등학생도 이해할 수 있도록 일상적인 비유를 들어서 아주 쉽게** 설명해 줘야 해.
학생이 정답을 맞히거나 모른다고 할 때, 만약 개념이 부족해 보이면 '재학습 필요' 체크를 해두라고 자연스럽게 유도해 줘.
반말체로 친근하고 위트 있게 대화할 것.
"""
    model = genai.GenerativeModel(
        model_name="models/gemini-3.5-flash",
        system_instruction=system_instruction
    )
    st.session_state.chat = model.start_chat(history=[])
    st.session_state.messages = []

    # 첫 번째 문제 뽑기
    first_q = st.session_state.question_pool[0]
    init_prompt = f"""
다음 기출문제를 하나 출제해줘:
{first_q}

출제 형식:
1. 문제를 깔끔하게 보여주고
2. "정답이 뭔 것 같아? 모르면 '모르겠다'고 해줘!" 하고 물어봐 줘.
"""
    res = st.session_state.chat.send_message(init_prompt)
    st.session_state.messages.append({"role": "assistant", "content": res.text})

# 화면에 대화 내역 출력
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# 사이드바에 오답/재학습 노트 표시
with st.sidebar:
    st.subheader("📌 복습 및 재학습 노트")
    if st.session_state.review_list:
        for idx, item in enumerate(st.session_state.review_list):
            st.write(f"{idx+1}. {item[:30]}...")
    else:
        st.write("아직 체크된 재학습 항목이 없어요!")

    if st.button("🔄 다음 문제로 넘어가기"):
        st.session_state.currentIndex += 1
        if st.session_state.currentIndex >= len(st.session_state.question_pool):
            st.warning("모든 문제를 다 풀었습니다! 문제를 다시 섞습니다.")
            random.shuffle(st.session_state.question_pool)
            st.session_state.currentIndex = 0
        
        next_q = st.session_state.question_pool[st.session_state.currentIndex]
        next_prompt = f"다음 새로운 기출문제를 출제해줘:\n{next_q}"
        
        with st.spinner("다음 문제 가져오는 중..."):
            res = st.session_state.chat.send_message(next_prompt)
            st.session_state.messages.append({"role": "assistant", "content": res.text})
            st.rerun()

# 유저 입력 처리
if user_input := st.chat_input("정답을 말하거나, '초딩처럼 설명해줘'라고 해보세요!"):
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("과외 쌤이 생각 중..."):
            response = st.session_state.chat.send_message(user_input)
            st.markdown(response.text)
            st.session_state.messages.append({"role": "assistant", "content": response.text})
            
            # 만약 유저가 모른다고 하거나 다시 보기를 원하면 자동으로 사이드바 복습 노트에 추가하는 힌트 텍스트 감지
            if any(keyword in user_input for keyword in ["모르겠", "이해 안", "어려워", "체크", "다시"]):
                current_q = st.session_state.question_pool[st.session_state.currentIndex]
                if current_q not in st.session_state.review_list:
                    st.session_state.review_list.append(current_q)