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

st.set_page_config(page_title="매경TEST 1:1 튜터 AI", page_icon="📈", layout="centered")
st.title("📈 1:1 매경TEST 고득점 튜터 AI")
st.caption("매경TEST 교재 요약 및 기출/모의고사를 기반으로 경제·경영 1:1 맞춤 과외를 진행합니다.")

SYSTEM_INSTRUCTION = """
너는 국가공인 경제·경영 이해력 인증시험인 '매경TEST' 최우수 등급 1:1 전담 과외 선생님이야.
업로드된 매경TEST 교재 요약 및 기출/모의고사 PDF 자료들을 기반으로 학생에게 1문제씩 출제하고 철저하게 원리를 이해할 때까지 지도해.

[다루는 영역]
1. 경제 영역: 미시경제(시장원리, 탄력성, 시장실패), 거시경제(GDP, 물가, 금리, 환율, 통화정책), 국제경제
2. 경영 영역: 경영전략, 마케팅, 재무/회계, 인사조직, 생산관리, 최신 비즈니스 시사/용어

[출제 및 과외 규칙]
1. [실전 기출 형태 반영 및 출력 포맷 엄수]:
   - 출처(예: [출처: 매경 701제 / 거시경제])와 문제 본문, 필요시 [보기] 박스를 제시할 것.
   - 선지는 ①~⑤까지 각각 1줄씩 내용과 함께 작성할 것.
   - [중요 금지 사항]: 5개의 선지 작성이 끝난 직후, 본문 하단에 내용 없는 빈 번호 목록(① ② ③ ④ ⑤)을 절대로 중복해서 출력하지 말 것.
2. 학생이 답을 선택하기 전에는 절대 정답이나 해설을 먼저 알려주지 말 것.
3. 문제 출제 방식 (완전 무작위):
   - 특정 연도나 1번부터 차례대로 내지 말 것.
   - 첫 문제는 물론, 정답을 맞힌 뒤 이어지는 문제들도 '항상 전체 PDF 자료의 경제/경영 전 영역에서 완전 무작위(랜덤)'로 하나씩 골라 출제할 것.
   - 경제 이론, 경영 이론, 시사 상식 문제를 골고루 번갈아가며 출제할 것.
4. 학생이 정답을 맞히면:
   - 칭찬과 함께 해당 개념이 현실 경제/기업 경영에서 왜 중요한지 핵심 맥락을 1~2줄로 명쾌하게 정리해줄 것.
5. 학생이 오답을 내거나 힌트를 요구하면:
   - 복잡한 수식 대신 현실 경제 뉴스나 일상생활 속 직관적인 비유(예: 마트 장보기, 금리 인상 시 은행 대출 등)로 쉽게 이해시킬 것.
6. 친근하고 명확하게 반말로 응대할 것.
"""

# 1. 매경 PDF 캐싱 업로드 함수 (600,000ms = 10분 설정 및 BytesIO 안정 전송)
@st.cache_resource(show_spinner=False)
def get_uploaded_maekyung_files():
    client = genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(timeout=600000)
    )
    PDF_DIR = "./pdf_maekyung"
    pdf_files = sorted(glob.glob(os.path.join(PDF_DIR, "*.pdf")))
    
    if not pdf_files:
        return []

    # 기존 구글 서버에 이미 등록된 파일이 있다면 즉시 재사용
    existing_files = {f.display_name: f for f in client.files.list()}
    
    uploaded = []
    for idx, file_path in enumerate(pdf_files):
        display_name = f"maekyung_doc_{idx+1}.pdf"
        
        if display_name in existing_files and existing_files[display_name].state.name == "ACTIVE":
            uploaded.append(existing_files[display_name])
            continue

        file_ref = None
        for attempt in range(3):
            try:
                with open(file_path, "rb") as f:
                    file_bytes = io.BytesIO(f.read())
                    file_ref = client.files.upload(
                        file=file_bytes,
                        config=types.UploadFileConfig(
                            display_name=display_name,
                            mime_type="application/pdf"
                        )
                    )
                break
            except Exception as e:
                if attempt < 2:
                    time.sleep(3)
                else:
                    raise e

        while file_ref.state.name == "PROCESSING":
            time.sleep(1)
            file_ref = client.files.get(name=file_ref.name)
            
        uploaded.append(file_ref)
        
    return uploaded

# 2. 세션 상태 초기화
if "mk_chat" not in st.session_state:
    with st.spinner("매경TEST PDF 교재 및 기출자료 분석 중 (최초 1회만 진행)..."):
        uploaded_files = get_uploaded_maekyung_files()
        
        if not uploaded_files:
            st.error("경고: 'pdf_maekyung' 폴더에 PDF 파일이 없습니다! 파일을 넣어주세요.")
            st.stop()

        client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(timeout=600000)
        )
        
        mk_chat = client.chats.create(
            model="gemini-3.5-flash-lite",
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                temperature=0.8
            )
        )
        
        prompt_text = "업로드된 매경TEST 자료들 중 경제, 경영, 시사 전 범위에서 '완전 무작위(랜덤)'로 첫 번째 문제를 출제해줘!"
        init_res = None
        for attempt in range(3):
            try:
                init_res = mk_chat.send_message([*uploaded_files, prompt_text])
                break
            except Exception as e:
                if "RESOURCE_EXHAUSTED" in str(e):
                    st.error("무료 API 일일 쿼터를 초과했어. 결제를 설정하거나 내일 다시 시도해줘.")
                    st.stop()
                elif attempt < 2:
                    time.sleep(3)
                else:
                    raise e
        
        st.session_state.mk_chat = mk_chat
        st.session_state.mk_messages = [{"role": "assistant", "content": init_res.text}]

# 3. 대화 히스토리 출력
for msg in st.session_state.mk_messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# 4. 사용자 입력 및 과외 진행 (실시간 스트리밍 적용)
if user_input := st.chat_input("정답(예: 3번)을 입력하거나 질문해보세요 (예: 왜 답이 3번이야? / 힌트 줘)"):
    st.session_state.mk_messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        # 실시간 스트리밍 생성기 함수
        def generate_stream():
            for attempt in range(3):
                try:
                    stream = st.session_state.mk_chat.send_message_stream(user_input)
                    for chunk in stream:
                        if chunk.text:
                            yield chunk.text
                    return
                except Exception as e:
                    if "RESOURCE_EXHAUSTED" in str(e):
                        st.error("무료 API 일일 쿼터를 초과했어. 결제를 설정하거나 내일 다시 시도해줘.")
                        st.stop()
                    elif attempt < 2:
                        time.sleep(3)
                    else:
                        st.error("구글 서버 응답이 지연되고 있어. 다시 한번 엔터를 쳐줘!")
                        st.stop()

        # 글자가 실시간으로 촤르륵 타이핑되면서 출력됨
        full_response = st.write_stream(generate_stream())
        st.session_state.mk_messages.append({"role": "assistant", "content": full_response})