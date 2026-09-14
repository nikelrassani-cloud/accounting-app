import streamlit as st
import sqlite3
import pandas as pd
from datetime import date

st.set_page_config(page_title="MiniBooks", page_icon="📊", layout="wide")

con = sqlite3.connect("minibooks.db", check_same_thread=False)
con.execute("""CREATE TABLE IF NOT EXISTS accounts(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    type TEXT NOT NULL CHECK(type IN
    ('ASSET','LIABILITY','EQUITY','INCOME','EXPENSE')))""")
con.execute("""CREATE TABLE IF NOT EXISTS journal(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_date TEXT NOT NULL,
    description TEXT,
    account_code TEXT NOT NULL,
    debit REAL NOT NULL DEFAULT 0,
    credit REAL NOT NULL DEFAULT 0)""")
con.commit()

DEFAULT_ACCOUNTS = [
    ("1000", "Cash", "ASSET"),
    ("1010", "Bank", "ASSET"),
    ("1200", "Accounts Receivable", "ASSET"),
    ("1300", "Inventory", "ASSET"),
    ("2000", "Accounts Payable", "LIABILITY"),
    ("2100", "Tax Payable", "LIABILITY"),
    ("3000", "Owner's Capital", "EQUITY"),
    ("4000", "Sales Revenue", "INCOME"),
    ("5000", "Cost of Goods Sold", "EXPENSE"),
    ("6000", "Rent Expense", "EXPENSE"),
    ("6100", "Salaries Expense", "EXPENSE"),
]
if con.execute("SELECT COUNT(*) FROM accounts").fetchone()[0] == 0:
    con.executemany("INSERT INTO accounts(code,name,type) VALUES(?,?,?)", DEFAULT_ACCOUNTS)
    con.commit()

acc_df = pd.read_sql("SELECT code, name FROM accounts ORDER BY code", con)
acc_options = [f"{r.code}  {r.name}" for _, r in acc_df.iterrows()]

page = st.sidebar.radio("Menu", ["Dashboard", "New Entry", "Trial Balance", "Chart of Accounts"])

if page == "Dashboard":
    st.title("📊 MiniBooks — Accounting Dashboard")
    cash = con.execute("SELECT SUM(debit)-SUM(credit) FROM journal WHERE account_code='1000'").fetchone()[0] or 0
    bank = con.execute("SELECT SUM(debit)-SUM(credit) FROM journal WHERE account_code='1010'").fetchone()[0] or 0
    sales = con.execute("SELECT SUM(credit)-SUM(debit) FROM journal WHERE account_code='4000'").fetchone()[0] or 0
    n = con.execute("SELECT COUNT(*) FROM journal").fetchone()[0]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("💵 Cash", f"{cash:,.2f}")
    c2.metric("🏦 Bank", f"{bank:,.2f}")
    c3.metric("💰 Total Sales", f"{sales:,.2f}")
    c4.metric("🧾 Entries Posted", n)

elif page == "New Entry":
    st.title("➕ New Journal Entry")
    with st.form("entry"):
        c1, c2 = st.columns(2)
        entry_date = c1.date_input("Date", date.today())
        desc = c2.text_input("Description")
        st.subheader("Debit line")
        d_acc = st.selectbox("Debit account", acc_options)
        d_amt = st.number_input("Debit amount", min_value=0.0, step=0.01)
        st.subheader("Credit line")
        c_acc = st.selectbox("Credit account", acc_options)
        c_amt = st.number_input("Credit amount", min_value=0.0, step=0.01)
        if st.form_submit_button("Post Entry"):
            if d_amt <= 0 or abs(d_amt - c_amt) > 0.001:
                st.error("❌ Debit aur Credit barabar hone chahiye!")
            else:
                con.execute("INSERT INTO journal(entry_date,description,account_code,debit,credit) VALUES(?,?,?,?,?)",
                            (str(entry_date), desc, d_acc.split(" ")[0], d_amt, 0))
                con.execute("INSERT INTO journal(entry_date,description,account_code,debit,credit) VALUES(?,?,?,?,?)",
                            (str(entry_date), desc, c_acc.split(" ")[0], 0, c_amt))
                con.commit()
                st.success("✅ Entry post ho gayi!")

elif page == "Trial Balance":
    st.title("⚖️ Trial Balance")
    df = pd.read_sql("""SELECT j.account_code AS Code, a.name AS Account, a.type AS Type,
                        SUM(j.debit) AS Debit, SUM(j.credit) AS Credit
                        FROM journal j JOIN accounts a ON a.code=j.account_code
                        GROUP BY j.account_code, a.name, a.type ORDER BY j.account_code""", con)
    if df.empty:
        st.info("Abhi koi entry nahi — pehle New Entry banayein!")
    else:
        df["Balance"] = df.Debit - df.Credit
        totals = pd.DataFrame([{"Code":"","Account":"TOTAL","Type":"",
                                "Debit":df.Debit.sum(),"Credit":df.Credit.sum(),
                                "Balance":df.Balance.sum()}])
        st.dataframe(pd.concat([df, totals], ignore_index=True), use_container_width=True)
        if abs(df.Debit.sum() - df.Credit.sum()) < 0.01:
            st.success(f"✅ Balanced! {df.Debit.sum():,.2f}")
        else:
            st.error("❌ Balance nahi hai")

elif page == "Chart of Accounts":
    st.title("📒 Chart of Accounts")
    st.dataframe(acc_df.rename(columns={"code":"Code","name":"Account"}), use_container_width=True)
    with st.form("add_acc"):
        st.subheader("Naya account add karein")
        c1, c2, c3 = st.columns(3)
        code = c1.text_input("Code (maslan 6200)")
        name = c2.text_input("Account ka naam")
        typ = c3.selectbox("Type", ["ASSET","LIABILITY","EQUITY","INCOME","EXPENSE"])
        if st.form_submit_button("Add"):
            try:
                con.execute("INSERT INTO accounts(code,name,type) VALUES(?,?,?)", (code, name, typ))
                con.commit()
                st.success(f"{code} {name} add ho gaya")
                st.rerun()
            except Exception as e:
                st.error(f"Add nahi hua: {e}")
