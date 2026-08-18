import os
import glob
import time
import io
import streamlit as st
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

# 웹페이지 기본 설정
st.set_page_config(page_title="서진회장님의 전산/C언어 과외 AI", page_icon="🎓", layout="centered")
st.title("🎓 1:1 전산/자격증 튜터 AI")
st.caption("PDF 기출문제를 기반으로 1:1 맞춤 과외를 진행합니다.")

# 1. Gemini 클라이언트 및 세션 초기화 (Client 세션 보존)
if "client" not in st.session_state:
    st.session_state.client = genai.Client()

if "chat" not in st.session_state:
    with st.spinner("기출문제 PDF 16개 분석 및 준비 중... 잠시만 기다려주세요!"):
        PDF_DIR = "./pdf_data"
        pdf_files = glob.glob(os.path.join(PDF_DIR, "*.pdf"))
        
        if not pdf_files:
            st.error("경고: 'pdf_data' 폴더에 필기 PDF 파일이 없습니다! 파일을 넣어주세요.")
            st.stop()

        uploaded_files = []
        for idx, file_path in enumerate(sorted(pdf_files)):
            # 한글/영문 파일명 모두 안전하게 업로드
            with open(file_path, "rb") as f:
                file_bytes = io.BytesIO(f.read())
                file_ref = st.session_state.client.files.upload(
                    file=file_bytes,
                    config=types.UploadFileConfig(
                        display_name=f"exam_doc_{idx+1}.pdf",
                        mime_type="application/pdf"
                    )
                )
            while file_ref.state.name == "PROCESSING":
                time.sleep(1)
                file_ref = st.session_state.client.files.get(name=file_ref.name)
            uploaded_files.append(file_ref)

        system_instruction = """
        너는 정보처리기사/산업기사 및 전산 자격증 시험 1:1 전담 과외 선생님이야.
        학생(서진회장님)에게 제공된 기출문제 PDF 자료들을 바탕으로 1문제씩 출제하고 철저하게 이해할 때까지 지도해.

        [다루는 영역]
        - 프로그래밍 언어: C언어(포인터, 배열, 연산자 등), Java(상속, 객체지향 등), Python(기본 문법/슬라이싱)
        - 전산 이론: DB(SQL), 소프트웨어공학, 운영체제/네트워크 기출 전 범위

        [규칙]
        1. 반드시 한 번에 '딱 1문제'만 출제할 것 (출처, 문제 본문, 4지선다 보기 깔끔하게 유지).
        2. 학생이 답을 고르거나 질문하기 전에는 정답/해설을 먼저 절대 주지 말 것.
        3. 답을 맞히면 칭찬과 함께 핵심 원리를 1~2줄 요약할 것.
        4. 틀리거나 질문하면 초등학생도 이해할 수 있는 일상 속 비유로 쉽게 설명할 것.
        5. 학생이 이해했다고 하면 다음 문제로 넘어갈 것.
        6. 친근하고 명확하게 반말로 응대할 것.
        """

        chat = st.session_state.client.chats.create(
            model="gemini-2.5-flash",
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
            )
        )

        # 첫 문제 요청
        init_res = chat.send_message([*uploaded_files, "업로드된 기출문제 자료들을 확인하고 첫 번째 문제를 출제해줘!"])
        
        st.session_state.chat = chat
        st.session_state.messages = [{"role": "assistant", "content": init_res.text}]

# 2. 대화 기록 화면에 출력
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# 3. 사용자 채팅 입력창
if user_input := st.chat_input("정답을 입력하거나 질문해보세요 (예: 1번 / 비유로 설명해줘)"):
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("생각 중..."):
            response = st.session_state.chat.send_message(user_input)
            st.markdown(response.text)
            st.session_state.messages.append({"role": "assistant", "content": response.text})