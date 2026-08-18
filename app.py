import os
import glob
import time
import io
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
st.title("🎓 1:1 전산/자격증 튜터 AI")
st.caption("PDF 기출문제를 기반으로 1:1 맞춤 과외를 진행합니다.")

SYSTEM_INSTRUCTION = """
너는 정보처리기사 전산 자격증 시험 1:1 전담 과외 선생님이야.
업로드된 기출문제 PDF 자료들의 실제 문제들을 기반으로 학생에게 1문제씩 출제하고 철저하게 이해할 때까지 지도해.

[다루는 영역]
- 프로그래밍 언어: C언어(포인터, 배열, 연산자 등), Java(상속, 객체지향 등), Python(기본 문법/슬라이싱)
- 전산 이론: 데이터베이스(SQL), 소프트웨어공학, 운영체제, 정보통신개론/네트워크

[규칙]
1. 반드시 한 번에 '딱 1문제'만 출제할 것 (출처, 문제 본문, 4지선다 보기 깔끔하게 표기).
2. 학생이 답을 고르거나 질문하기 전에는 정답/해설을 먼저 절대 알려주지 말 것.
3. 답을 맞히면 칭찬과 함께 핵심 원리를 1~2줄로 명쾌하게 정리해줄 것.
4. 틀리거나 힌트를 요청하면 초등학생도 이해할 수 있는 일상 속 비유로 쉽게 설명할 것.
5. 학생이 이해했다고 하거나 다음 문제를 요청하면 다음 기출문제를 출제할 것.
6. 친근하고 명확하게 반말로 응대할 것.
7. 실제 기출문제 형태를 충실히 반영해서 출제할 것.
"""

# 1. PDF 캐싱 업로드 함수 (최초 1회만 실행)
@st.cache_resource(show_spinner=False)
def get_uploaded_files():
    client = genai.Client(api_key=api_key)
    PDF_DIR = "./pdf_data"
    pdf_files = sorted(glob.glob(os.path.join(PDF_DIR, "*.pdf")))
    
    if not pdf_files:
        return []

    uploaded = []
    for idx, file_path in enumerate(pdf_files):
        with open(file_path, "rb") as f:
            file_bytes = io.BytesIO(f.read())
            file_ref = client.files.upload(
                file=file_bytes,
                config=types.UploadFileConfig(
                    display_name=f"exam_doc_{idx+1}.pdf",
                    mime_type="application/pdf"
                )
            )
        while file_ref.state.name == "PROCESSING":
            time.sleep(1)
            file_ref = client.files.get(name=file_ref.name)
        uploaded.append(file_ref)
    return uploaded

# 2. 세션 상태(Chat & Messages) 초기화
if "chat" not in st.session_state:
    with st.spinner("기출문제 PDF 분석 및 과외 준비 중 (최초 1회만 진행)..."):
        uploaded_files = get_uploaded_files()
        
        if not uploaded_files:
            st.error("경고: 'pdf_data' 폴더에 PDF 파일이 없습니다! 파일을 확인해주세요.")
            st.stop()

        client = genai.Client(api_key=api_key)
        
        # PDF와 시스템 프롬프트가 영구 유지되는 채팅 세션 생성
        chat = client.chats.create(
            model="gemini-3.6-flash",
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION
            )
        )
        
        # 최초 1회: PDF 파일 16개 통째로 넘기며 첫 문제 요청
        init_res = chat.send_message([*uploaded_files, "업로드된 기출문제 자료들을 기반으로 첫 번째 문제를 출제해줘!"])
        
        st.session_state.chat = chat
        st.session_state.messages = [{"role": "assistant", "content": init_res.text}]

# 3. 대화 히스토리 화면 출력
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# 4. 사용자 입력 및 대화 진행
if user_input := st.chat_input("정답을 입력하거나 질문해보세요 (예: 1번 / 왜 1번이야?)"):
    # 유저 메시지 표시 및 기록
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # 튜터 답변 생성 (기존 chat 세션이 PDF 맥락을 그대로 유지)
    with st.chat_message("assistant"):
        with st.spinner("생각 중..."):
            response = st.session_state.chat.send_message(user_input)
            st.markdown(response.text)
            st.session_state.messages.append({"role": "assistant", "content": response.text})