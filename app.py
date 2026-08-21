import os
import streamlit as st
from dotenv import load_dotenv
import google.generativeai as genai  # [핵심] 안정적인 구버전 라이브러리 사용

st.set_page_config(page_title="정보처리기사 문제은행", page_icon="🎓", layout="centered")
load_dotenv()

try:
    api_key = st.secrets.get("GEMINI_API_KEY", os.getenv("GEMINI_API_KEY"))
except Exception:
    api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    st.error("API 키가 없습니다!")
    st.stop()

# [핵심] 구버전 방식으로 명확하게 키 설정
genai.configure(api_key=api_key)

st.title("🎓 1:1 정보처리기사 필기 튜터 AI")
st.caption("정제된 기출문제 텍스트를 기반으로 1:1 맞춤 과외를 진행합니다.")

# 텍스트 파일 로드 함수
@st.cache_data
def load_question_bank():
    txt_path = "all_questions.txt"
    if not os.path.exists(txt_path):
        return None
    with open(txt_path, "r", encoding="utf-8") as f:
        return f.read()

# 세션 상태 및 모델 초기화
if "chat" not in st.session_state:
    with st.spinner("과외 준비 중..."):
        question_bank_text = load_question_bank()
        if not question_bank_text:
            st.error("'all_questions.txt' 파일이 없습니다!")
            st.stop()

        # 시스템 프롬프트 정의
        system_instruction = f"""
너는 정보처리기사 '필기 시험' 1:1 전담 과외 선생님이야.
아래 기출 데이터를 바탕으로 1문제씩 무작위로 출제하고 지도해. 친근한 반말로 해줘.

[기출문제 데이터]
{question_bank_text[:30000]}
"""

        # [핵심] 안정적인 1.5 플래시 모델 및 채팅 세션 생성
        model = genai.GenerativeModel(
            model_name="models/gemini-3.5-flash",
            system_instruction=system_instruction
        )
        chat = model.start_chat(history=[])
        
        init_res = chat.send_message("기출 텍스트 중 무작위로 하나 골라서 첫 번째 문제를 출제해줘!")
        
        st.session_state.chat = chat
        st.session_state.messages = [{"role": "assistant", "content": init_res.text}]

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if user_input := st.chat_input("정답을 입력하세요"):
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("생각 중..."):
            response = st.session_state.chat.send_message(user_input)
            st.markdown(response.text)
            st.session_state.messages.append({"role": "assistant", "content": response.text})