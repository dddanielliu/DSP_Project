import requests
from bs4 import BeautifulSoup
import os

# 1. 取得網頁所有 PDF 連結
url = "https://www.osh-soeasy.com/exam.html"
headers = {
    "User-Agent": "Mozilla/5.0",
    "Referer": url
}
response = requests.get(url, headers=headers)
soup = BeautifulSoup(response.text, "html.parser")
pdf_links = [a['href'] for a in soup.find_all('a', href=True) if a['href'].lower().endswith('.pdf')]

print(f"共找到 {len(pdf_links)} 個 PDF 連結")

# 2. 下載 PDF，並檢查是否為真正的 PDF
os.makedirs("pdfs", exist_ok=True)
for link in pdf_links:
    filename = os.path.join("pdfs", os.path.basename(link))
    pdf_url = link if link.startswith("http") else requests.compat.urljoin(url, link)
    r = requests.get(pdf_url, headers=headers)
    with open(filename, "wb") as f:
        f.write(r.content)
    # 檢查檔案開頭
    with open(filename, "rb") as f:
        head = f.read(5)
        if head != b"%PDF-":
            print(f"刪除非 PDF 檔案: {filename}")
            os.remove(filename)

# 3. 處理 PDF（以 pypdf 為例）
from pypdf import PdfReader
for pdf_file in os.listdir("pdfs"):
    if pdf_file.endswith(".pdf"):
        path = os.path.join("pdfs", pdf_file)
        try:
            reader = PdfReader(path)
            print(f"成功讀取: {pdf_file}，頁數: {len(reader.pages)}")
            # 你的處理邏輯
        except Exception as e:
            print(f"無法讀取 {pdf_file}: {e}")
