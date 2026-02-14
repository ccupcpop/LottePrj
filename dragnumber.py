import pandas as pd
from collections import Counter
from datetime import datetime
import os
import shutil
import urllib.request

# CSV 下載對應表
CSV_URLS = {
    'tw539.csv': 'https://biga.com.tw/HISTORYDATA/tw539.csv',
    'us539.csv': 'https://biga.com.tw/HISTORYDATA/us539.csv',
}

def download_csv(csv_filename):
    """下載最新 CSV 覆蓋本地檔案"""
    url = CSV_URLS.get(os.path.basename(csv_filename))
    if not url:
        print(f"⚠ 未知的 CSV 檔案: {csv_filename}，跳過下載")
        return
    script_dir = os.path.dirname(os.path.abspath(__file__))
    local_path = os.path.join(script_dir, os.path.basename(csv_filename))
    print(f"下載 {url} ...")
    urllib.request.urlretrieve(url, local_path)
    print(f"✓ 已下載: {local_path}")

def analyze_lottery(csv_filename, days_back=120, use_occurrence_limit=False, max_occurrences=5, threshold=1, validate_position=False, trigger_count=7):
    """
    分析539彩票拖牌統計
    
    Args:
        csv_filename: CSV檔案名稱
        days_back: 往前搜尋的期數，預設120
        use_occurrence_limit: 是否使用出現次數限制（True=只統計前N次出現，False=統計天數內所有）
        max_occurrences: 當use_occurrence_limit=True時，限制統計的出現次數
        threshold: 顯示門檻值，只顯示出現次數大於此值的號碼
        validate_position: 是否驗證號碼位置有效性（True=只統計符合位置區間的號碼）
        trigger_count: 取最後幾筆作為觸發條件，預設7
    """
    # 讀取資料
    df = pd.read_csv(
        csv_filename,
        header=None,
        names=['日期', '期號', '號1', '號2', '號3', '號4', '號5', 
               '分隔', '排序1', '排序2', '排序3', '排序4', '排序5']
    )
    
    df['日期'] = pd.to_datetime(df['日期'])
    df = df.sort_values('日期').reset_index(drop=True)
    #df = df.iloc[:-1]
    # 定義位置區間
    position_ranges = {
        1: (1, 8),
        2: (9, 16),
        3: (17, 24),
        4: (25, 32),
        5: (33, 39)
    }
    
    # 取得最後N筆
    last_n_indices = list(range(len(df) - trigger_count, len(df)))  # 獲取最後N筆在df中的真實index
    last_n = df.iloc[last_n_indices].reset_index(drop=True)
    
    # 準備輸出內容
    output_lines = []
    
    # 全局統計用
    global_tail_counter = Counter()
    global_number_counter = Counter()  # 全局號碼統計
    
    header = "=" * 80
    output_lines.append(header)
    output_lines.append(f"最後{trigger_count}筆數據作為觸發條件：")
    output_lines.append(header)
    
    for i in range(trigger_count - 1, -1, -1):  # 從最後1筆到倒數第N筆
        row = last_n.iloc[i]
        line = f"倒數第{trigger_count-i}筆 ({row['日期'].strftime('%Y/%m/%d')} 期{row['期號']}): 排序1={int(row['排序1'])}, 排序2={int(row['排序2'])}, 排序3={int(row['排序3'])}, 排序4={int(row['排序4'])}, 排序5={int(row['排序5'])}"
        output_lines.append(line)
    
    output_lines.append("")
    
    validation_text = "啟用位置驗證 (排序1:1-8, 排序2:9-16, 排序3:17-24, 排序4:25-32, 排序5:33-39)" if validate_position else "不驗證位置"
    output_lines.append(f"資料有效性檢查: {validation_text}")
    output_lines.append("")
    
    # 對每個觸發條件進行分析（從最後1筆開始）
    for trigger_idx in range(trigger_count - 1, -1, -1):
        trigger_row = last_n.iloc[trigger_idx]
        trigger_global_idx = last_n_indices[trigger_idx]  # 獲取在完整df中的真實index
        periods_ahead = trigger_count - trigger_idx  # 最後1筆找下1期，倒數第2筆找下2期...
        
        search_method = f"前{max_occurrences}次出現" if use_occurrence_limit else f"過去{days_back}筆"
        
        output_lines.append(header)
        output_lines.append(f"觸發條件 #{trigger_count-trigger_idx} (倒數第{trigger_count-trigger_idx}筆)")
        output_lines.append(f"日期: {trigger_row['日期'].strftime('%Y/%m/%d')} 期號: {trigger_row['期號']}")
        output_lines.append(f"找下 {periods_ahead} 期的號碼統計 (搜尋範圍: {search_method}, 顯示門檻: >{threshold})")
        output_lines.append(header)
        
        # 對每個排序位置進行統計
        for pos in range(1, 6):
            trigger_num = int(trigger_row[f'排序{pos}'])
            
            # 如果啟用位置驗證，檢查號碼是否在有效區間內
            if validate_position:
                min_val, max_val = position_ranges[pos]
                if not (min_val <= trigger_num <= max_val):
                    output_lines.append(f"\n排序{pos} = {trigger_num:02d} [跳過: 不在有效區間 {min_val}-{max_val}]")
                    output_lines.append("-" * 80)
                    continue
            
            output_lines.append(f"\n排序{pos} = {trigger_num:02d}")
            output_lines.append("-" * 80)
            
            # 統計下期號碼
            all_next_nums = []
            match_count = 0
            occurrence_count = 0  # 出現次數計數器
            match_records = []  # 記錄匹配的日期期號
            
            # 從觸發條件往前搜尋（不包含觸發條件本身）
            search_start = trigger_global_idx - 1
            
            # 如果使用出現次數限制，就不限制搜尋範圍；否則用天數限制
            if use_occurrence_limit:
                search_end = 0  # 搜尋到最早的資料
            else:
                search_end = max(0, trigger_global_idx - days_back)

            for i in range(search_start, search_end - 1, -1):
                # 確保下N期存在（往後數N筆資料）
                if i + periods_ahead >= len(df):
                    continue
                    
                current_num = int(df.loc[i, f'排序{pos}'])
                
                # 如果啟用位置驗證，檢查搜尋到的號碼是否也在有效區間內
                if validate_position:
                    min_val, max_val = position_ranges[pos]
                    if not (min_val <= current_num <= max_val):
                        continue
                
                # 如果排序位置的號碼匹配
                if current_num == trigger_num:
                    # 如果使用出現次數限制，檢查是否已達上限
                    if use_occurrence_limit and occurrence_count >= max_occurrences:
                        break
                    
                    match_count += 1
                    occurrence_count += 1
                    
                    # 記錄匹配的日期和期號
                    match_date = df.loc[i, '日期'].strftime('%Y/%m/%d')
                    match_period = df.loc[i, '期號']
                    
                    # 取得當期的5個號碼
                    current_nums = [int(df.loc[i, f'排序{j}']) for j in range(1, 6)]
                    
                    # 取得下N期的號碼（往後數N筆）
                    next_idx = i + periods_ahead
                    next_row = df.iloc[next_idx]
                    next_nums = [int(next_row[f'排序{j}']) for j in range(1, 6)]
                    next_date = next_row['日期'].strftime('%Y/%m/%d')
                    next_period = next_row['期號']
                    
                    # 統計下期的所有號碼（不管當期有沒有）
                    all_next_nums.extend(next_nums)
                    
                    # 記錄這次匹配的詳細資訊
                    current_nums_str = ', '.join([f"{n:02d}" for n in current_nums])
                    next_nums_str = ', '.join([f"{n:02d}" for n in next_nums])
                    match_records.append(f"  第{occurrence_count}次: {match_date} 期{match_period} [{current_nums_str}] → 下{periods_ahead}期 {next_date} 期{next_period} [{next_nums_str}]")
            
            # 統計1-39號碼出現次數
            counter = Counter(all_next_nums)
            
            output_lines.append(f"找到 {match_count} 次匹配")
            
            # 顯示匹配記錄
            if match_records:
                output_lines.append(f"\n匹配記錄:")
                output_lines.extend(match_records)
            
            output_lines.append(f"\n下期號碼出現次數 (>{threshold})：")
            
            # 只顯示大於門檻值的號碼
            filtered_nums = []
            for num in range(1, 40):
                count = counter.get(num, 0)
                if count > threshold:
                    filtered_nums.append((num, count))
                    bar = '█' * min(count, 30)
                    line = f"  號碼 {num:2d}: {count:3d} 次  {bar}"
                    output_lines.append(line)
                    global_number_counter[num] += count  # 加到全局號碼統計
            
            if not filtered_nums:
                output_lines.append(f"  (沒有號碼出現次數 > {threshold})")
            else:
                # 統計尾數
                tail_counter = Counter()
                for num, count in filtered_nums:
                    tail = num % 10
                    tail_counter[tail] += count
                    global_tail_counter[tail] += count  # 加到全局統計
                
                output_lines.append(f"\n尾數統計 (基於上述 >{threshold} 的號碼)：")
                output_lines.append("-" * 80)
                
                # 按尾數排序（0-9）
                for tail in range(10):
                    count = tail_counter.get(tail, 0)
                    if count > 0:
                        bar = '█' * min(count, 30)
                        line = f"  {tail}尾: {count:3d} 次  {bar}"
                        output_lines.append(line)
        
        output_lines.append("\n")
    
    # 全局號碼統計總結
    output_lines.append(header)
    output_lines.append("全局號碼統計總結 (所有觸發條件加總，僅顯示 >門檻值 的號碼)")
    output_lines.append(header)
    output_lines.append("")
    
    if global_number_counter:
        # 按次數降序排列
        sorted_numbers = sorted(global_number_counter.items(), key=lambda x: (-x[1], x[0]))
        for num, count in sorted_numbers:
            bar = '█' * min(count, 50)
            line = f"  號碼 {num:2d}: {count:4d} 次  {bar}"
            output_lines.append(line)
    else:
        output_lines.append("  (沒有數據)")
    
    output_lines.append("")
    
    # 全局尾數統計總結
    output_lines.append(header)
    output_lines.append("全局尾數統計總結 (所有觸發條件加總)")
    output_lines.append(header)
    output_lines.append("")
    
    if global_tail_counter:
        # 按次數降序排列
        sorted_tails = sorted(global_tail_counter.items(), key=lambda x: (-x[1], x[0]))
        for tail, count in sorted_tails:
            bar = '█' * min(count, 50)
            line = f"  {tail}尾: {count:4d} 次  {bar}"
            output_lines.append(line)
    else:
        output_lines.append("  (沒有數據)")
    
    output_lines.append("")
    output_lines.append(header)
    
    # 打印到螢幕
    for line in output_lines:
        print(line)
    
    # 建立輸出目錄（先清空再建立）
    output_dir = os.path.join(os.path.dirname(os.path.abspath(csv_filename)) if os.path.dirname(csv_filename) else os.path.dirname(os.path.abspath(__file__)), 'drag_output')
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    os.makedirs(output_dir)
    
    # 建立輸出檔名
    csv_basename = os.path.splitext(os.path.basename(csv_filename))[0]
    last_date = last_n.iloc[-1]['日期'].strftime('%Y%m%d')
    search_suffix = f"前{max_occurrences}次" if use_occurrence_limit else f"{days_back}筆"
    validate_suffix = "_驗證位置" if validate_position else ""
    filename = os.path.join(output_dir, f"{csv_basename}_{last_date}_號碼統計_{search_suffix}_門檻{threshold}{validate_suffix}.txt")
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write('\n'.join(output_lines))
    
    print(f"\n✓ 已存檔: {filename}")
    return filename

def main():
    # 設定參數
    CSV_FILENAME = 'tw539.csv'  # CSV檔案名稱
    DAYS_BACK = 30  # 往前搜尋的期數
    USE_OCCURRENCE_LIMIT = True  # True=只統計前N次出現，False=統計天數內所有
    MAX_OCCURRENCES = 6  # 當USE_OCCURRENCE_LIMIT=True時，限制統計的出現次數
    THRESHOLD = 1  # 顯示門檻值，只顯示出現次數大於此值的號碼
    VALIDATE_POSITION = False  # True=驗證號碼位置，False=不驗證
    TRIGGER_COUNT = 3  # 取最後幾筆作為觸發條件
    
    # 下載最新 CSV
    download_csv(CSV_FILENAME)
    
    # 執行分析
    analyze_lottery(
        csv_filename=CSV_FILENAME,
        days_back=DAYS_BACK, 
        use_occurrence_limit=USE_OCCURRENCE_LIMIT,
        max_occurrences=MAX_OCCURRENCES,
        threshold=THRESHOLD,
        validate_position=VALIDATE_POSITION,
        trigger_count=TRIGGER_COUNT
    )

if __name__ == "__main__":
    main()