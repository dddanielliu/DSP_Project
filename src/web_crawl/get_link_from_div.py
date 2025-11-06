import os
from bs4 import BeautifulSoup
# from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
# from reportlab.lib.styles import getSampleStyleSheet
# from reportlab.lib.pagesizes import A4

# Read the div content from file
with open(os.path.join(os.path.dirname(__file__),"div.txt"), "r", encoding="utf-8") as f:
    html_content = f.read()

# Parse with BeautifulSoup
soup = BeautifulSoup(html_content, "html.parser")

# Extract all links
links = [a["href"] for a in soup.find_all("a", href=True)]

# Create a PDF
# pdf_file = "links.pdf"
# doc = SimpleDocTemplate(pdf_file, pagesize=A4)
# styles = getSampleStyleSheet()
# story = []

# story.append(Paragraph("Extracted Links:", styles["Title"]))
# story.append(Spacer(1, 12))

for i, link in enumerate(links, 1):
    print(link)
    # story.append(Paragraph(f"{i}. <a href='{link}'>{link}</a>", styles["Normal"]))
    # story.append(Spacer(1, 6))

# doc.build(story)

# print(f"Saved {len(links)} links to {pdf_file}")
