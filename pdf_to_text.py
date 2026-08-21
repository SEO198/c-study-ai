import os
import glob
import pdfplumber

def convert_pdfs_to_txt():
    PDF_DIR = "./pdf_data"  # PDF 파일들이 있는 폴더 경로
    output_txt_path = "all_questions.txt"  # 합쳐서 저장할 텍스트 파일 이름
    
    # PDF 파일 목록 찾기
    pdf_files = sorted(glob.glob(os.path.join(PDF_DIR, "*.pdf")))
    
    if not pdf_files:
        print(f"경고: '{PDF_DIR}' 폴더에 PDF 파일이 없습니다! 경로를 확인해주세요.")
        return

    print(f"총 {len(pdf_files)}개의 PDF 파일을 발견했습니다. 텍스트 추출을 시작합니다...")

    total_text = ""
    
    for file_path in pdf_files:
        file_name = os.path.basename(file_path)
        print(f"처리 중: {file_name}...")
        
        try:
            with pdfplumber.open(file_path) as pdf:
                total_text += f"\n\n==================== [파일 시작: {file_name}] ====================\n\n"
                for page_idx, page in enumerate(pdf.pages):
                    text = page.extract_text()
                    if text:
                        total_text += f"\n--- {file_name} (Page {page_idx + 1}) ---\n" + text
        except Exception as e:
            print(f"에러 발생 ({file_name}): {e}")

    # 결과 텍스트 파일로 저장 (UTF-8 인코딩)
    with open(output_txt_path, "w", encoding="utf-8") as f:
        f.write(total_text)
        
    print(f"\n[완료!] 모든 PDF 텍스트가 '{output_txt_path}' 파일로 성공적으로 저장되었습니다!")

if __name__ == "__main__":
    convert_pdfs_to_txt()