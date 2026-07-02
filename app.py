import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import date

st.set_page_config(page_title="牛の分娩後日数管理", layout="wide")

SHEET_NAME = "cows"

# =========================
# Google Sheets 接続
# =========================
@st.cache_resource
def connect_gsheet():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]

    credentials = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=scopes,
    )

    gc = gspread.authorize(credentials)
    sh = gc.open_by_key(st.secrets["SPREADSHEET_ID"])
    worksheet = sh.worksheet(SHEET_NAME)
    return worksheet


def load_cows():
    worksheet = connect_gsheet()
    records = worksheet.get_all_records()

    if len(records) == 0:
        return pd.DataFrame(columns=["個体番号", "群", "分娩日", "メモ"])

    df = pd.DataFrame(records)

    for col in ["個体番号", "群", "分娩日", "メモ"]:
        if col not in df.columns:
            df[col] = ""

    return df[["個体番号", "群", "分娩日", "メモ"]]


def save_cows(df):
    worksheet = connect_gsheet()
    worksheet.clear()

    values = [df.columns.tolist()] + df.astype(str).values.tolist()
    worksheet.update(values)


# =========================
# 分娩後日数・状態判定
# =========================
def judge_status(days):
    if pd.isna(days):
        return "日付未入力"
    if days < 0:
        return "分娩日前"
    elif days <= 7:
        return "分娩直後・要注意"
    elif days <= 21:
        return "産後観察"
    elif days <= 60:
        return "繁殖準備・回復期"
    else:
        return "通常管理"


def add_calculated_columns(df):
    today = date.today()
    df = df.copy()

    df["分娩日"] = pd.to_datetime(df["分娩日"], errors="coerce").dt.date
    df["分娩後日数"] = df["分娩日"].apply(
        lambda x: (today - x).days if pd.notna(x) else None
    )
    df["状態"] = df["分娩後日数"].apply(judge_status)

    return df


def color_by_days(row):
    days = row["分娩後日数"]

    if pd.isna(days):
        color = "background-color: #ffffff"
    elif days < 0:
        color = "background-color: #d9d9d9"
    elif days <= 7:
        color = "background-color: #ff9999"
    elif days <= 21:
        color = "background-color: #ffd699"
    elif days <= 60:
        color = "background-color: #ffff99"
    else:
        color = "background-color: #b6f2b6"

    return [color] * len(row)


# =========================
# 画面
# =========================
st.title("牛の分娩後日数管理アプリ")

st.info("分娩日を保存し、分娩後日数は今日の日付から自動計算します。")

# 読み込み
try:
    cows_df = load_cows()
except Exception as e:
    st.error("Googleスプレッドシートの読み込みに失敗しました。")
    st.exception(e)
    st.stop()


# =========================
# 新規登録
# =========================
st.header("牛の新規登録")

with st.form("add_cow_form"):
    col1, col2, col3 = st.columns(3)

    with col1:
        cow_id = st.text_input("個体番号")

    with col2:
        group = st.text_input("群", value="1群")

    with col3:
        calving_date = st.date_input("分娩日", value=date.today())

    memo = st.text_input("メモ")

    submitted = st.form_submit_button("登録して保存")

    if submitted:
        if cow_id.strip() == "":
            st.error("個体番号を入力してください。")
        elif cow_id in cows_df["個体番号"].astype(str).tolist():
            st.error("この個体番号はすでに登録されています。")
        else:
            new_row = pd.DataFrame(
                [
                    {
                        "個体番号": cow_id,
                        "群": group,
                        "分娩日": str(calving_date),
                        "メモ": memo,
                    }
                ]
            )

            updated_df = pd.concat([cows_df, new_row], ignore_index=True)

            try:
                save_cows(updated_df)
                st.success(f"{cow_id} を保存しました。")
                st.rerun()
            except Exception as e:
                st.error("保存に失敗しました。")
                st.exception(e)

st.divider()


# =========================
# 一覧表示
# =========================
st.header("全頭一覧")

calc_df = add_calculated_columns(cows_df)

if len(calc_df) == 0:
    st.warning("まだ牛が登録されていません。")
else:
    groups = ["全群"] + sorted(calc_df["群"].dropna().astype(str).unique().tolist())
    selected_group = st.selectbox("表示する群", groups)

    if selected_group != "全群":
        display_df = calc_df[calc_df["群"].astype(str) == selected_group].copy()
    else:
        display_df = calc_df.copy()

    display_df = display_df.sort_values("分娩後日数", ascending=True)

    st.dataframe(
        display_df.style.apply(color_by_days, axis=1),
        use_container_width=True,
        hide_index=True,
    )

    st.subheader("状態ごとの頭数")
    count_df = display_df["状態"].value_counts().reset_index()
    count_df.columns = ["状態", "頭数"]
    st.dataframe(count_df, use_container_width=True, hide_index=True)


# =========================
# 削除機能
# =========================
st.divider()
st.header("登録削除")

if len(cows_df) > 0:
    delete_id = st.selectbox("削除する個体番号", cows_df["個体番号"].astype(str).tolist())

    if st.button("この牛を削除する"):
        updated_df = cows_df[cows_df["個体番号"].astype(str) != str(delete_id)].copy()

        try:
            save_cows(updated_df)
            st.success(f"{delete_id} を削除しました。")
            st.rerun()
        except Exception as e:
            st.error("削除に失敗しました。")
            st.exception(e)
else:
    st.info("削除できる牛がいません。")