#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
連續成功分析系統 - 純精確排序位置版本
只顯示：排序1、排序2、排序3、排序4、排序5
過濾已實現的觸發條件
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
from itertools import combinations

class PurePositionAnalyzer:
    def __init__(self, csv_file):
        self.csv_file = csv_file
        self.df = None
        self.load_data()
    
    def load_data(self):
        """讀取數據"""
        print("載入數據中...")
        self.df = pd.read_csv(
            self.csv_file,
            header=None,
            names=['日期', '期號', '號1', '號2', '號3', '號4', '號5', 
                   '分隔', '排序1', '排序2', '排序3', '排序4', '排序5']
        )
        
        self.df['日期'] = pd.to_datetime(self.df['日期'])
        last_date = self.df['日期'].iloc[-2]
        print(last_date)
        print(f"✓ 載入 {len(self.df)} 期數據\n")
    
    def get_all_numbers(self, idx):
        row = self.df.iloc[idx]
        return [int(row[f'排序{i}']) for i in range(1, 6)]
    
    def get_number_at_position(self, idx, pos):
        row = self.df.iloc[idx]
        return int(row[f'排序{pos}'])
    
    def get_recent_numbers(self, days=3):
        # 1. 取得所有不重複的日期並排序（確保由舊到新）
        all_dates = sorted(self.df['日期'].unique())
        
        # 2. 直接取最後 N 個日期
        recent_dates = all_dates[-days:]
        
        print(f"最近 {len(recent_dates)} 個有資料的天數:")
        print("="*80)
        
        number_list = []
        # 接下來的邏輯基本保持不變，但保證 recent_dates 裡面一定有資料
        for date in recent_dates:
            # 因為 date 已經是 Timestamp 物件，直接篩選即可
            day_df = self.df[self.df['日期'] == date]
            
            if not day_df.empty:
                date_str = pd.to_datetime(date).strftime('%Y/%m/%d')
                print(f"\n{date_str}:")
                for idx in day_df.index:
                    row = day_df.loc[idx]
                    period = row['期號']
                    # 這裡假設你的欄位名稱是 '排序1', '排序2' ...
                    numbers = [int(row[f'排序{i}']) for i in range(1, 6)]
                    
                    print(f"  期號 {period}: " + 
                        " | ".join([f"排序{i+1}={n:02d}" for i, n in enumerate(numbers)]))
                    
                    for pos in range(1, 6):
                        number_list.append((numbers[pos-1], pos, idx, date_str, period))
        
        print(f"\n總共: {len(number_list)} 個號碼")
        print("="*80)
        
        # 取得這段期間內最後一筆的 index
        latest_idx = self.df[self.df['日期'].isin(recent_dates)].index.max()
        return number_list, latest_idx, recent_dates
    
    def check_already_success(self, trigger_num, trigger_pos, trigger_idx, latest_idx, target_nums):
        """檢查觸發條件是否已經在後續期數中成功"""
        for offset in range(1, 4):  # 檢查後續1-3期
            check_idx = trigger_idx + offset
            if check_idx > latest_idx:  # 超過最新數據
                break
            check_numbers = self.get_all_numbers(check_idx)
            for target_num in target_nums:
                if target_num in check_numbers:
                    return True  # 已經成功
        return False
    
    def count_consecutive(self, trigger_num, trigger_pos, target_nums, start_idx, look_ahead=3):
        count = 0
        records = []
        idx = start_idx
        
        while idx >= 0:
            current_num = self.get_number_at_position(idx, trigger_pos)
            if current_num != trigger_num:
                idx -= 1
                continue
            
            found = False
            found_info = None
            for offset in range(1, look_ahead + 1):
                check_idx = idx + offset
                if check_idx >= len(self.df):
                    break
                check_numbers = self.get_all_numbers(check_idx)
                for target_num in target_nums:
                    if target_num in check_numbers:
                        found = True
                        check_row = self.df.iloc[check_idx]
                        target_pos = check_numbers.index(target_num) + 1
                        found_info = {
                            'offset': offset,
                            'target': target_num,
                            'target_pos': target_pos,
                            'date': check_row['日期'].strftime('%Y/%m/%d'),
                            'period': check_row['期號']
                        }
                        break
                if found:
                    break
            
            trigger_row = self.df.iloc[idx]
            if found:
                count += 1
                records.append({
                    'date': trigger_row['日期'].strftime('%Y/%m/%d'),
                    'period': trigger_row['期號'],
                    'status': '成功',
                    'found': found_info
                })
                idx -= 1
            else:
                records.append({
                    'date': trigger_row['日期'].strftime('%Y/%m/%d'),
                    'period': trigger_row['期號'],
                    'status': '失敗'
                })
                break
        return count, records
    
    def analyze(self, days=3, min_single=3, min_double=5, min_triple=10):
        print("\n連續成功分析 - 純精確排序位置")
        print("="*80)
        print(f"門檻設定: 單球≥{min_single} | 雙球≥{min_double} | 三球≥{min_triple}")
        print("="*80)
        
        number_list, latest_idx, recent_dates = self.get_recent_numbers(days)
        start_idx = latest_idx - 1
        
        unique_triggers = {}
        for num, pos, idx, date, period in number_list:
            key = (num, pos, idx)
            if key not in unique_triggers:
                unique_triggers[key] = (num, pos, idx, date, period)
        
        unique_list = list(unique_triggers.values())
        all_numbers = sorted(list(set([num for num, _, _, _, _ in number_list])))
        
        print(f"\n觸發條件: {len(unique_list)} 個")
        print(f"目標球: {len(all_numbers)} 個")
        print("="*80)
        
        results = []
        filtered_count = 0
        
        for i, (trigger_num, trigger_pos, trigger_idx, _, _) in enumerate(unique_list, 1):
            print(f"\n[{i}/{len(unique_list)}] 分析: {trigger_num:02d} 在排序{trigger_pos}")
            found_single = 0
            found_double = 0
            found_triple = 0
            
            # 單球
            for target in all_numbers:
                if target == trigger_num:
                    continue
                
                # 檢查是否已經成功
                if self.check_already_success(trigger_num, trigger_pos, trigger_idx, latest_idx, [target]):
                    filtered_count += 1
                    continue
                
                count, records = self.count_consecutive(trigger_num, trigger_pos, [target], start_idx)
                if count >= min_single:
                    results.append({
                        'type': '單球',
                        'trigger': trigger_num,
                        'pos': trigger_pos,
                        'targets': [target],
                        'count': count,
                        'records': records
                    })
                    found_single += 1
            
            # 雙球
            for combo in combinations(all_numbers, 2):
                if trigger_num in combo:
                    continue
                
                if self.check_already_success(trigger_num, trigger_pos, trigger_idx, latest_idx, list(combo)):
                    filtered_count += 1
                    continue
                
                count, records = self.count_consecutive(trigger_num, trigger_pos, list(combo), start_idx)
                if count >= min_double:
                    results.append({
                        'type': '雙球',
                        'trigger': trigger_num,
                        'pos': trigger_pos,
                        'targets': list(combo),
                        'count': count,
                        'records': records
                    })
                    found_double += 1
            
            # 三球
            for combo in combinations(all_numbers, 3):
                if trigger_num in combo:
                    continue
                
                if self.check_already_success(trigger_num, trigger_pos, trigger_idx, latest_idx, list(combo)):
                    filtered_count += 1
                    continue
                
                count, records = self.count_consecutive(trigger_num, trigger_pos, list(combo), start_idx)
                if count >= min_triple:
                    results.append({
                        'type': '三球',
                        'trigger': trigger_num,
                        'pos': trigger_pos,
                        'targets': list(combo),
                        'count': count,
                        'records': records
                    })
                    found_triple += 1
            
            print(f"  找到: 單球{found_single}個 | 雙球{found_double}個 | 三球{found_triple}個")
        
        print(f"\n{'='*80}")
        print(f"完成！共 {len(results)} 個模式 (已過濾 {filtered_count} 個已實現的模式)")
        return results
    
    def export_csv(self, results, filename, min_single=3, min_double=5, min_triple=10):
        data = []
        for r in results:
            # 在每個號碼前加上單引號，防止Excel誤判為日期
            target_str = '/'.join([f"'{t:02d}" for t in r['targets']])
            dates = []
            for rec in r['records']:
                if rec['status'] == '成功':
                    info = rec['found']
                    dates.append(f"{rec['date']}期{rec['period']}→+{info['offset']}期{info['date']}期{info['period']}出現{info['target']:02d}排序{info['target_pos']}")
            
            data.append({
                '類型': r['type'],
                '觸發球': f"'{r['trigger']:02d}",
                '觸發位置': f"排序{r['pos']}",
                '目標球': target_str,
                '連續成功': r['count'],
                '成功日期列表': ' | '.join(dates)
            })
        
        df = pd.DataFrame(data)
        
        # 先按類型排序（三球、雙球、單球），再按連續次數降序
        type_order = {'三球': 0, '雙球': 1, '單球': 2}
        df['類型順序'] = df['類型'].map(type_order)
        df = df.sort_values(['類型順序', '連續成功'], ascending=[True, False])
        df = df.drop('類型順序', axis=1)
        df = df.reset_index(drop=True)
        
        # === 統計目標球出現次數（同一觸發條件下，一個號碼只算一次）===
        target_count = {}
        for r in results:
            trigger_key = (r['trigger'], r['pos'])
            for target in r['targets']:
                if target not in target_count:
                    target_count[target] = set()
                target_count[target].add(trigger_key)
        
        # 轉換成次數
        target_stats = [(num, len(triggers)) for num, triggers in target_count.items()]
        target_stats.sort(key=lambda x: (-x[1], x[0]))  # 按次數降序，號碼升序
        
        # 添加空行和統計表
        df = pd.concat([df, pd.DataFrame([{}] * 3)], ignore_index=True)  # 3個空行
        
        stats_data = []
        stats_data.append({
            '類型': '目標球統計',
            '觸發球': '號碼',
            '觸發位置': '出現次數',
            '目標球': '',
            '連續成功': '',
            '成功日期列表': ''
        })
        stats_data.append({
            '類型': '==========',
            '觸發球': '==========',
            '觸發位置': '==========',
            '目標球': '',
            '連續成功': '',
            '成功日期列表': ''
        })
        
        for num, count in target_stats:
            stats_data.append({
                '類型': '',
                '觸發球': f"'{num:02d}",
                '觸發位置': str(count),
                '目標球': '',
                '連續成功': '',
                '成功日期列表': ''
            })
        
        df = pd.concat([df, pd.DataFrame(stats_data)], ignore_index=True)
        
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        print(f"\n✓ 已導出: {filename}")
        
        # 統計數量
        single_count = len([r for r in results if r['type'] == '單球'])
        double_count = len([r for r in results if r['type'] == '雙球'])
        triple_count = len([r for r in results if r['type'] == '三球'])
        
        # 顯示完整列表
        print("\n" + "="*80)
        print(f"完整模式列表 (共 {len(results)} 個)")
        print(f"門檻設定: 單球≥{min_single}次 ({single_count}個) | 雙球≥{min_double}次 ({double_count}個) | 三球≥{min_triple}次 ({triple_count}個)")
        print("="*80)
        print(f"{'排名':<6}{'類型':<8}{'觸發球':<10}{'位置':<12}{'目標球':<30}{'連續':<6}")
        print("-"*80)
        
        for i, row in df.iterrows():
            if row['類型'] in ['單球', '雙球', '三球']:
                print(f"{i+1:<6}{row['類型']:<8}{row['觸發球']:<10}{row['觸發位置']:<12}{row['目標球']:<30}{row['連續成功']:<6}")
        
        # 顯示目標球統計
        print("\n" + "="*80)
        print("目標球出現次數統計 (同一觸發條件下，一個號碼只算一次)")
        print("="*80)
        print(f"{'號碼':<10}{'出現次數':<10}")
        print("-"*80)
        for num, count in target_stats:
            print(f"{num:02d}{'':<8}{count:<10}")
        print("="*80)

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    csv_file = os.path.join(script_dir, 'tw539.csv')
    
    # 門檻設定
    MIN_SINGLE = 3
    MIN_DOUBLE = 5
    MIN_TRIPLE = 10
    
    analyzer = PurePositionAnalyzer(csv_file)
    results = analyzer.analyze(days=3, min_single=MIN_SINGLE, min_double=MIN_DOUBLE, min_triple=MIN_TRIPLE)
    
    if results:
        output = os.path.join(script_dir, '連續成功分析_純位置.csv')
        analyzer.export_csv(results, output, MIN_SINGLE, MIN_DOUBLE, MIN_TRIPLE)

if __name__ == "__main__":
    main()