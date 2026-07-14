import streamlit as st
import pandas as pd
import io
import re

# 網頁版面設定
st.set_page_config(page_title="💊 健保大數據自動整併中心", layout="wide")
st.title("💊 健保藥品大數據：用量、價格與主檔自動整併系統")
st.markdown("這是一個能永續使用的自動化工具。只需上傳最新檔案，系統會自動幫您合併成一張 **Master Excel 總表**！")
st.markdown("---")

# 檔案上傳區塊
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

# 簡易整併按鈕
if st.button("🚀 開始一鍵無腦融合", type="primary"):
    if not master_file or not volume_files or not price_files:
        st.error("⚠️ 請確保三大類的檔案皆已上傳！")
    else:
        with st.spinner('⚙️ 系統正在處理中...'):
            try:
                # 1. 讀取主檔 (Master)
                df_master = pd.read_csv(master_file)
                df_master = df_master.rename(columns={df_master.columns[0]: '健保藥品代碼'})
                
                # 2. 處理用量檔 (Volumes)
                df_vols_list = []
                for v_file in volume_files:
                    df_v = pd.read_csv(v_file)
                    year = "111年" if "111" in v_file.name else ("112年" if "112" in v_file.name else "113年")
                    # 尋找代碼與用量欄位
                    code_col = [c for c in df_v.columns if '代碼' in c or '代號' in c][0]
                    vol_col = [c for c in df_v.columns if '量' in c or '合計' in c][0]
                    
                    df_v_grouped = df_v.groupby(code_col)[vol_col].sum().reset_index()
                    df_v_grouped.columns = ['健保藥品代碼', f'{year}醫令用量']
                    df_vols_list.append(df_v_grouped)
                
                df_volume_merged = df_vols_list[0]
                for i in range(1, len(df_vols_list)):
                    df_volume_merged = pd.merge(df_volume_merged, df_vols_list[i], on='健保藥品代碼', how='outer')
                
                # 3. 解析價格
                price_results = []
                for p_file in price_files:
                    text_stream = io.StringIO(p_file.getvalue().decode('utf-8', errors='ignore'))
                    for line in text_stream:
                        if not line.strip(): continue
                        parts = [p.strip() for p in re.split(r'\s{3,}', line) if p.strip()]
                        if len(parts) < 8: continue
                        try:
                            code = parts[0].split()[1] if len(parts[0].split()) > 1 else ""
                            price = parts[1].split()[0] if len(parts[1].split()) > 0 else "0"
                            price_results.append({'健保藥品代碼': code, '最新健保單價': float(price)})
                        except:
                            continue
                
                df_price = pd.DataFrame(price_results).drop_duplicates(subset=['健保藥品代碼'], keep='last')
                
                # 4. 合併
                final_master = pd.merge(df_master, df_volume_merged, on='健保藥品代碼', how='left')
                final_master = pd.merge(final_master, df_price, on='健保藥品代碼', how='left').fillna(0)
                
                # 5. 直接轉為 CSV 輸出 (完全不依賴 Excel 寫入引擎，零崩潰率！)
                csv_data = final_master.to_csv(index=False).encode('utf-8-sig')
                
                st.success("🎉 合併成功！")
                st.download_button(
                    label="📥 下載健保大數據 Master 總表 (CSV 格式)",
                    data=csv_data,
                    file_name="健保藥物大數據_Master總表.csv",
                    mime="text/csv"
                )
            except Exception as e:
                st.error(f"發生錯誤：{str(e)}")
