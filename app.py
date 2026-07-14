import streamlit as st
import io
import csv
import re

# ==========================================
# 網頁版面設定
# ==========================================
st.set_page_config(page_title="💊 健保大數據自動整併中心", layout="wide")
st.title("💊 健保藥品大數據：用量、價格與主檔自動整併系統")
st.markdown("這是一個採用 **「極速純 Python 引擎」** 的永續整併工具。不依賴肥大套件，完美相容所有雲端環境！")
st.markdown("---")

# ==========================================
# 檔案上傳區塊
# ==========================================
col1, col2, col3 = st.columns(3)

with col1:
    st.subheader("📁 1. 藥品成分/分類主檔")
    master_file = st.file_uploader("上傳 A21030000I-E41001.csv", type=['csv'])

with col2:
    st.subheader("📈 2. 歷年醫令用量檔")
    volume_files = st.file_uploader("上傳用量 CSV (可多選)", type=['csv'], accept_multiple_files=True)

with col3:
    st.subheader("💰 3. 最新健保價查詢檔")
    price_files = st.file_uploader("上傳 TXT 原始檔 (可多選)", type=['txt'], accept_multiple_files=True)

# ==========================================
# 純 Python 解析與整併核心 (無 Pandas 依賴)
# ==========================================
if st.button("🚀 開始一鍵無腦融合", type="primary"):
    if not master_file or not volume_files or not price_files:
        st.error("⚠️ 請確保三大類的檔案皆已上傳！")
    else:
        with st.spinner('⚙️ 引擎正在全速處理中...'):
            try:
                # --- 1. 讀取與解析主檔 (Master) ---
                master_bytes = master_file.getvalue()
                master_text = master_bytes.decode('utf-8-sig', errors='ignore')
                master_reader = csv.reader(io.StringIO(master_text))
                
                master_headers = next(master_reader, None)
                if not master_headers:
                    st.error("主檔格式有誤，請確認是否為 CSV。")
                    st.stop()
                
                # 找出「藥品代號」在第幾個欄位
                code_idx = -1
                for idx, h in enumerate(master_headers):
                    if '代號' in h or '代碼' in h or 'ID' in h.upper():
                        code_idx = idx
                        break
                
                if code_idx == -1:
                    code_idx = 0  # 預設為第一個欄位
                
                # 重新命名該標題為「健保藥品代碼」
                master_headers[code_idx] = "健保藥品代碼"
                
                # 載入主檔數據，以藥品代碼為 Key 去重
                master_data = {}
                for row in master_reader:
                    if not row: continue
                    key = row[code_idx].strip()
                    if key and key not in master_data:
                        master_data[key] = row

                # --- 2. 處理用量檔 (Volumes) ---
                # 用一個字典記錄：{藥品代碼: {年份: 總用量}}
                volume_map = {}
                years_found = set()
                
                for v_file in volume_files:
                    # 辨識年份
                    year = "111年" if "111" in v_file.name else ("112年" if "112" in v_file.name else "113年")
                    years_found.add(year)
                    
                    v_text = v_file.getvalue().decode('utf-8-sig', errors='ignore')
                    v_reader = csv.reader(io.StringIO(v_text))
                    v_headers = next(v_reader, None)
                    if not v_headers: continue
                    
                    # 定位代碼與用量欄位
                    v_code_idx = -1
                    v_val_idx = -1
                    for idx, h in enumerate(v_headers):
                        if '代碼' in h or '代號' in h:
                            v_code_idx = idx
                        if '量' in h or '合計' in h:
                            v_val_idx = idx
                    
                    if v_code_idx == -1: v_code_idx = 0
                    if v_val_idx == -1: v_val_idx = -1
                    
                    # 累加用量
                    for row in v_reader:
                        if not row or len(row) <= max(v_code_idx, v_val_idx): continue
                        v_code = row[v_code_idx].strip()
                        if not v_code: continue
                        
                        try:
                            # 移除數值中的逗號並轉換為 float
                            v_val = float(row[v_val_idx].replace(',', '').strip())
                        except ValueError:
                            v_val = 0.0
                            
                        if v_code not in volume_map:
                            volume_map[v_code] = {}
                        volume_map[v_code][year] = volume_map[v_code].get(year, 0.0) + v_val

                # --- 3. 解析價格 TXT (純文字 FWF 解析) ---
                price_map = {}
                for p_file in price_files:
                    p_text = p_file.getvalue().decode('utf-8', errors='ignore')
                    for line in p_text.splitlines():
                        if not line.strip(): continue
                        parts = [p.strip() for p in re.split(r'\s{3,}', line) if p.strip()]
                        if len(parts) < 8: continue
                        try:
                            code_part = parts[0].split()
                            price_part = parts[1].split()
                            if len(code_part) > 1 and len(price_part) > 0:
                                code = code_part[1].strip()
                                price = float(price_part[0].strip())
                                price_map[code] = price
                        except:
                            continue

                # --- 4. 終極大融合 (Merge & Generate CSV) ---
                sorted_years = sorted(list(years_found))
                # 新增欄位標題
                output_headers = master_headers + [f"{y}醫令用量" for y in sorted_years] + ["最新健保單價"]
                
                output_rows = []
                for code, row_data in master_data.items():
                    # 補足用量
                    vol_v_list = []
                    for y in sorted_years:
                        vol_v_list.append(str(volume_map.get(code, {}).get(y, 0.0)))
                    # 補足價格
                    price_v = str(price_map.get(code, 0.0))
                    
                    output_rows.append(row_data + vol_v_list + [price_v])

                # 將結果寫入記憶體中的 CSV
                output_stream = io.StringIO()
                writer = csv.writer(output_stream)
                writer.writerow(output_headers)
                writer.writerows(output_rows)
                
                csv_bytes = output_stream.getvalue().encode('utf-8-sig')

                st.success("🎉 太棒了！大數據合併已成功完成！")
                st.download_button(
                    label="📥 下載健保大數據 Master 總表 (CSV 格式)",
                    data=csv_bytes,
                    file_name="健保藥物大數據_Master總表.csv",
                    mime="text/csv"
                )
            except Exception as e:
                st.error(f"系統在融合過程中發生未知錯誤：{str(e)}")
