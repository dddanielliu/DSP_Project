import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import unquote
import pandas as pd
import numpy as np
database=pd.DataFrame([],columns=["actname","chapter","title","article"])
import os
import re

#%%第二段
#urls=[]
# url = input('請輸入全國法規資料庫網址：')

#urls=urls[0:6] 
#start_time=time.time()
#print(start_time)

def crawl_questions(url, filename):
    web = requests.get(url)
    soup = BeautifulSoup(web.text, "html.parser")
    
    # 找出所有 class='row' 的 div (條文) 和 class='char-2' 的 div (章節標題)
    major_elements = soup.find_all('div', class_=['row', 'char-2']) 
    
    lawbase = pd.DataFrame([], columns=["actname", "chapter", "title", "subsection", "article"])
    current_chapter = ""  # 初始化章節名稱

    for element in major_elements:
        
        # 檢查是否為章節標題容器 (<div class="char-2">)
        if 'char-2' in element.get('class', []):
            
            chapter_text = element.text.strip()
            
            # --- 關鍵正規表達式清理步驟 ---
            # 1. 將 "第" 後面到 "章" 前面的所有空白字元 (\s 是所有空白字元的簡寫) 替換為空字串。
            # 2. 如果你的空白是 \xa0 (非中斷空格)，\s 也通常能涵蓋。
            #    如果你想更精確地匹配，可以使用 [\s\xa0]
            # 模式：(第)(空白字元+)(章) -> 替換成 \1\3 (即：第 + 章)
            cleaned_chapter_text = re.sub(
                r"第\s*(.*?)\s*章",                      # 匹配「第 ... 章」
                lambda m: "第" + m.group(1).replace(" ", "") + "章",  # 去除中間空白
                chapter_text,
                count=1                                 # 只處理第一個匹配
            )
            # 如果有多個空格，替換成單一空格
            cleaned_chapter_text = re.sub(r"\s+", " ", cleaned_chapter_text)
            
            current_chapter = cleaned_chapter_text
            
        # 檢查是否為條文容器 (<div class="row">)
        elif 'row' in element.get('class', []):
            
            title_div = element.find('div', class_='col-no')
            article_div = element.find('div', class_='law-article')
            if title_div and article_div:
                all_lines = article_div.find_all('div', recursive=False)
                current_subsection_id = 0

                # 1. Prepare for iteration
                current_section = None
                for line in all_lines:
                    line_classes = line.get('class', [])
                    if 'line-0000' in line_classes and 'show-number' in line_classes:
                        if current_section is not None:
                            title_text = title_div.text.replace("本條文有附件", "").replace(" ", "").strip()
                            exports = pd.DataFrame()
                            exports["actname"] = [filename]
                            exports["chapter"] = [current_chapter]
                            exports["title"] = [title_text]
                            exports["subsection"] = [current_subsection_id if current_subsection_id != 0 else np.nan]
                            exports["article"] = [current_section]
                            lawbase = pd.concat([lawbase, exports], ignore_index=True)
                            current_section = None
                        current_subsection_id += 1
                    
                    if current_section is None:
                        current_section = line.text.strip()
                    else:
                        current_section += "\n" + line.text.strip()
                
                if current_section is not None:
                    title_text = title_div.text.replace("本條文有附件", "").replace(" ", "").strip()
                        
                    exports = pd.DataFrame()
                    exports["actname"] = [filename]
                    exports["chapter"] = [current_chapter]
                    exports["title"] = [title_text]
                    exports["subsection"] = [current_subsection_id if current_subsection_id != 0 else np.nan]
                    exports["article"] = [current_section]
                    lawbase = pd.concat([lawbase, exports], ignore_index=True)
                    current_section = None

    return lawbase

def process_url(url: str):
    database=pd.DataFrame([],columns=["actname","chapter","title","subsection","article"])
    print("Crawling URL:", url)
    # Call the function with the URL
    web = requests.get(url)
    soup = BeautifulSoup(web.text, "html.parser")
    filename=soup.find('table').find('a').text
    lawbase=crawl_questions(url, filename)
    database=pd.concat([lawbase,database])
    #database.to_csv("{}.csv".format(filename))
    return (database, filename)

if __name__ == "__main__":
    with open(os.path.join(os.path.dirname(__file__),"links.txt"), "r") as file:
        urls = [line.strip() for line in file.readlines()]
    if os.path.exists("laws") is False:
        os.mkdir("laws")
    for url in urls:
        try:
            database, filename = process_url(url)
            database.to_csv(os.path.join(os.path.dirname(__file__), "laws", "{}_{}.csv".format(filename, url.replace(":", "_").replace("/", "_").replace("?", "_"))),index=False)
        except Exception as err:
            # direct download file
            print("Error occurred, trying to download file directly:", url, "({})".format(err))
            try:
                response = requests.get(url)
                if response.status_code == 200:
                    filename = url.split("/")[-1]
                    if os.path.exists(os.path.join(os.path.dirname(__file__),"pdfs")) is False:
                        os.mkdir("pdfs")
                    with open(os.path.join(os.path.dirname(__file__), "pdfs", unquote(filename)), "wb") as file:
                        file.write(response.content)
                    print(f"檔案已下載並儲存為: {filename}")
                else:
                    print(f"無法下載檔案，HTTP 狀態碼: {response.status_code}")
            except Exception as e:
                print(f"下載檔案時發生錯誤: {e}")
    #end_time=time.time()
    #print("花費時間:",end_time-start_time)