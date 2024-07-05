import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta

# Streamlit SecretsからJSON情報を取得
credentials = {
    "type": st.secrets["gcp_service_account"]["type"],
    "project_id": st.secrets["gcp_service_account"]["project_id"],
    "private_key_id": st.secrets["gcp_service_account"]["private_key_id"],
    "private_key": st.secrets["gcp_service_account"]["private_key"],
    "client_email": st.secrets["gcp_service_account"]["client_email"],
    "client_id": st.secrets["gcp_service_account"]["client_id"],
    "auth_uri": st.secrets["gcp_service_account"]["auth_uri"],
    "token_uri": st.secrets["gcp_service_account"]["token_uri"],
    "auth_provider_x509_cert_url": st.secrets["gcp_service_account"]["auth_provider_x509_cert_url"],
    "client_x509_cert_url": st.secrets["gcp_service_account"]["client_x509_cert_url"]
}

# 認証設定
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/spreadsheets",
         "https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(credentials, scope)
client = gspread.authorize(creds)
sheet1 = client.open("bates").sheet1
sheet3 = client.open("bates").get_worksheet(2)  # シート3を取得

# キャッシュの設定
CACHE_DURATION = timedelta(minutes=15)  # キャッシュの有効期限を15分に延長
cache = {
    'sheet1_data': None,
    'sheet1_timestamp': None,
    'sheet3_data': None,
    'sheet3_timestamp': None
}

# キャッシュからシート1のデータを取得
def get_data_from_sheet1():
    now = datetime.now()
    if cache['sheet1_data'] is None or now - cache['sheet1_timestamp'] > CACHE_DURATION:
        try:
            data = sheet1.get_all_records()
            cache['sheet1_data'] = pd.DataFrame(data)
            cache['sheet1_timestamp'] = now
        except gspread.exceptions.APIError as e:
            st.error(f"Google Sheets API error: {e}")
            return None
    return cache['sheet1_data']

# キャッシュからシート3のデータを取得
def get_data_from_sheet3():
    now = datetime.now()
    if cache['sheet3_data'] is None or now - cache['sheet3_timestamp'] > CACHE_DURATION:
        try:
            data = sheet3.get_all_records()
            cache['sheet3_data'] = pd.DataFrame(data)
            cache['sheet3_timestamp'] = now
        except gspread.exceptions.APIError as e:
            st.error(f"Google Sheets API error: {e}")
            return None
    return cache['sheet3_data']

# データをシート1に保存
def save_data_to_sheet1(data):
    data = data.fillna('')  # NaN値を空文字列に置き換える
    try:
        sheet1.clear()
        sheet1.append_rows([data.columns.values.tolist()] + data.values.tolist())
        # キャッシュを更新
        cache['sheet1_data'] = data
        cache['sheet1_timestamp'] = datetime.now()
    except gspread.exceptions.APIError as e:
        st.error(f"Google Sheets API error: {e}")

# Streamlitアプリの構成
def main():
    st.title("ROK10周年　出席確認システム")
    
    st.subheader("sまたはspから始まる社員番号で入力してください")
    name_or_number = st.text_input("社員番号")
    
    check_d_column = st.checkbox("社員番号がわからない方はこちらをチェックしフルネーム[例:日置太郎]とスペースを入れずに入力をお願いします。")

    if st.button("登録"):
        data_sheet1 = get_data_from_sheet1()
        data_sheet3 = get_data_from_sheet3()

        if data_sheet1 is None or data_sheet3 is None:
            st.error("データの取得に失敗しました。後でもう一度お試しください。")
            return

        # シート1で重複確認
        if '名前' in data_sheet1.columns:
            if name_or_number in data_sheet1['名前'].values:
                st.warning(f"{name_or_number}さんは既に登録されています。")
                return
            elif 'no' in data_sheet3.columns and name_or_number in data_sheet3['no'].values:
                person_name = data_sheet3.loc[data_sheet3['no'] == name_or_number, '名前'].values[0]
                if person_name in data_sheet1['名前'].values:
                    st.warning(f"{person_name}さんは既に登録されています。")
                    return

        if check_d_column:
            # 名前で確認
            if '名前' in data_sheet3.columns and name_or_number in data_sheet3['名前'].values:
                row = data_sheet3[data_sheet3['名前'] == name_or_number].iloc[0]
                if '座席' not in row:
                    st.error("シートに '座席' 列が存在しません。")
                    return
                seat_number = row['座席']
                st.markdown(
                    f'<p style="font-size:42px;">{name_or_number}さんの席番号は{seat_number}番テーブルです。</p>',
                    unsafe_allow_html=True
                )
                new_entry = pd.DataFrame({"名前": [name_or_number], "座席": [seat_number]})
                data_sheet1 = pd.concat([data_sheet1, new_entry], ignore_index=True)
                save_data_to_sheet1(data_sheet1)
            else:
                st.warning("名前が見つかりません。")
        else:
            # 社員番号で確認
            if 'no' in data_sheet3.columns and name_or_number in data_sheet3['no'].values:
                row = data_sheet3[data_sheet3['no'] == name_or_number].iloc[0]
                if '座席' not in row:
                    st.error("シートに '座席' 列が存在しません。")
                    return
                person_name = row['名前']
                seat_number = row['座席']
                st.markdown(
                    f'<p style="font-size:42px;">{person_name}さんの席番号は{seat_number}番テーブルです。</p>',
                    unsafe_allow_html=True
                )
                new_entry = pd.DataFrame({"名前": [person_name], "座席": [seat_number]})
                data_sheet1 = pd.concat([data_sheet1, new_entry], ignore_index=True)
                save_data_to_sheet1(data_sheet1)
            else:
                st.warning("番号が見つかりません。")

if __name__ == "__main__":
    main()
