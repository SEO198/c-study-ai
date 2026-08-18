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
st.set_page_config(page_title="서진회장님의 정보처리 실기 과외 AI", page_icon="💻", layout="centered")
st.title("💻 1:1 정보처리 실기 집중 튜터 AI")
st.caption("실기 기출문제를 바탕으로 주관식 단답형 및 코드 실행 결과 추적 과외를 진행합니다.")

SYSTEM_INSTRUCTION = """
너는 정보처리기사/산업기사 '실기 시험' 1:1 전담 과외 선생님이야.
학생(서진회장님)에게 제공된 실기 기출문제 PDF 자료들을 바탕으로 1문제씩 출제하고 완벽히 이해할 때까지 지도해.

[실기 과외 출제 및 진행 규칙]
1. 4지선다 보기는 절대 주지 말고, 실제 실기 시험처럼 '주관식 단답형' 또는 '코드 실행 결과 작성형'으로 출제할 것.
2. C언어/Java/Python 코드 문제는 원본 코드를 마크다운 코드 블록으로 깔끔하게 보여주고 "출력 결과를 적으세요" 형태로 낼 것.
3. 학생이 답을 작성하기 전에는 절대 정답이나 힌트를 먼저 주지 말 것.
4. 학생이 오답을 내거나 "모르겠어", "어려워"라고 하면:
   - 바로 정답을 주지 말고 핵심 단서(힌트)를 먼저 던져서 스스로 유추하게 유도할 것.
   - 코드 문제의 경우 반복문과 변수 값이 어떻게 바뀌는지 줄 단위 '트레이싱 표'나 비유로 쉽게 짚어줄 것.
5. 정답을 맞히면 다음 실기 문제를 1개씩 순차적으로 출제할 것.
6. 말투는 친근하고 명확하게 반말로 응대할 것.
"""

# 1. 실기 PDF 업로드 함수 (최초 1회 캐싱)
@st.cache_resource(show_spinner=False)
def get_uploaded_practical_files():
    client = genai.Client()
    PDF_DIR = "./pdf_practical"
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
                    display_name=f"practical_doc_{idx+1}.pdf",
                    mime_type="application/pdf"
                )
            )
        while file_ref.state.name == "PROCESSING":
            time.sleep(1)
            file_ref = client.files.get(name=file_ref.name)
        uploaded.append(file_ref)
    return uploaded

# 2. 실기 메시지 히스토리 초기화
if "practical_messages" not in st.session_state:
    st.session_state.practical_messages = []
    
    with st.spinner("실기 기출문제 PDF 분석 및 과외 준비 중 (최초 1회만 진행)..."):
        uploaded_files = get_uploaded_practical_files()
        
        if not uploaded_files:
            st.error("경고: 'pdf_practical' 폴더에 실기 PDF 파일이 없습니다! 파일을 넣어주세요.")
            st.stop()

        client = genai.Client()
        init_prompt = [*uploaded_files, "업로드된 실기 기출문제 자료들을 확인하고, 첫 번째 실기 문제를 출제해줘!"]
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=init_prompt,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION
            )
        )
        st.session_state.practical_messages.append({"role": "model", "content": response.text})

# 3. 이전 대화 화면에 렌더링
for msg in st.session_state.practical_messages:
    role = "assistant" if msg["role"] == "model" else "user"
    with st.chat_message(role):
        st.markdown(msg["content"])

# 4. 사용자 입력 처리
if user_input := st.chat_input("정답(결과값/용어)을 입력하거나 질문해보세요 (예: 15 / 힌트 줘)"):
    st.session_state.practical_messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    contents_payload = []
    for m in st.session_state.practical_messages:
        contents_payload.append(
            types.Content(
                role=m["role"],
                parts=[types.Part.from_text(text=m["content"])]
            )
        )

    with st.chat_message("assistant"):
        with st.spinner("생각 중..."):
            client = genai.Client()
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=contents_payload,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION
                )
            )
            st.markdown(response.text)
            st.session_state.practical_messages.append({"role": "model", "content": response.text})