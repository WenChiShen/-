import streamlit as st
import pandas as pd
import io
import re

# ==========================================
# 網頁版面設定
# ==========================================
st.set_page_config(page_title="💊 健保大數據自動整併中心", layout="wide")
st.title("💊 健保藥品大數據：用量、價格與主檔自動整併系統")
st.markdown("這是一個能永續使用的自動化工具。只需上傳最新檔案，系統會自動幫您合併成一張 **Master Excel 總表**！")
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
    volume_files = st.file_uploader("上傳用量 CSV (可多選，如 111, 112, 113)", type=['csv'], accept_multiple_files=True)

with col3:
    st.subheader("💰 3. 最新健保價查詢檔")
    price_files = st.file_uploader("上傳 TXT 原始檔 (可多選，支援 400MB)", type=['txt'], accept_multiple_files=True)

# ==========================================
# 資料處理引擎
# ==========================================
if st.button("🚀 開始一鍵無腦融合", type="primary"):
    if not master_file or not volume_files or not price_files:
        st.error("⚠️ 請確保三大類的檔案皆已上傳！")
    else:
        with st.spinner('⚙️ 系統正在全速運轉處理中（這可能需要 10-30 秒）...'):
            try:
                # 1. 讀取主檔 (Master)
                df_master = pd.read_csv(master_file)
                # 確保欄位名稱乾淨
                df_master = df_master.drop_duplicates(subset=['藥品代號'], keep='first')
                df_master = df_master.rename(columns={'藥品代號': '健保藥品代碼'})
                
                # 2. 處理用量檔 (Volumes)
                df_vols_list = []
                for v_file in volume_files:
                    df_v = pd.read_csv(v_file)
                    # 假設有 '藥品代碼' 和 '含包裹支付的醫令量_合計'，並根據檔名推測年份
                    year = "未知年份"
                    if "111" in v_file.name: year = "111年"
                    elif "112" in v_file.name: year = "112年"
                    elif "113" in v_file.name: year = "113年"
                    
                    df_v_grouped = df_v.groupby('藥品代碼')['含包裹支付的醫令量_合計'].sum().reset_index()
                    df_v_grouped = df_v_grouped.rename(columns={'藥品代碼': '健保藥品代碼', '含包裹支付的醫令量_合計': f'{year}醫令用量'})
                    df_vols_list.append(df_v_grouped)
                
                # 合併所有用量
                df_volume_merged = df_vols_list[0]
                for i in range(1, len(df_vols_list)):
                    df_volume_merged = pd.merge(df_volume_merged, df_vols_list[i], on='健保藥品代碼', how='outer')
                
                # 3. 解析健保價格 TXT (FWF 引擎)
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
                
                df_price = pd.DataFrame(price_results)
                df_price = df_price.drop_duplicates(subset=['健保藥品代碼'], keep='last')
                
                # 4. 終極大融合 (Merge All)
                # 以 Master 主檔為基底，Left Join 用量與價格
                final_master = pd.merge(df_master, df_volume_merged, on='健保藥品代碼', how='left')
                final_master = pd.merge(final_master, df_price, on='健保藥品代碼', how='left')
                
                # 填補空值
                final_master = final_master.fillna(0)
                
                # 5. 輸出成 Excel
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    final_master.to_excel(writer, index=False, sheet_name='Master_Data')
                
                st.success("🎉 太棒了！所有資料已成功融合為一份 Master 總表！")
                
                # 提供下載按鈕
                st.download_button(
                    label="📥 下載健保大數據 Master 總表 (.xlsx)",
                    data=output.getvalue(),
                    file_name="健保藥物大數據_Master總表.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            except Exception as e:
                st.error(f"發生錯誤：{str(e)}")