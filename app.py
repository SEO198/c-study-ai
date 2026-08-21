import os
import streamlit as st
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

# Streamlit Cloud(Secrets) 및 로컬(.env) 키 지원
try:
    api_key = st.secrets.get("GEMINI_API_KEY", os.getenv("GEMINI_API_KEY"))
except Exception:
    api_key = os.getenv("GEMINI_API_KEY")

st.set_page_config(page_title="정보처리기사 문제은행", page_icon="🎓", layout="centered")
st.title("🎓 1:1 정보처리기사 필기 튜터 AI")
st.caption("정제된 기출문제 텍스트를 기반으로 1:1 맞춤 과외를 진행합니다.")

# 시스템 프롬프트에 기출문제 컨텍스트를 동적으로 주입하기 위해 함수로 분리
def get_system_instruction(question_text):
    return f"""
너는 정보처리기사 '필기 시험' 1:1 전담 과외 선생님이야.
아래에 제공된 [기출문제 데이터] 내용들을 기반으로 학생에게 1문제씩 출제하고 철저하게 이해할 때까지 지도해.

[다루는 영역]
- 프로그래밍 언어: C언어(포인터, 배열, 연산자 등), Java(상속, 객체지향 등), Python(기본 문법/슬라이싱)
- 전산 이론: 데이터베이스(SQL), 소프트웨어공학, 운영체제, 정보통신개론/네트워크

[규칙]
1. 반드시 한 번에 '딱 1문제'만 출제할 것 (출처, 문제 본문, 4지선다 보기 깔끔하게 표기).
2. 학생이 답을 고르거나 질문하기 전에는 정답/해설을 먼저 절대 알려주지 말 것.
3. 답을 맞히면 칭찬과 함께 핵심 원리를 1~2줄로 명쾌하게 정리해줄 것.
4. 틀리거나 힌트를 요청하면 초등학생도 이해할 수 있는 일상 속 비유로 쉽게 설명할 것.
5. [중요] 문제 출제 방식:
   - 특정 연도/회차의 1번부터 순서대로 출제하지 말 것.
   - 첫 문제는 물론, 정답을 맞힌 뒤 이어지는 다음 문제들도 '항상 아래 기출 데이터의 모든 연도, 회차 중에서 완전 무작위(랜덤)'로 하나씩 골라 출제할 것.
   - 방금 출제했던 문제와 겹치지 않게 과목을 골고루 섞어서 출제할 것.
6. 친근하고 명확하게 반말로 응대할 것.
7. 실제 기출문제 형태를 충실히 반영해서 출제할 것.

[기출문제 데이터]
{question_text[:30000]}  # 너무 길면 토큰 초과할 수 있으니 앞부분 주요 내용 컨텍스트로 제공
"""

# 1. 텍스트 파일 로드 함수 (캐싱 적용)
@st.cache_data
def load_question_bank():
    txt_path = "all_questions.txt"
    if not os.path.exists(txt_path):
        return None
    with open(txt_path, "r", encoding="utf-8") as f:
        return f.read()

# 2. 세션 상태 초기화 및 튜터 세팅
if "chat" not in st.session_state:
    with st.spinner("기출문제 텍스트 데이터 로딩 및 과외 준비 중..."):
        question_bank_text = load_question_bank()
        
        if not question_bank_text:
            st.error("경고: 'all_questions.txt' 파일이 없습니다! 먼저 pdf_to_text.py를 실행해서 텍스트 파일을 생성해주세요.")
            st.stop()

        if not api_key:
            st.error("경고: GEMINI_API_KEY가 설정되지 않았습니다. 시크릿츠나 .env를 확인해주세요.")
            st.stop()

        client = genai.Client(api_key=api_key)
        
        # 시스템 프롬프트에 기출 텍스트 심어주기
        system_instruction = get_system_instruction(question_bank_text)
        
        # 채팅 세션 생성 (안정적인 최신 플래시 모델 사용)
        chat = client.chats.create(
            model="gemini-3.5-flash-light",
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.8
            )
        )
        
        # 첫 문제 요청
        init_res = chat.send_message(
            "업로드된 기출 텍스트 자료들 중 완전 무작위(랜덤)로 하나 골라서 첫 번째 문제를 출제해줘!"
        )
        
        st.session_state.chat = chat
        st.session_state.messages = [
            {"role": "assistant", "content": init_res.text}
        ]

# 3. 대화 히스토리 화면 출력
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# 4. 사용자 입력 및 대화 진행
if user_input := st.chat_input("정답을 입력하거나 질문해보세요 (예: 1번 / 왜 1번이야?)"):
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("생각 중..."):
            response = st.session_state.chat.send_message(user_input)
            st.markdown(response.text)
            st.session_state.messages.append({"role": "assistant", "content": response.text})