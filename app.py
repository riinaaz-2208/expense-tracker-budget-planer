import sqlite3
from datetime import date
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(
    page_title="Expense Tracker & Budget Planner",
    page_icon="💰",
    layout="wide"
)

st.title("💰 Expense Tracker & Budget Planner")
st.write("Track your income, expenses and monthly savings.")

# Database connection
conn = sqlite3.connect("expenses.db")

conn.execute("""
CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    amount REAL NOT NULL,
    transaction_type TEXT NOT NULL,
    category TEXT NOT NULL,
    transaction_date TEXT NOT NULL
)
""")

conn.execute("""
CREATE TABLE IF NOT EXISTS budgets (
    month TEXT PRIMARY KEY,
    amount REAL NOT NULL
)
""")

conn.commit()

# Navigation
page = st.sidebar.radio(
    "Navigation",
    [
        "Dashboard",
        "Add Transaction",
        "Transaction History",
        "Budget Planner",
        "Data Analysis"
    ]
)

# Load data
def load_data():
    df = pd.read_sql_query(
        "SELECT * FROM transactions ORDER BY transaction_date DESC",
        conn
    )

    if not df.empty:
        df["transaction_date"] = pd.to_datetime(
            df["transaction_date"]
        )

    return df


df = load_data()

# Dashboard
if page == "Dashboard":

    st.header("Financial Dashboard")

    if df.empty:
        st.info("No transactions yet. Add your first transaction!")

    income = (
        df.loc[df["transaction_type"] == "Income", "amount"].sum()
        if not df.empty else 0
    )

    expenses = (
        df.loc[df["transaction_type"] == "Expense", "amount"].sum()
        if not df.empty else 0
    )

    balance = income - expenses

    col1, col2, col3 = st.columns(3)

    col1.metric("Total Income", f"₹{income:,.2f}")
    col2.metric("Total Expenses", f"₹{expenses:,.2f}")
    col3.metric("Available Balance", f"₹{balance:,.2f}")

    if not df.empty:

        expense_df = df[
            df["transaction_type"] == "Expense"
        ]

        if not expense_df.empty:

            category_data = (
                expense_df.groupby("category")["amount"]
                .sum()
                .reset_index()
            )

            fig = px.pie(
                category_data,
                names="category",
                values="amount",
                title="Expenses by Category",
                hole=0.4
            )

            st.plotly_chart(fig, use_container_width=True)

        st.subheader("Recent Transactions")
        st.dataframe(df, use_container_width=True, hide_index=True)


# Add Transaction
elif page == "Add Transaction":

    st.header("Add New Transaction")

    with st.form("add_transaction"):

        title = st.text_input("Transaction Name")

        amount = st.number_input(
            "Amount (₹)",
            min_value=0.0,
            step=100.0
        )

        transaction_type = st.selectbox(
            "Transaction Type",
            ["Income", "Expense"]
        )

        category = st.selectbox(
            "Category",
            [
                "Salary",
                "Food",
                "Travel",
                "Shopping",
                "Education",
                "Bills",
                "Health",
                "Entertainment",
                "Other"
            ]
        )

        transaction_date = st.date_input(
            "Date",
            value=date.today()
        )

        submitted = st.form_submit_button("Add Transaction")

        if submitted:

            if not title.strip():
                st.error("Please enter a transaction name.")

            elif amount <= 0:
                st.error("Amount must be greater than zero.")

            else:

                conn.execute(
                    """
                    INSERT INTO transactions
                    (title, amount, transaction_type, category,
                     transaction_date)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        title.strip(),
                        amount,
                        transaction_type,
                        category,
                        transaction_date.isoformat()
                    )
                )

                conn.commit()

                st.success("Transaction added successfully!")
                st.rerun()


# Transaction History
elif page == "Transaction History":

    st.header("Transaction History")

    if df.empty:
        st.info("No transactions available.")

    else:

        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True
        )

        selected_id = st.selectbox(
            "Select Transaction ID to Delete",
            df["id"].tolist()
        )

        if st.button("Delete Transaction"):

            conn.execute(
                "DELETE FROM transactions WHERE id = ?",
                (int(selected_id),)
            )

            conn.commit()

            st.success("Transaction deleted.")
            st.rerun()


# Budget Planner
elif page == "Budget Planner":

    st.header("Monthly Budget Planner")

    selected_month = st.text_input(
        "Month (YYYY-MM)",
        value=date.today().strftime("%Y-%m")
    )

    budget = st.number_input(
        "Monthly Budget (₹)",
        min_value=0.0,
        step=500.0
    )

    if st.button("Save Budget"):

        try:

            valid_month = (
                len(selected_month) == 7
                and date.fromisoformat(
                    selected_month + "-01"
                ).strftime("%Y-%m") == selected_month
            )

            if not valid_month:
                st.error("Enter the month as YYYY-MM.")

            elif budget <= 0:
                st.error("Budget must be greater than zero.")

            else:

                conn.execute(
                    """
                    INSERT INTO budgets (month, amount)
                    VALUES (?, ?)
                    ON CONFLICT(month)
                    DO UPDATE SET amount = excluded.amount
                    """,
                    (selected_month, budget)
                )

                conn.commit()

                st.success("Budget saved successfully!")

        except ValueError:
            st.error("Invalid month. Example: 2026-10")

    try:

        valid_month = (
            len(selected_month) == 7
            and date.fromisoformat(
                selected_month + "-01"
            ).strftime("%Y-%m") == selected_month
        )

    except ValueError:
        valid_month = False

    if valid_month:

        result = conn.execute(
            "SELECT amount FROM budgets WHERE month = ?",
            (selected_month,)
        ).fetchone()

        saved_budget = result[0] if result else 0

        month_df = df[
            df["transaction_date"].dt.strftime("%Y-%m")
            == selected_month
        ] if not df.empty else pd.DataFrame()

        spent = (
            month_df.loc[
                month_df["transaction_type"] == "Expense",
                "amount"
            ].sum()
            if not month_df.empty else 0
        )

        remaining = saved_budget - spent

        col1, col2, col3 = st.columns(3)

        col1.metric("Monthly Budget", f"₹{saved_budget:,.2f}")
        col2.metric("Total Spent", f"₹{spent:,.2f}")
        col3.metric("Remaining Budget", f"₹{remaining:,.2f}")

        if saved_budget > 0:

            st.progress(min(spent / saved_budget, 1.0))

            if spent > saved_budget:
                st.error("Your expenses have exceeded the budget!")

            else:
                st.success("You are within your budget.")


# Data Analysis
elif page == "Data Analysis":

    st.header("Financial Data Analysis")

    if df.empty:

        st.info("Add transactions to see data analysis.")

    else:

        expense_df = df[
            df["transaction_type"] == "Expense"
        ].copy()

        if not expense_df.empty:

            st.subheader("Category-wise Expense Analysis")

            category_analysis = (
                expense_df.groupby("category")["amount"]
                .agg(["sum", "mean", "count"])
                .reset_index()
            )

            category_analysis.columns = [
                "Category",
                "Total Expense",
                "Average Expense",
                "Transaction Count"
            ]

            category_analysis = category_analysis.sort_values(
                "Total Expense",
                ascending=False
            )

            st.dataframe(
                category_analysis.round(2),
                use_container_width=True,
                hide_index=True
            )

            fig = px.bar(
                category_analysis,
                x="Category",
                y="Total Expense",
                title="Category-wise Spending"
            )

            st.plotly_chart(fig, use_container_width=True)

            top_category = category_analysis.iloc[0]

            st.info(
                f"Highest spending category: "
                f"{top_category['Category']} "
                f"(₹{top_category['Total Expense']:,.2f})"
            )

        else:
            st.info("No expense records available.")

        st.subheader("Monthly Income and Expense Analysis")

        df["month"] = df["transaction_date"].dt.strftime("%Y-%m")

        monthly = (
            df.groupby(["month", "transaction_type"])["amount"]
            .sum()
            .reset_index()
        )

        fig_monthly = px.bar(
            monthly,
            x="month",
            y="amount",
            color="transaction_type",
            barmode="group",
            title="Monthly Income vs Expenses"
        )

        st.plotly_chart(
            fig_monthly,
            use_container_width=True
        )

        st.subheader("Download Data")

        st.download_button(
            "Download Transactions as CSV",
            df.to_csv(index=False).encode("utf-8"),
            file_name="expense_analysis.csv",
            mime="text/csv"
        )


conn.close()