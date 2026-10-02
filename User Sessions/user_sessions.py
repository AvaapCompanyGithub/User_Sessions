# Login & Query History Dashboard
# Co-authored with CoCo
import streamlit as st
from datetime import date, timedelta
from snowflake.snowpark.context import get_active_session

st.set_page_config(page_title="Login & Query History", layout="wide")
st.title("Login & Query History Dashboard")

session = get_active_session()

# Date range filter inline
default_start = date.today() - timedelta(days=date.today().weekday())
default_end = date.today()
date_range = st.date_input(
    "Date range",
    value=(default_start, default_end),
    max_value=date.today(),
)

if len(date_range) == 2:
    start_date, end_date = date_range
else:
    st.warning("Please select a start and end date.")
    st.stop()


@st.cache_data(ttl=600)
def load_login_history(_start, _end):
    return session.sql(
        """
        SELECT
            USER_NAME,
            SUM(CASE WHEN IS_SUCCESS = 'YES' THEN 1 ELSE 0 END) AS SUCCESS_LOGINS,
            SUM(CASE WHEN IS_SUCCESS = 'NO' THEN 1 ELSE 0 END) AS FAILED_LOGINS,
            FIRST_AUTHENTICATION_FACTOR AS AUTH_TYPE,
            MAX(EVENT_TIMESTAMP)::TIMESTAMP_NTZ AS LAST_EVENT
        FROM SNOWFLAKE.ACCOUNT_USAGE.LOGIN_HISTORY
        WHERE EVENT_TIMESTAMP >= ? AND EVENT_TIMESTAMP < DATEADD(day, 1, TO_DATE(?))
        GROUP BY USER_NAME, FIRST_AUTHENTICATION_FACTOR
        ORDER BY SUCCESS_LOGINS DESC
        """,
        params=[str(_start), str(_end)],
    ).to_pandas()


@st.cache_data(ttl=600)
def load_query_history(_start, _end):
    return session.sql(
        """
        SELECT
            USER_NAME,
            COUNT(*) AS NUM_QUERIES,
            SUM(TOTAL_ELAPSED_TIME) / 1000 AS TOTAL_DURATION_SEC
        FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
        WHERE START_TIME >= ? AND START_TIME < DATEADD(day, 1, TO_DATE(?))
        GROUP BY USER_NAME
        ORDER BY NUM_QUERIES DESC
        """,
        params=[str(_start), str(_end)],
    ).to_pandas()


# --- Login History ---
st.header("Login History")

with st.spinner("Loading login history..."):
    login_df = load_login_history(start_date, end_date)

if not login_df.empty:
    total_success = int(login_df["SUCCESS_LOGINS"].sum())
    total_failed = int(login_df["FAILED_LOGINS"].sum())
    unique_users = login_df["USER_NAME"].nunique()

    with st.container(horizontal=True):
        st.metric("Unique Users", unique_users, border=True)
        st.metric("Successful Logins", f"{total_success:,}", border=True)
        st.metric("Failed Logins", f"{total_failed:,}", border=True)

    col1, col2 = st.columns(2)
    with col1:
        with st.container(border=True):
            st.subheader("Logins by User")
            user_logins = login_df.groupby("USER_NAME")[["SUCCESS_LOGINS", "FAILED_LOGINS"]].sum().reset_index()
            user_logins = user_logins.sort_values("SUCCESS_LOGINS", ascending=False).head(10)
            st.bar_chart(user_logins, x="USER_NAME", y=["SUCCESS_LOGINS", "FAILED_LOGINS"])

    with col2:
        with st.container(border=True):
            st.subheader("Logins by Auth Type")
            auth_logins = login_df.groupby("AUTH_TYPE")[["SUCCESS_LOGINS", "FAILED_LOGINS"]].sum().reset_index()
            st.bar_chart(auth_logins, x="AUTH_TYPE", y=["SUCCESS_LOGINS", "FAILED_LOGINS"])

    with st.container(border=True):
        st.subheader("Detail")
        st.dataframe(login_df, use_container_width=True, hide_index=True)
else:
    st.info("No login history found for the selected date range.")

# --- Query History ---
st.header("Query History")

with st.spinner("Loading query history..."):
    query_df = load_query_history(start_date, end_date)

if not query_df.empty:
    total_queries = int(query_df["NUM_QUERIES"].sum())
    total_duration = round(float(query_df["TOTAL_DURATION_SEC"].sum()), 1)
    active_users = query_df["USER_NAME"].nunique()

    with st.container(horizontal=True):
        st.metric("Active Users", active_users, border=True)
        st.metric("Total Queries", f"{total_queries:,}", border=True)
        st.metric("Total Duration", f"{total_duration:,.1f}s", border=True)

    with st.container(border=True):
        st.subheader("Queries by User")
        top_users = query_df.sort_values("NUM_QUERIES", ascending=False).head(10)
        st.bar_chart(top_users, x="USER_NAME", y="NUM_QUERIES")

    with st.container(border=True):
        st.subheader("Detail")
        st.dataframe(query_df, use_container_width=True, hide_index=True)
else:
    st.info("No query history found for the selected date range.")
