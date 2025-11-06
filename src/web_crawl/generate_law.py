"""
法規連結生成器
用途：根據輸入的法規名稱，從全國法規資料庫搜尋並返回該法規的連結
"""

import requests
from bs4 import BeautifulSoup
from urllib.parse import quote
import re
import os


def search_law_by_name(law_name):
    """
    根據法規名稱搜尋法規連結
    
    參數:
        law_name (str): 法規名稱，例如「勞動基準法」、「民法」等
        
    返回:
        dict: 包含法規資訊的字典，格式為：
              {
                  'name': 法規名稱,
                  'url': 法規連結,
                  'pcode': 法規編號
              }
              如果找不到則返回 None
    """
    # 全國法規資料庫的搜尋 API（使用正確的參數格式）
    search_url = "https://law.moj.gov.tw/Law/LawSearchResult.aspx"
    
    # 構建搜尋參數（根據官方網站的格式）
    params = {
        'cur': 'Ln',      # 當前位置
        'ty': 'LAW',      # 搜尋類型：法規名稱
        'kw': law_name,   # 關鍵字
    }
    
    # 添加 User-Agent 模擬瀏覽器
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'zh-TW,zh;q=0.9',
    }
    
    try:
        # 發送搜尋請求
        response = requests.get(search_url, params=params, headers=headers, timeout=10)
        response.encoding = 'utf-8'
        
        if response.status_code != 200:
            print(f"搜尋請求失敗，狀態碼：{response.status_code}")
            return None
        
        # 檢查是否為錯誤頁面
        if 'ErrorPage.aspx' in response.url or '系統發生非預期錯誤' in response.text:
            print(f"網站返回錯誤，可能無法處理搜尋請求")
            return None
        
        # 解析 HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 尋找搜尋結果表格
        result_table = soup.find('table', class_='table')
        
        if not result_table:
            print(f"找不到法規「{law_name}」")
            return None
        
        # 找第一筆搜尋結果（在 tbody 中）
        tbody = result_table.find('tbody')
        if not tbody:
            # 如果沒有 tbody，直接在 table 中找
            links = result_table.find_all('a', href=re.compile(r'pcode='))
        else:
            links = tbody.find_all('a', href=re.compile(r'pcode='))
        
        if links:
            link = links[0]
            href = link.get('href')
            law_title = link.text.strip()
            
            # 提取 PCODE
            pcode_match = re.search(r'[Pp][Cc][Oo][Dd][Ee]=([A-Za-z0-9]+)', href)
            pcode = pcode_match.group(1) if pcode_match else None
            
            # 構建完整的 URL（統一使用 LawAll.aspx 格式）
            if pcode:
                full_url = f"https://law.moj.gov.tw/LawClass/LawAll.aspx?pcode={pcode}"
            elif href.startswith('http'):
                full_url = href
            elif href.startswith('/'):
                full_url = f"https://law.moj.gov.tw{href}"
            else:
                full_url = f"https://law.moj.gov.tw/Law/{href}"
            
            # 清理 URL，移除多餘的參數，只保留 pcode
            if pcode and 'LawAll.aspx' not in full_url:
                full_url = f"https://law.moj.gov.tw/LawClass/LawAll.aspx?pcode={pcode}"
            
            return {
                'name': law_title,
                'url': full_url,
                'pcode': pcode
            }
        
        print(f"找不到法規「{law_name}」")
        return None
        
    except requests.exceptions.RequestException as e:
        print(f"網路請求錯誤：{e}")
        return None
    except Exception as e:
        print(f"發生錯誤：{e}")
        return None


def get_law_url_directly(law_name):
    """
    直接從法規資料庫首頁搜尋法規
    使用另一種搜尋方式，可能返回多筆結果
    
    參數:
        law_name (str): 法規名稱
        
    返回:
        list: 符合的法規資訊列表
    """
    search_url = "https://law.moj.gov.tw/Law/LawSearchResult.aspx"
    
    # 使用正確的參數格式
    params = {
        'cur': 'Ln',
        'ty': 'LAW',
        'kw': law_name,
    }
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    }
    
    try:
        response = requests.get(search_url, params=params, headers=headers, timeout=10)
        response.encoding = 'utf-8'
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 尋找所有搜尋結果
        results = []
        
        # 找到所有包含 pcode 的連結
        links = soup.find_all('a', href=re.compile(r'pcode=', re.IGNORECASE))
        
        for link in links:
            href = link.get('href')
            title = link.text.strip()
            
            # 過濾掉空標題或非法規連結
            if href and title and 'AddHotLaw' in href:
                # 提取 PCODE
                pcode_match = re.search(r'[Pp][Cc][Oo][Dd][Ee]=([A-Za-z0-9]+)', href)
                pcode = pcode_match.group(1) if pcode_match else None
                
                if pcode:
                    # 構建標準的法規連結
                    full_url = f"https://law.moj.gov.tw/LawClass/LawAll.aspx?pcode={pcode}"
                    
                    results.append({
                        'name': title,
                        'url': full_url,
                        'pcode': pcode
                    })
        
        return results
        
    except Exception as e:
        print(f"搜尋發生錯誤：{e}")
        return []


def save_to_links_file(url, filename="links.txt"):
    """
    將法規連結保存到 links.txt 檔案
    
    參數:
        url (str): 要保存的法規連結
        filename (str): 目標檔案名稱，預設為 "links.txt"
    
    返回:
        bool: 保存成功返回 True，失敗返回 False
    """
    try:
        # 檢查連結是否已存在
        if os.path.exists(filename):
            with open(filename, 'r', encoding='utf-8') as f:
                existing_links = f.read().splitlines()
                if url in existing_links:
                    print(f"ℹ️  連結已存在於 {filename} 中")
                    return True
        
        # 將連結追加到檔案末尾
        with open(filename, 'a', encoding='utf-8') as f:
            f.write(url + '\n')
        
        print(f"連結已保存至 {filename}")
        return True
        
    except Exception as e:
        print(f"保存連結時發生錯誤：{e}")
        return False


def search_and_save(law_name, filename="links.txt"):
    """
    搜尋法規並自動保存到 links.txt
    
    參數:
        law_name (str): 法規名稱
        filename (str): 目標檔案名稱，預設為 "links.txt"
    
    返回:
        dict or None: 成功返回法規資訊字典，失敗返回 None
    """
    result = search_law_by_name(law_name)
    
    if result:
        save_to_links_file(result['url'], filename)
        return result
    else:
        # 嘗試備用方法
        results = get_law_url_directly(law_name)
        if results:
            save_to_links_file(results[0]['url'], filename)
            return results[0]
    
    return None


def main():
    """
    主程式：提供互動式介面讓使用者輸入法規名稱並取得連結
    """
    print("=" * 60)
    print("全國法規資料庫 - 法規連結查詢工具")
    print("=" * 60)
    
    while True:
        print("\n請輸入法規名稱（輸入 'q' 或 'quit' 離開）：")
        law_name = input("> ").strip()
        
        if law_name.lower() in ['q', 'quit', 'exit']:
            print("感謝使用！")
            break
        
        if not law_name:
            print("請輸入有效的法規名稱！")
            continue
        
        print(f"\n正在搜尋「{law_name}」...")
        
        # 嘗試搜尋
        result = search_law_by_name(law_name)
        
        if result:
            print("\n" + "=" * 60)
            print(f"法規名稱：{result['name']}")
            print(f"法規編號：{result['pcode']}")
            print(f"法規連結：{result['url']}")
            print("=" * 60)
            
            # 自動保存連結到 links.txt
            save_to_links_file(result['url'])
            
        else:
            # 如果第一種方法失敗，嘗試第二種方法
            print("嘗試使用其他搜尋方式...")
            results = get_law_url_directly(law_name)
            
            if results:
                print(f"\n找到 {len(results)} 筆相關法規：")
                print("=" * 60)
                for idx, item in enumerate(results, 1):
                    print(f"{idx}. 法規名稱：{item['name']}")
                    print(f"   法規編號：{item['pcode']}")
                    print(f"   法規連結：{item['url']}")
                    print("-" * 60)
                
                # 詢問是否要保存第一筆結果
                if results:
                    save_choice = input("\n是否要將第一筆結果保存到 links.txt？(y/n): ").strip().lower()
                    if save_choice in ['y', 'yes', '是']:
                        save_to_links_file(results[0]['url'])
            else:
                print(f"很抱歉，找不到「{law_name}」相關的法規。")


if __name__ == "__main__":
    main()
