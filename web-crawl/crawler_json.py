#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
法規資料爬蟲程式
從全國法規資料庫爬取法規內容並轉換為 JSON 格式
支援處理內嵌表格的複雜結構
"""

import requests
from bs4 import BeautifulSoup
import json
import re


def parse_ascii_table(table_string):
    """
    解析 text-pre 格式的純文字表格字串，轉換為字典的列表 (List of Dictionaries)。
    
    Args:
        table_string (str): 包含 ASCII 表格的字串
        
    Returns:
        list: 字典列表，每個字典代表表格中的一行資料
    """
    lines = table_string.strip().split('\n')
    
    # 過濾掉邊框線 (包含─、┌、└、├的行)
    data_lines = [line for line in lines if '─' not in line and '┌' not in line and '└' not in line]
    
    # 至少需要 標頭、次標頭、一筆資料
    if len(data_lines) < 3:
        return []

    try:
        # 處理標頭
        header_main = data_lines[0].split('│')
        header_sub = data_lines[1].split('│')
        
        # 組合出完整的標頭 ["種類", "垂直方向", "水平方向"]
        headers = [
            header_main[1].strip(), 
            header_sub[1].strip(),
            header_sub[2].strip()
        ]

        # 處理資料列
        parsed_data = []
        for row_line in data_lines[2:]: # 從第三行開始是資料
            columns = [col.strip() for col in row_line.split('│')]
            # 正常資料行分割後會有4個元素(因為前後都有│)，例如 ['', '單管施工架', '五', '五點五']
            if len(columns) > len(headers):
                row_data = {
                    headers[0]: columns[1],
                    headers[1]: columns[2],
                    headers[2]: columns[3]
                }
                parsed_data.append(row_data)
                
        return parsed_data
    except IndexError:
        # 如果表格格式不如預期，返回空列表以避免程式崩潰
        print("警告：解析表格時發生錯誤，可能格式有變。將跳過此表格。")
        return []


def scrape_law_data(url):
    """
    爬取指定 URL 的法規資料並轉換為 JSON 格式。
    此版本能處理內嵌表格，並將其儲存為字典的列表。
    
    Args:
        url (str): 要爬取的法規網址
        
    Returns:
        dict: 包含法規資料的字典，如果失敗則返回 None
    """
    print(f"正在嘗試爬取網址: {url}")
    
    try:
        # 1. 模擬瀏覽器發送請求
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        response.encoding = 'utf-8'
        print("網頁原始碼獲取成功。")

        # 2. 解析 HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 3. 獲取法規標題 (修正：法規標題的正確 ID 是 'hlLawName')
        law_title_element = soup.find('a', id='hlLawName')
        if not law_title_element:
            print("錯誤：在 HTML 中找不到法規標題 (id='hlLawName')。")
            return None
        law_title = law_title_element.text.strip()
        print(f"成功找到法規標題: {law_title}")

        # 準備資料結構
        law_data = {law_title: {}}

        # 4. 查找所有法規內容的父容器 (修正：主要內容區塊的 ID 是 'pnLawFla')
        content_container = soup.find('div', id='pnLawFla')
        if not content_container:
            print("錯誤：找不到主要的法規內容容器 (id='pnLawFla')。")
            return None
            
        # 修正：遍歷內容區塊的所有子元素來區分章節和條文
        # law-reg-content 是實際包含章節和條文的 div
        current_chapter_key = ""
        elements = content_container.find('div', class_='law-reg-content').find_all(recursive=False)

        for element in elements:
            # 檢查這個元素是不是章節標題 (修正：章節標題的 class 是 'h3 char-2')
            if 'h3' in element.get('class', []) and 'char-2' in element.get('class', []):
                chapter_text = element.get_text(strip=True)
                match = re.match(r'(第\s*\S+\s*章)\s*(.*)', chapter_text)
                if match:
                    current_chapter_key = match.group(1).replace(" ", "")
                    chapter_name = match.group(2)
                    law_data[law_title][current_chapter_key] = {"name": chapter_name}
                else: # 處理沒有 "第 X 章" 的情況，例如附則
                    current_chapter_key = chapter_text
                    law_data[law_title][current_chapter_key] = {"name": ""}
                continue

            # 檢查這個元素是不是條文 (修正：每個條文都包在 class 'row' 的 div 中)
            if 'row' in element.get('class', []):
                article_no_element = element.find('div', class_='col-no')
                article_data_element = element.find('div', class_='col-data')

                if article_no_element and article_data_element:
                    article_no = article_no_element.get_text(strip=True)
                    
                    paragraphs = []
                    law_article_container = article_data_element.find('div', class_='law-article')
                    if law_article_container:
                        content_divs = law_article_container.find_all('div', recursive=False)
                        for content_div in content_divs:
                            if 'text-pre' in content_div.get('class', []):
                                table_raw_text = content_div.get_text()
                                parsed_table = parse_ascii_table(table_raw_text)
                                
                                # 直接將解析後的字典列表作為一個元素加入
                                if parsed_table: # 確保解析成功才加入
                                    paragraphs.append(parsed_table)
                            else:
                                p_text = content_div.get_text(strip=True)
                                if p_text:
                                    paragraphs.append(p_text)
                    else:
                        # 舊版本相容性：內容被包在多個 div 中，其 class 命名為 "line-xxxx"
                        content_divs = article_data_element.find_all('div', class_=re.compile(r'line-\d+'))
                        paragraphs = [div.get_text(strip=True) for div in content_divs if div.get_text(strip=True)]
                    
                    if not current_chapter_key:
                        current_chapter_key = "未分類"
                        law_data[law_title][current_chapter_key] = {"name": ""}

                    if paragraphs:
                        law_data[law_title][current_chapter_key][article_no] = paragraphs

        print("所有法條解析完成。")
        return law_data

    except requests.exceptions.RequestException as e:
        print(f"網路連線或請求錯誤: {e}")
        return None
    except Exception as e:
        print(f"處理資料時發生未預期的錯誤: {e}")
        return None


def save_to_json(data, filename=None):
    """
    將爬取的法規資料儲存為 JSON 檔案
    
    Args:
        data (dict): 要儲存的法規資料
        filename (str, optional): 檔案名稱，如果未提供則自動生成
        
    Returns:
        str: 儲存的檔案名稱
    """
    if not data:
        print("錯誤：沒有資料可儲存。")
        return None
        
    # 將結果轉換為 JSON 字串 (美化格式)
    json_output = json.dumps(data, ensure_ascii=False, indent=4)
    
    print("\n--- JSON 輸出結果預覽 ---")
    # 為了避免洗版，只印出前 500 個字元
    print(json_output[:500] + "\n...")
    
    # 儲存成檔案
    try:
        if not filename:
            filename = list(data.keys())[0] + '.json'
            
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(json_output)
        print(f"\n資料已成功儲存至檔案: {filename}")
        return filename
    except Exception as e:
        print(f"儲存檔案時發生錯誤: {e}")
        return None


def main():
    """
    主程式入口點
    """
    # 範例網址
    urls = [
        "https://law.moj.gov.tw/LawClass/LawAll.aspx?PCODE=N0060010",  # 職業安全衛生教育訓練規則
        "https://law.moj.gov.tw/LawClass/LawAll.aspx?PCODE=N0060014"   # 營造安全衛生設施標準
    ]
    
    print("=== 法規資料爬蟲程式 ===\n")
    
    for i, url in enumerate(urls, 1):
        print(f"處理第 {i} 個網址...")
        scraped_data = scrape_law_data(url)
        
        if scraped_data:
            filename = save_to_json(scraped_data)
            if filename and "營造安全衛生設施標準" in filename:
                print(f"您可以在檔案中查看 '第 59 條' 的內容，表格已是'字典列表'格式。")
        else:
            print(f"爬取第 {i} 個網址失敗。")
        
        print("-" * 50)


if __name__ == '__main__':
    main()
