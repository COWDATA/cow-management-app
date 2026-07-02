import streamlit as st
import pandas as pd
from datetime import date, timedelta

st.set_page_config(page_title="牛の分娩・給餌管理", layout="wide")

st.title("牛の分娩・給餌管理アプリ")

st.header("分娩管理")

cow_id = st.text_input("個体番号", "A001")
breeding_date = st.date_input("種付け日", date.today())

calving_date = breeding_date + timedelta(days=280)
today = date.today()

pregnancy_days = (today - breeding_date).days
days_until_calving = (calving_date - today).days

st.subheader("計算結果")

col1, col2, col3 = st.columns(3)

col1.metric("分娩予定日", str(calving_date))
col2.metric("妊娠日数", f"{pregnancy_days}日")
col3.metric("分娩まで", f"{days_until_calving}日")

if days_until_calving <= 0:
    st.error("分娩予定日を過ぎています。確認してください。")
elif days_until_calving <= 7:
    st.warning("分娩予定日が近いです。要観察です。")
elif days_until_calving <= 30:
    st.info("分娩準備期間です。")
else:
    st.success("通常管理です。")

st.divider()

st.header("給餌管理")

feed_amount = st.number_input("給餌量 kg", min_value=0.0, value=8.0, step=0.5)
leftover_amount = st.number_input("残餌量 kg", min_value=0.0, value=1.0, step=0.5)

intake_amount = feed_amount - leftover_amount

st.metric("摂取量", f"{intake_amount:.1f} kg")

if feed_amount > 0:
    intake_rate = intake_amount / feed_amount

    if intake_rate < 0.6:
        st.error("摂取量が少ないです。食欲低下の可能性があります。")
    elif intake_rate < 0.8:
        st.warning("やや残餌が多いです。注意してください。")
    else:
        st.success("食欲はおおむね良好です。")