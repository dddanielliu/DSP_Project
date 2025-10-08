import tiktoken
import re
from typing import List

# --- 參數設定 (400_200) ---
MAX_TOKENS = 500
CHUNK_OVERLAP = 200

# 調整後的分隔符順序：優先使用「大」結構來切分，以獲得更寬鬆的 Chunk
SEPARATORS = [
    r"\s*\n{2,}\s*",   # 1. 結構性分隔 (多於一個換行符) -> 優先切段落
    "\n",             # 2. 單行換行符 (段落內換行)
    "；", ";",          # 3. 分號 (較長的語義單元)
    "。", "！", "？",  # 4. 中文句尾標點 (降級，除非段落過長才使用)
    ". ", "! ", "? ", # 5. 英文句尾標點 (注意後接空格)
    "，", ",",          # 6. 逗號
    "、",              # 7. 頓號
    " ",               # 8. 空格
    ""                 # 9. 最差情況：強制字元切分
]

# 初始化 Tokenizer (使用常用的 LLM 編碼)
ENCODER = tiktoken.encoding_for_model("gpt-3.5-turbo")

def count_tokens(text: str) -> int:
    """計算文本的 Token 數量。"""
    # 避免空字串錯誤
    if not text:
        return 0
    return len(ENCODER.encode(text))

def recursive_chunker(text: str) -> List[str]:
    """
    遞歸地將文本切分為語義塊 (Token 數 <= 400)，
    接著合併小塊，最後應用 400 Token / 200 Token 重疊。
    這個版本旨在產生更「寬鬆」的 Chunk。
    """
    
    # 內部遞歸函式，用於處理分割邏輯
    def _recursive_split(current_texts: List[str], separators: List[str]) -> List[str]:
        # 1. 停止條件：所有文本塊都滿足長度要求
        if all(count_tokens(t) <= MAX_TOKENS for t in current_texts):
            return current_texts
        
        # 2. 終極失敗：耗盡所有分隔符，進行強制切分
        if not separators:
            final_forced_chunks = []
            for text_to_split in current_texts:
                if count_tokens(text_to_split) > MAX_TOKENS:
                    tokens = ENCODER.encode(text_to_split)
                    # 強制按 MAX_TOKENS 分割
                    for i in range(0, len(tokens), MAX_TOKENS):
                        chunk_tokens = tokens[i : i + MAX_TOKENS]
                        final_forced_chunks.append(ENCODER.decode(chunk_tokens))
                else:
                    final_forced_chunks.append(text_to_split)
            return final_forced_chunks

        # 3. 執行當前最高優先級的切分
        current_separator = separators[0]
        next_separators = separators[1:]
        
        new_text_list = []
        for text_to_split in current_texts:
            if count_tokens(text_to_split) > MAX_TOKENS:
                
                # 處理 Regex/字串分隔符
                if current_separator.startswith(r"\s*") or not current_separator:
                    # 使用 re.split 處理所有情況，包含 "" (最終強制切分應處理)
                    sub_texts = re.split(current_separator, text_to_split)
                    new_text_list.extend([t.strip() for t in sub_texts if t.strip()])
                else:
                    sub_texts = text_to_split.split(current_separator)
                    
                    # 重新組裝子文本，將分隔符加回前一塊
                    for i, sub_text in enumerate(sub_texts):
                        if sub_text.strip():
                            # 將分隔符加到前一塊的末尾
                            # 由於這裡不是直接強制切分，而是遞歸，將分隔符加回有助於語義完整
                            if i > 0 and new_text_list:
                                new_text_list[-1] += current_separator
                            
                            new_text_list.append(sub_text.strip())
            else:
                new_text_list.append(text_to_split)
        
        # 4. 遞歸處理新切分的子塊
        filtered_list = [t for t in new_text_list if t]
        return _recursive_split(filtered_list, next_separators)

    # -----------------------------------------------
    # 核心邏輯開始
    # -----------------------------------------------
    # 1. 執行遞歸切分，獲得所有 <= 400 Token 的語義塊
    initial_chunks = _recursive_split([text], SEPARATORS)

    # 2. 廣度優化：後處理合併 (Merging) 邏輯 - 解決「單句切一次」的問題
    # 將相鄰的小語義塊合併起來，直到接近 MAX_TOKENS
    merged_chunks = []
    current_chunk = ""
    
    for next_chunk in initial_chunks:
        # 使用換行符連接，保持語義塊間的區隔
        test_chunk = (current_chunk + "\n" + next_chunk).strip()
        
        if not current_chunk:
            # 第一個塊，直接開始
            current_chunk = next_chunk
        elif count_tokens(test_chunk) <= MAX_TOKENS:
            # 合併後沒有超限，則合併 (實現更寬鬆的 Chunk)
            current_chunk = test_chunk
        else:
            # 合併後超限，則將當前塊定稿，並用新塊開始下一個塊
            merged_chunks.append(current_chunk)
            current_chunk = next_chunk
            
    # 處理最後一個塊
    if current_chunk:
        merged_chunks.append(current_chunk)

    # -----------------------------------------------
    # 3. 深度優化：應用 400/200 的重疊 (Striding) 邏輯
    # -----------------------------------------------
    final_chunks = []
    
    # 對合併後的 Chunk 列表進行重疊處理
    for chunk in merged_chunks:
        tokens = ENCODER.encode(chunk)
        start = 0
        while start < len(tokens):
            end = min(start + MAX_TOKENS, len(tokens))
            
            # 解碼 Token 列表為文本
            final_chunks.append(ENCODER.decode(tokens[start:end]))

            if end == len(tokens):
                break
            
            # 移動起始指針，實現 200 Token 重疊
            # MAX_TOKENS - CHUNK_OVERLAP = 400 - 200 = 200
            start += MAX_TOKENS - CHUNK_OVERLAP
            
    return final_chunks

if __name__ == "__main__":
    # --- 範例使用 ---
    mixed_text = """
    壓力容器安全檢查構造標準,第4條,第一種壓力容器或第一種壓力容器之受壓部分，不得使用附表一規定之材料。
    壓力容器安全檢查構造標準,第5條,材料之容許抗拉應力，應依下列規定。但鑄造件，不在此限：一、鋼鐵材料及非鐵系金屬材料之容許抗拉應力，取下列各目規定算得之值中之最小之值：（一）常溫時之抗拉強度之最小值之四分之一。（二）材料於使用溫度時之抗拉強度之四分之一。（三）常溫時之降伏點或百分之零點二耐力之最小值之一點五分之一。（四）材料於使用溫度時之降伏點或百分之零點二耐力之一點五分之一；沃斯田鐵系不銹鋼鋼料使用於可因使用處所而允許稍微變形之部位者，得取材料於使用溫度時之百分之零點二耐力之百分之九十。二、國家標準 CNS  四二七一「壓力容器用鋼板」、國家標準 CNS  八九七三「壓力容器用調質型錳鉬鋼及錳鉬鎳鋼鋼板」、國家標準CNS八六九七「低溫壓力容器用碳鋼鋼板」與國家標準CNS八六九八「低溫壓力容器用鎳鋼鋼板」規定之鋼鐵材料及具有同等以上機械性質者，其容許抗拉應力，得取下列各目規定算得之值中較小之值，不受前款規定之限制：（一）常溫時之降伏點或百分之零點二耐力之最小值之 0.5（1.6-γ）倍之值；其中，γ為降伏點或百分之零點二耐力與抗拉強度之比值。但γ值未滿零點七時應取零點七；第二目之γ，亦同。（二）材料於使用溫度時之降伏點或百分之零點二耐力之 0.5（1.6-γ）倍之值。三、以熱處理提高強度之螺栓，其容許抗拉應力，應取第一款規定算得之值及依下列規定算得之值中最小之值，不受第一款規定之限制：（一）常溫時之抗拉強度之最小值之五分之一。（二）常溫時之降伏點或百分之零點二耐力之最小值之四分之一。材料之使用溫度在該材料之潛變領域內者，其容許抗拉應力，應取下列規定算得之值中最小之值，不受前項規定之限制：一、在該溫度下，於一千小時內發生百分之零點零一潛變之應力之平均值。二、在該溫度下，於十萬小時即發生破裂之應力之平均值之一點五分之一。三、在該溫度下，於十萬小時即發生破裂之應力之最小值之一點二五分之一
    壓力容器安全檢查構造標準,第6條,鑄造件之容許抗拉應力，應依下列各款規定：一、鑄鐵件之容許抗拉應力，取下列規定算得之值：（一）國家標準 CNS  二九三六「黑心展性鑄鐵件」、國家標準 CNS  二八六九「球狀石墨鑄鐵件」之FCD四○○、FCD四五○及具有與其同等以上之機械性質者：材料於使用溫度時之抗拉強度之六點二五分之一。（二）其他鑄鐵件：材料於使用溫度時之抗拉強度之十分之一。二、鑄鋼件之容許抗拉應力，取下列規定之鑄造係數與依前條第一項第一款或第二項之規定算得之值相乘所得之值：（一）國家標準 CNS  二九○六「碳鋼鑄鋼件」，其化學成分含量，在依附表二規定值以下者，及國家標準CNS七一四三「熔接結構用鑄鋼件」、國家標準CNS四○○○「不銹鋼鑄鋼件」、國家標準CNS七一四七「高溫高壓用鑄鋼件」、國家標準CNS七一四九「低溫高壓用鑄鋼件」之鑄造係數：零點八。（二）經依附表三規定檢查合格者，分別依同表之檢查種類及方法，取其鑄造係數：零點九或一。（三）其他鑄鋼件之鑄造係數：零點六七。三、非鐵系金屬鑄造件之容許抗拉應力，取前條第一項第一款算得之值乘以鑄造係數零點八所得之值。
    壓力容器安全檢查構造標準,第7條,"護面鋼之容許抗拉應力，依下式計算：      σa1t1＋σa2t2
    """

    chunks = recursive_chunker(mixed_text)

    print(f"原始文本 Token 數: {count_tokens(mixed_text)}")
    print(f"總共產生了 {len(chunks)} 個最終文本塊。")
    print("---")

    # 輸出結果檢查
    for i, chunk in enumerate(chunks):
        token_count = count_tokens(chunk)
        print(f"Chunk {i+1} (Tokens: {token_count}, 字數: {len(chunk)}):")
        print(chunk.strip())
        print("-" * 20)
