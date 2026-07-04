import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import date
from html import escape

st.set_page_config(page_title="牛の分娩後日数管理", layout="wide")

SHEET_NAME = "cows"

# =========================
# 表示調整CSS
# =========================
st.markdown(
    """
<style>
.cow-grid {
    display: grid;
    grid-template-columns: 0.9fr 0.7fr 1.2fr 0.9fr 1.1fr 0.8fr 1.2fr;
    gap: 0px;
    margin-bottom: 4px;
}

.cow-cell {
    padding: 8px 4px;
    border: 1px solid #dddddd;
    min-height: 38px;
    text-align: center;
    font-size: 14px;
    box-sizing: border-box;
    word-break: break-word;
    display: flex;
    align-items: center;
    justify-content: center;
}

.cow-header {
    background-color: #eeeeee;
    font-weight: bold;
}

div[data-testid="stButton"] > button {
    height: 38px;
    padding: 4px 10px;
    margin-top: 0px;
}
</style>
""",
    unsafe_allow_html=True,
)


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
# 分娩後日数・色分け判定
# =========================
def judge_color_group(days):
    if pd.isna(days):
        return "日付未入力"

    if days < 0:
        return "分娩日前"
    elif days <= 13:
        return "ピンク"
    elif days <= 20:
        return "緑"
    elif days <= 27:
        return "黄"
    elif days <= 119:
        return "赤"
    elif days <= 179:
        return "黄"
    elif days <= 209:
        return "緑"
    else:
        return "ピンク"


def judge_management_value(days):
    if pd.isna(days):
        return ""

    if days < 0:
        return ""
    elif days <= 13:
        return "0.5"
    elif days <= 20:
        return "1.5"
    elif days <= 27:
        return "2.5"
    elif days <= 119:
        return "3.5"
    elif days <= 179:
        return "3.5〜2.5"
    elif days <= 209:
        return "2.5〜1.5"
    else:
        return "0.5"


def judge_day_range(days):
    if pd.isna(days):
        return "日付未入力"

    if days < 0:
        return "分娩日前"
    elif days <= 13:
        return "0〜13日"
    elif days <= 20:
        return "14〜20日"
    elif days <= 27:
        return "21〜27日"
    elif days <= 119:
        return "28〜119日"
    elif days <= 179:
        return "120〜179日"
    elif days <= 209:
        return "180〜209日"
    else:
        return "210日〜"


def add_calculated_columns(df):
    today = date.today()
    df = df.copy()

    df["分娩日"] = pd.to_datetime(df["分娩日"], errors="coerce").dt.date

    df["分娩後日数"] = df["分娩日"].apply(
        lambda x: (today - x).days if pd.notna(x) else None
    )

    df["日数区分"] = df["分娩後日数"].apply(judge_day_range)
    df["色区分"] = df["分娩後日数"].apply(judge_color_group)
    df["管理値"] = df["分娩後日数"].apply(judge_management_value)

    return df


def get_background_color(color_group):
    if color_group == "ピンク":
        return "#ffc0cb"
    elif color_group == "緑":
        return "#b6f2b6"
    elif color_group == "黄":
        return "#ffff99"
    elif color_group == "赤":
        return "#ff9999"
    elif color_group == "分娩日前":
        return "#d9d9d9"
    else:
        return "#ffffff"


def make_cell(value, bg_color, header=False, bold=False):
    safe_value = escape(str(value))
    classes = "cow-cell cow-header" if header else "cow-cell"
    font_weight = "bold" if bold else "normal"

    return (
        f'<div class="{classes}" '
        f'style="background-color:{bg_color}; font-weight:{font_weight};">'
        f'{safe_value}'
        f'</div>'
    )


def render_table_header():
    headers = [
        "個体番号",
        "群",
        "分娩日",
        "分娩後日数",
        "日数区分",
        "管理値",
        "メモ",
    ]

    cells = "".join(
        make_cell(header, "#eeeeee", header=True, bold=True)
        for header in headers
    )

    return f'<div class="cow-grid">{cells}</div>'


def render_table_row(row, bg_color):
    values = [
        row["個体番号"],
        row["群"],
        row["分娩日"],
        row["分娩後日数"],
        row["日数区分"],
        row["管理値"],
        row["メモ"],
    ]

    cells = "".join(
        make_cell(value, bg_color, bold=(i in [0, 5]))
        for i, value in enumerate(values)
    )

    return f'<div class="cow-grid">{cells}</div>'


def reset_calving_date(cows_df, cow_id):
    updated_df = cows_df.copy()

    updated_df.loc[
        updated_df["個体番号"].astype(str) == str(cow_id),
        "分娩日"
    ] = str(date.today())

    save_cows(updated_df)


# =========================
# 画面
# =========================
st.title("牛の分娩後日数管理アプリ")

st.info("分娩日を保存し、分娩後日数は今日の日付から自動計算します。")

st.markdown(
    """
### 色分けルール

| 分娩後日数 | 色 | 管理値 |
|---:|---|---|
| 0〜13日 | ピンク | 0.5 |
| 14〜20日 | 緑 | 1.5 |
| 21〜27日 | 黄 | 2.5 |
| 28〜119日 | 赤 | 3.5 |
| 120〜179日 | 黄 | 3.5〜2.5 |
| 180〜209日 | 緑 | 2.5〜1.5 |
| 210日〜 | ピンク | 0.5 |
"""
)

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
    # 群の絞り込み
    groups = ["全群"] + sorted(calc_df["群"].dropna().astype(str).unique().tolist())
    selected_group = st.selectbox("表示する群", groups)

    if selected_group != "全群":
        display_df = calc_df[calc_df["群"].astype(str) == selected_group].copy()
    else:
        display_df = calc_df.copy()

    # 個体番号検索
    search_id = st.text_input(
        "個体番号で検索",
        placeholder="例：8353",
        key="cow_id_search",
    )

    if search_id.strip() != "":
        display_df = display_df[
            display_df["個体番号"]
            .astype(str)
            .str.contains(search_id.strip(), case=False, na=False)
        ].copy()

    display_df = display_df.sort_values("分娩後日数", ascending=True)

    st.write(f"表示頭数：{len(display_df)}頭")

    if len(display_df) == 0:
        st.warning("該当する個体番号がありません。")
    else:
        # ヘッダー
        header_left, header_right = st.columns([8.2, 1.0], gap="large")

        with header_left:
            st.markdown(render_table_header(), unsafe_allow_html=True)

        with header_right:
            st.markdown(
                '<div class="cow-cell cow-header">リセット</div>',
                unsafe_allow_html=True,
            )

        # データ行
        for _, row in display_df.iterrows():
            bg_color = get_background_color(row["色区分"])

            row_left, row_right = st.columns([8.2, 1.0], gap="large")

            with row_left:
                st.markdown(
                    render_table_row(row, bg_color),
                    unsafe_allow_html=True,
                )

            with row_right:
                if st.button(
                    "0日",
                    key=f"reset_{row['個体番号']}",
                    help=f"{row['個体番号']} の分娩日を今日に更新します",
                ):
                    try:
                        reset_calving_date(cows_df, row["個体番号"])
                        st.success(f"{row['個体番号']} の分娩後日数を0日にリセットしました。")
                        st.rerun()
                    except Exception as e:
                        st.error("リセットに失敗しました。")
                        st.exception(e)

        st.subheader("管理値ごとの頭数")
        value_count_df = display_df["管理値"].value_counts().reset_index()
        value_count_df.columns = ["管理値", "頭数"]
        st.dataframe(value_count_df, use_container_width=True, hide_index=True)


# =========================
# 削除機能
# =========================
st.divider()
st.header("登録削除")

if len(cows_df) > 0:
    delete_id = st.selectbox(
        "削除する個体番号",
        cows_df["個体番号"].astype(str).tolist(),
        key="delete_id_selectbox",
    )

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