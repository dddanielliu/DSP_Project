from pypdf import PdfReader
import re
import os
import pandas as pd

def pdf_to_csv(pdf_path):
    all_text = []
    try:
        reader = PdfReader(pdf_path)
        number_of_pages = len(reader.pages)
        print(f"  頁數: {number_of_pages}")
        for i in range(number_of_pages):
            page = reader.pages[i]
            text = page.extract_text()
            if text is None:
                print(f"  第{i+1}頁無法擷取文字")
                continue
            text = re.sub(r'Page\\s*\\d+\\s+of\\s+\\d+', '', text, flags=re.IGNORECASE)
            text = re.sub(r'[ \\t]{2,}', ' ', text)
            text = re.sub(r'\\n{2,}', '\\n\\n', text)
            text = text.strip()
            all_text.append(text)

        content = '\n'.join(all_text)
        # 正則解析
        pattern = re.compile(r'(\d+)\.\s*\((\d+)\)\s*(.+?)(?=\d+\.\s*\(|$)', re.DOTALL) 
        results = []
        for match in pattern.finditer(content):
            number = match.group(1)
            answer = match.group(2)
            question = match.group(3).replace('\n', ' ').strip()
            results.append({'number': number, 'answer': answer, 'question': question})

        df = pd.DataFrame(results)
        if not os.path.exists("csvs"):
            os.makedirs("csvs")
        df.to_csv(os.path.join("csvs", os.path.basename(pdf_path).replace('.pdf', '.csv')), index=False, encoding='utf-8-sig')
    except Exception as e:
        print(f"  讀取失敗: {e}")

pdf_dir = "pdfs"
pdf_files = [os.path.join(pdf_dir, f) for f in os.listdir(pdf_dir) if f.lower().endswith('.pdf')]

for pdf_path in pdf_files:
    print(f"正在處理: {pdf_path}")
    pdf_to_csv(pdf_path)
