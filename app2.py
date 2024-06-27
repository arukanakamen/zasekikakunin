import streamlit as st
import pandas as pd
import random
import gspread
from oauth2client.service_account import ServiceAccountCredentials

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
sheet = client.open("bates").sheet1

# スプレッドシートからデータを取得
def get_data():
    data = sheet.get_all_records()
    return pd.DataFrame(data)

# データをスプレッドシートに保存
def save_data(data):
    sheet.clear()
    sheet.append_rows([data.columns.values.tolist()] + data.values.tolist())

# 座席のリスト
seats = list(range(1, 22))
excluded_seats = [1, 2, 4]
available_seats = [seat for seat in seats if seat not in excluded_seats]

# Streamlitアプリの構成
def main():
    st.title("ROK10周年　出席確認システム")
    
    st.subheader("フルネームで入力をお願いします")
    name = st.text_input("名前")
    
    if st.button("登録"):
        if name:
            data = get_data()
            if '名前' in data.columns and name in data['名前'].values:
                st.warning("入力済みです。")
            else:
                if len(data) >= 133:
                    st.write("入力は完了しました。")
                else:
                    chosen_seat = random.choice(available_seats)
                    if '座席' in data.columns:
                        seat_count = data['座席'].value_counts()
                        while seat_count.get(chosen_seat, 0) >= 7:
                            chosen_seat = random.choice(available_seats)
                    else:
                        seat_count = pd.Series([0] * len(available_seats), index=available_seats)

                    new_entry = pd.DataFrame({"名前": [name], "座席": [chosen_seat]})
                    data = pd.concat([data, new_entry], ignore_index=True)
                    save_data(data)
                    st.markdown(
                        f'<p style="font-size:42px;">{name}さんの座席は{chosen_seat}番テーブルです。</p>',
                        unsafe_allow_html=True
                    )

if __name__ == "__main__":
    main()
