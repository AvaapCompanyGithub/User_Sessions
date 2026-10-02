"""
Login & Query History Dashboard

Requires the app owner role to hold IMPORTED PRIVILEGES on database SNOWFLAKE.
Uses only packages bundled with Streamlit in Snowflake — no extra packages needed.
"""

import decimal
import math
from typing import Optional

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from snowflake.snowpark.context import get_active_session

# -------------------------------------------------
# Session
# -------------------------------------------------

try:
    session = get_active_session()
except Exception:
    conn = st.connection("snowflake")
    session = conn.session()
else:
    class _SessConn:
        def query(self, sql, ttl=300):
            return session.sql(sql).to_pandas()
    conn = _SessConn()

# -------------------------------------------------
# Page config
# -------------------------------------------------

st.set_page_config(
    page_title="Login & Query History",
    page_icon="📊",
    layout="wide",
)

# ----------------------------------------------------------------------
# Page settings
# Cache Snowflake queries for 1h; cast NUMBER/Decimal to float for charts.
# ----------------------------------------------------------------------

@st.cache_data(ttl=3600, show_spinner="Querying ACCOUNT_USAGE...")

def _query(sql: str, start: str, end: str) -> pd.DataFrame:
    df = session.sql(sql, params=[start, end]).to_pandas()
    # Snowflake NUMBER(p,s) arrives as decimal.Decimal -> object dtype.
    for c in df.columns:
        if df[c].map(lambda v: isinstance(v, decimal.Decimal)).any():
            df[c] = df[c].astype(float)
    # Normalize column names so mixed-case Snowflake identifiers are stable.
    df.columns = [str(c).strip() for c in df.columns]
    return df


def run(sql: str, start: str, end: str) -> pd.DataFrame:
    """A missing view or column degrades one section, not the whole app."""
    try:
        return _query(sql, start, end)
    except Exception as e:
        st.warning(f"Query failed, section will be empty: {e}")
        return pd.DataFrame()

def run_optional(sql: str, start: str, end: str) -> pd.DataFrame:
    """Silent variant: these views are legitimately absent on many accounts."""
    try:
        return _query(sql, start, end)
    except Exception:
        return pd.DataFrame()

# ----------------------------------------------------------------------
# Colors
# ----------------------------------------------------------------------

NAVY = "#16324F"
NAVY_LIGHT = "#2A5F8F"
NAVY_DEEP = "#0F2438"
SNOW_BLUE = "#29B5E8"
BLUE_MID = "#5FC5EC"
BLUE_LIGHT = "#A7D8EF"
BLUE_PALE = "#CFE8F5"
PANEL = "#E9EEF2"
CARD_BG = "#FFFFFF"
INK = "#0F2438"
MUTED = "#6B7F92"
GREEN = "#1F9D6B"
RED = "#C23B3B"
WHITE = "#FFFFFF"
GOLD = "#D4A017"
CHART_BLUE = "#4C6EF5"
CHART_GOLD = "#D4A017"

SUCCESS_FAIL_COLORS = {
    "SUCCESS_LOGINS": CHART_GOLD,
    "FAILED_LOGINS": CHART_BLUE,
}

# ----------------------------------------------------------------------
# Style
# ----------------------------------------------------------------------

st.markdown(
    f"""
    <style>
      .stApp {{ background: #F4F6F8; }}
      .block-container {{ padding-top: 1.4rem; max-width: 1600px; }}
      #MainMenu, footer {{ visibility: hidden; }}

      .masthead {{ display: flex; align-items: baseline; gap: .55rem; margin-bottom: .1rem; }}
      .masthead h1 {{
        font-size: 1.65rem; font-weight: 800; color: {INK};
        margin: 0; letter-spacing: -.02em;
      }}
      .masthead .logo {{
        height: 28px; width: auto; object-fit: contain;
        display: block;
      }}
      .masthead .logo-fallback {{
        width: 28px; height: 28px; border-radius: 6px;
        background: linear-gradient(135deg, {SNOW_BLUE}, {NAVY_LIGHT});
        flex-shrink: 0;
      }}
      .subhead {{ color: {MUTED}; font-size: .75rem; margin: .1rem 0 .8rem 0; }}

      .card {{
        border-radius: 12px; padding: .85rem 1rem 0.95rem 1rem; height: 100%;
        text-align: left; background: {CARD_BG};
        border: 1px solid #E2E8EE;
      }}
      .card .label {{
        font-size: .72rem; font-weight: 600; letter-spacing: .01em;
        color: {MUTED}; margin-bottom: .35rem; line-height: 1.2;
      }}
      .card .value {{
        font-size: 1.55rem; font-weight: 800; letter-spacing: -.03em;
        line-height: 1.15; font-variant-numeric: tabular-nums;
        color: {INK};
      }}

      .section-title {{
        font-size: 1.28rem; font-weight: 800; color: {INK};
        margin: 0.15rem 0 0.75rem 0; letter-spacing: -.02em;
      }}
      .panel-title {{
        font-size: .92rem; font-weight: 700; color: {INK};
        margin: 0 0 .45rem .05rem;
      }}
      .chart-box {{
        background: {WHITE};
        border: 1px solid #E2E8EE;
        border-radius: 12px;
        padding: .7rem .8rem .55rem .8rem;
        height: 100%;
      }}
      .table-box {{
        background: {WHITE};
        border: 1px solid #E2E8EE;
        border-radius: 12px;
        padding: .7rem .8rem .85rem .8rem;
      }}

      .note {{
        text-align: left; color: {MUTED}; font-size: .66rem;
        margin: .55rem 0 1rem 0; line-height: 1.4;
      }}
      div[data-testid="stSelectbox"] label,
      div[data-testid="stDateInput"] label {{
        color: {MUTED}; font-size: .72rem;
      }}

      div[data-testid="stDataFrame"] {{
        font-size: 0.72rem;
      }}
      div[data-testid="stDataFrame"] table {{
        font-size: 0.72rem;
      }}
      div[data-testid="stDataFrame"] th {{
        font-size: 0.68rem !important;
        padding-top: 0.25rem !important;
        padding-bottom: 0.25rem !important;
      }}
      div[data-testid="stDataFrame"] td {{
        font-size: 0.72rem !important;
        padding-top: 0.2rem !important;
        padding-bottom: 0.2rem !important;
      }}
    </style>
    """,
    unsafe_allow_html=True,
)

# ----------------------------------------------------------------------
# Logo
# ----------------------------------------------------------------------

_logo_html = '<div class="logo-fallback" title="Add logo.png or logo.jpg"></div>'
try:
    import base64 as _b64

    _logo_dir = Path(__file__).resolve().parent
    _logo_path = None
    _mime = None
    for _name, _m in (
        ("logo.png", "image/png"),
        ("logo.jpg", "image/jpeg"),
        ("logo.jpeg", "image/jpeg"),
    ):
        _candidate = _logo_dir / _name
        if _candidate.is_file():
            _logo_path, _mime = _candidate, _m
            break
    if _logo_path is not None:
        _b64data = _b64.b64encode(_logo_path.read_bytes()).decode("ascii")
        _logo_html = (
            f'<img class="logo" alt="Logo" '
            f'src="data:{_mime};base64,{_b64data}"/>'
        )
except Exception:
    pass

# ----------------------------------------------------------------------
# Page Header
# ----------------------------------------------------------------------

DATE_PRESET_MAP = {
    "Today": "TODAY",
    "Week to Date": "WTD",
    "Month to Date": "MTD",
    "Quarter to Date": "QTD",
    "Year to Date": "YTD",
}
DATE_PRESETS = list(DATE_PRESET_MAP.keys())

if "last_refreshed" not in st.session_state:
    st.session_state.last_refreshed = datetime.now()

title_col, range_col = st.columns([3.2, 1.3])
with title_col:
    st.markdown(
        f'<div class="masthead">{_logo_html}<h1>Login & Query History Dashboard</h1></div>'
        '<div class="subhead">Overview of usage on the account.</div>'
        f'<div style="color:{MUTED};font-size:.72rem;margin:-0.35rem 0 0.15rem 0;">'
        f"Last refreshed: {st.session_state.last_refreshed.strftime('%Y-%m-%d %H:%M:%S')}</div>",
        unsafe_allow_html=True,
    )
with range_col:
    preset_label = st.selectbox(
        "Date Range",
        DATE_PRESETS,
        index=DATE_PRESETS.index("Year to Date"),
    )
    preset = DATE_PRESET_MAP[preset_label]

today = datetime.now().date()
if preset == "TODAY":
    start_date = today
    end_date = today
elif preset == "WTD":
    start_date = today - timedelta(days=today.weekday())  # Monday
    end_date = today
elif preset == "MTD":
    start_date = today.replace(day=1)
    end_date = today
elif preset == "QTD":
    quarter_start_month = ((today.month - 1) // 3) * 3 + 1
    start_date = today.replace(month=quarter_start_month, day=1)
    end_date = today
else:  # YTD
    start_date = today.replace(month=1, day=1)
    end_date = today

with range_col:
    st.markdown(
        f'<div style="color:{MUTED};font-size:0.72rem;margin-top:-0.35rem;">'
        f'{start_date.strftime("%b %d, %Y")} → {end_date.strftime("%b %d, %Y")}'
        f'</div>',
        unsafe_allow_html=True,
    )

st.markdown("---")

# ACCOUNT_USAGE ranges are half-open; end bound is exclusive.
p_start = start_date.strftime("%Y-%m-%d")
p_end = (end_date + timedelta(days=1)).isoformat()


# ----------------------------------------------------------------------
# Queries
# ----------------------------------------------------------------------

Q_LOGIN = """
SELECT
    USER_NAME,
    SUM(CASE WHEN IS_SUCCESS = 'YES' THEN 1 ELSE 0 END) AS SUCCESS_LOGINS,
    SUM(CASE WHEN IS_SUCCESS = 'NO' THEN 1 ELSE 0 END) AS FAILED_LOGINS,
    FIRST_AUTHENTICATION_FACTOR AS AUTH_TYPE,
    MAX(EVENT_TIMESTAMP)::TIMESTAMP_NTZ AS LAST_EVENT
FROM SNOWFLAKE.ACCOUNT_USAGE.LOGIN_HISTORY
WHERE EVENT_TIMESTAMP >= ? AND EVENT_TIMESTAMP < ?
GROUP BY USER_NAME, FIRST_AUTHENTICATION_FACTOR
ORDER BY SUCCESS_LOGINS DESC
"""

Q_QUERY = """
SELECT
    USER_NAME,
    COUNT(*) AS NUM_QUERIES,
    SUM(TOTAL_ELAPSED_TIME) / 1000 AS TOTAL_DURATION_SEC
FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
WHERE START_TIME >= ? AND START_TIME < ?
GROUP BY USER_NAME
ORDER BY NUM_QUERIES DESC
"""

login = run(Q_LOGIN, p_start, p_end)
qry = run(Q_QUERY, p_start, p_end)


def col(df: pd.DataFrame, name: str) -> Optional[str]:
    """Resolve a column regardless of Snowflake identifier casing."""
    if df.empty:
        return None
    wanted = name.lower()
    for c in df.columns:
        if str(c).lower() == wanted:
            return c
    return None


def as_num(df: pd.DataFrame, name: str) -> pd.Series:
    c = col(df, name)
    if c is None:
        return pd.Series(dtype=float)
    return pd.to_numeric(df[c], errors="coerce").fillna(0.0)


def fmt_int(v: float) -> str:
    return f"{int(round(v)):,}"


def fmt_duration(seconds: float) -> str:
    return f"{seconds:,.1f}s"


def card_html(label: str, value: str) -> str:
    return (
        f'<div class="card">'
        f'<div class="label">{label}</div>'
        f'<div class="value">{value}</div>'
        f"</div>"
    )


def truncate_label(s: str, n: int = 14) -> str:
    s = "" if s is None or (isinstance(s, float) and math.isnan(s)) else str(s)
    return s if len(s) <= n else s[: n - 1] + "…"


def stacked_login_chart(df: pd.DataFrame, category_col: str, height: int = 280):
    """Stacked success/fail bar chart. Falls back to Streamlit native chart."""
    if df.empty:
        st.info("No login data for the selected range.")
        return

    long = df.melt(
        id_vars=[category_col],
        value_vars=["SUCCESS_LOGINS", "FAILED_LOGINS"],
        var_name="Status",
        value_name="Logins",
    )
    try:
        import altair as alt

        color_scale = alt.Scale(
            domain=["FAILED_LOGINS", "SUCCESS_LOGINS"],
            range=[CHART_BLUE, CHART_GOLD],
        )
        n_cats = int(df[category_col].nunique())
        chart = (
            alt.Chart(long)
            .mark_bar()
            .encode(
                x=alt.X(
                    f"{category_col}:N",
                    sort=list(df[category_col]),
                    axis=alt.Axis(
                        title=category_col,
                        labelAngle=-90,
                        labelAlign="right",
                        labelBaseline="middle",
                        labelFontSize=10,
                        titleFontSize=11,
                        titleColor=MUTED,
                    ),
                ),
                y=alt.Y(
                    "Logins:Q",
                    stack="zero",
                    axis=alt.Axis(title=None, labelFontSize=10),
                ),
                color=alt.Color(
                    "Status:N",
                    scale=color_scale,
                    legend=alt.Legend(
                        title=None,
                        orient="bottom",
                        direction="horizontal",
                        labelFontSize=11,
                        symbolSize=80,
                    ),
                ),
                tooltip=[
                    alt.Tooltip(f"{category_col}:N"),
                    alt.Tooltip("Status:N"),
                    alt.Tooltip("Logins:Q", format=",.0f"),
                ],
            )
            .properties(height=height)
            .configure_view(strokeWidth=0)
            .configure_axis(grid=True, gridOpacity=0.25)
        )
        st.altair_chart(chart, use_container_width=True)
    except Exception:
        plot = df.set_index(category_col)[["FAILED_LOGINS", "SUCCESS_LOGINS"]]
        st.bar_chart(plot, height=height, use_container_width=True, color=[CHART_BLUE, CHART_GOLD])


def queries_bar_chart(df: pd.DataFrame, height: int = 300):
    if df.empty:
        st.info("No query data for the selected range.")
        return
    try:
        import altair as alt

        chart = (
            alt.Chart(df)
            .mark_bar(color=CHART_BLUE)
            .encode(
                x=alt.X(
                    "USER_NAME:N",
                    sort=list(df["USER_NAME"]),
                    axis=alt.Axis(
                        title="USER_NAME",
                        labelAngle=-90,
                        labelAlign="right",
                        labelBaseline="middle",
                        labelFontSize=10,
                        titleFontSize=11,
                        titleColor=MUTED,
                    ),
                ),
                y=alt.Y(
                    "NUM_QUERIES:Q",
                    axis=alt.Axis(title="NUM_QUERIES", labelFontSize=10, titleFontSize=11),
                ),
                tooltip=[
                    alt.Tooltip("USER_NAME:N"),
                    alt.Tooltip("NUM_QUERIES:Q", format=",.0f"),
                    alt.Tooltip("TOTAL_DURATION_SEC:Q", format=",.1f"),
                ],
            )
            .properties(height=height)
            .configure_view(strokeWidth=0)
            .configure_axis(grid=True, gridOpacity=0.25)
        )
        st.altair_chart(chart, use_container_width=True)
    except Exception:
        st.bar_chart(
            df.set_index("USER_NAME")[["NUM_QUERIES"]],
            height=height,
            use_container_width=True,
        )


# ----------------------------------------------------------------------
# Login History
# ----------------------------------------------------------------------

st.markdown('<div class="section-title">Login History</div>', unsafe_allow_html=True)

login_user_col = col(login, "USER_NAME")
login_ok_col = col(login, "SUCCESS_LOGINS")
login_fail_col = col(login, "FAILED_LOGINS")
login_auth_col = col(login, "AUTH_TYPE")
login_last_col = col(login, "LAST_EVENT")

if login.empty or login_user_col is None:
    unique_users = 0
    success_logins = 0.0
    failed_logins = 0.0
else:
    unique_users = int(login[login_user_col].nunique())
    success_logins = float(as_num(login, "SUCCESS_LOGINS").sum())
    failed_logins = float(as_num(login, "FAILED_LOGINS").sum())

k1, k2, k3 = st.columns(3)
with k1:
    st.markdown(card_html("Unique Users", fmt_int(unique_users)), unsafe_allow_html=True)
with k2:
    st.markdown(card_html("Successful Logins", fmt_int(success_logins)), unsafe_allow_html=True)
with k3:
    st.markdown(card_html("Failed Logins", fmt_int(failed_logins)), unsafe_allow_html=True)

st.markdown("<div style='height:0.7rem'></div>", unsafe_allow_html=True)

# Chart frames
if login.empty or login_user_col is None:
    by_user = pd.DataFrame(columns=["USER_NAME", "SUCCESS_LOGINS", "FAILED_LOGINS"])
    by_auth = pd.DataFrame(columns=["AUTH_TYPE", "SUCCESS_LOGINS", "FAILED_LOGINS"])
else:
    tmp = pd.DataFrame(
        {
            "USER_NAME": login[login_user_col].astype(str),
            "AUTH_TYPE": (
                login[login_auth_col].fillna("(none)").astype(str)
                if login_auth_col
                else "(none)"
            ),
            "SUCCESS_LOGINS": as_num(login, "SUCCESS_LOGINS"),
            "FAILED_LOGINS": as_num(login, "FAILED_LOGINS"),
        }
    )
    by_user = (
        tmp.groupby("USER_NAME", as_index=False)[["SUCCESS_LOGINS", "FAILED_LOGINS"]]
        .sum()
        .sort_values("SUCCESS_LOGINS", ascending=False)
    )
    by_auth = (
        tmp.groupby("AUTH_TYPE", as_index=False)[["SUCCESS_LOGINS", "FAILED_LOGINS"]]
        .sum()
        .sort_values("SUCCESS_LOGINS", ascending=False)
    )
    by_user["USER_NAME"] = by_user["USER_NAME"].map(lambda s: truncate_label(s, 16))
    by_auth["AUTH_TYPE"] = by_auth["AUTH_TYPE"].map(lambda s: truncate_label(s, 16))

c_user, c_auth = st.columns(2, gap="medium")
with c_user:
    st.markdown('<div class="panel-title">Logins by User</div>', unsafe_allow_html=True)
    stacked_login_chart(by_user.head(15), "USER_NAME")
with c_auth:
    st.markdown('<div class="panel-title">Logins by Auth Type</div>', unsafe_allow_html=True)
    stacked_login_chart(by_auth.head(12), "AUTH_TYPE")

st.markdown("<div style='height:0.85rem'></div>", unsafe_allow_html=True)

st.markdown('<div class="panel-title">Detail</div>', unsafe_allow_html=True)
if login.empty or login_user_col is None:
    st.info("No login history for the selected range.")
else:
    detail_login = pd.DataFrame(
        {
            "USER_NAME": login[login_user_col],
            "SUCCESS_LOGINS": as_num(login, "SUCCESS_LOGINS").astype(int),
            "FAILED_LOGINS": as_num(login, "FAILED_LOGINS").astype(int),
            "AUTH_TYPE": login[login_auth_col] if login_auth_col else "",
            "LAST_EVENT": login[login_last_col] if login_last_col else pd.NaT,
        }
    )
    if "LAST_EVENT" in detail_login.columns:
        detail_login["LAST_EVENT"] = pd.to_datetime(
            detail_login["LAST_EVENT"], errors="coerce"
        )
    row_h = 35
    tbl_h = min(380, 48 + max(len(detail_login), 1) * row_h)
    st.dataframe(
        detail_login,
        hide_index=True,
        use_container_width=True,
        height=tbl_h,
        column_config={
            "USER_NAME": st.column_config.TextColumn("USER_NAME", width="large"),
            "SUCCESS_LOGINS": st.column_config.NumberColumn(
                "SUCCESS_LOGINS", format="%d", width="small"
            ),
            "FAILED_LOGINS": st.column_config.NumberColumn(
                "FAILED_LOGINS", format="%d", width="small"
            ),
            "AUTH_TYPE": st.column_config.TextColumn("AUTH_TYPE", width="medium"),
            "LAST_EVENT": st.column_config.DatetimeColumn(
                "LAST_EVENT", format="YYYY-MM-DD HH:mm:ss", width="medium"
            ),
        },
    )

st.markdown("---")

# ----------------------------------------------------------------------
# Query History
# ----------------------------------------------------------------------

st.markdown('<div class="section-title">Query History</div>', unsafe_allow_html=True)

qry_user_col = col(qry, "USER_NAME")
qry_n_col = col(qry, "NUM_QUERIES")
qry_dur_col = col(qry, "TOTAL_DURATION_SEC")

if qry.empty or qry_user_col is None:
    active_users = 0
    total_queries = 0.0
    total_duration = 0.0
else:
    active_users = int(qry[qry_user_col].nunique())
    total_queries = float(as_num(qry, "NUM_QUERIES").sum())
    total_duration = float(as_num(qry, "TOTAL_DURATION_SEC").sum())

q1, q2, q3 = st.columns(3)
with q1:
    st.markdown(card_html("Active Users", fmt_int(active_users)), unsafe_allow_html=True)
with q2:
    st.markdown(card_html("Total Queries", fmt_int(total_queries)), unsafe_allow_html=True)
with q3:
    st.markdown(card_html("Total Duration", fmt_duration(total_duration)), unsafe_allow_html=True)

st.markdown("<div style='height:0.7rem'></div>", unsafe_allow_html=True)

st.markdown('<div class="panel-title">Queries by User</div>', unsafe_allow_html=True)
if qry.empty or qry_user_col is None:
    st.info("No query history for the selected range.")
else:
    by_qry_user = pd.DataFrame(
        {
            "USER_NAME": qry[qry_user_col].astype(str).map(lambda s: truncate_label(s, 16)),
            "NUM_QUERIES": as_num(qry, "NUM_QUERIES"),
            "TOTAL_DURATION_SEC": as_num(qry, "TOTAL_DURATION_SEC"),
        }
    ).sort_values("NUM_QUERIES", ascending=False)
    queries_bar_chart(by_qry_user.head(15))

st.markdown("<div style='height:0.85rem'></div>", unsafe_allow_html=True)

st.markdown('<div class="panel-title">Detail</div>', unsafe_allow_html=True)
if qry.empty or qry_user_col is None:
    st.info("No query history for the selected range.")
else:
    detail_qry = pd.DataFrame(
        {
            "USER_NAME": qry[qry_user_col],
            "NUM_QUERIES": as_num(qry, "NUM_QUERIES").astype(int),
            "TOTAL_DURATION_SEC": as_num(qry, "TOTAL_DURATION_SEC").round(3),
        }
    ).sort_values("NUM_QUERIES", ascending=False)
    row_h = 35
    tbl_h = min(380, 48 + max(len(detail_qry), 1) * row_h)
    st.dataframe(
        detail_qry,
        hide_index=True,
        use_container_width=True,
        height=tbl_h,
        column_config={
            "USER_NAME": st.column_config.TextColumn("USER_NAME", width="large"),
            "NUM_QUERIES": st.column_config.NumberColumn(
                "NUM_QUERIES", format="%d", width="medium"
            ),
            "TOTAL_DURATION_SEC": st.column_config.NumberColumn(
                "TOTAL_DURATION_SEC", format="%.3f", width="medium"
            ),
        },
    )

# ----------------------------------------------------------------------
# Notes
# ----------------------------------------------------------------------

st.markdown("---")

st.markdown(
    f"""
    <div class="note">
    Change the date range in the header to filter both login and query activity.
    ACCOUNT_USAGE views are not real time. LOGIN_HISTORY and QUERY_HISTORY
    typically lag by up to a few hours, so ranges that include today or yesterday
    will understate actual activity, and the most recent day is always partial.<br><br>
    Login rows are grouped by user and first authentication factor, so the same
    user can appear more than once when they authenticate with different methods.
    Query duration is the sum of TOTAL_ELAPSED_TIME converted to seconds.
    Figures are drawn from ACCOUNT_USAGE and are for internal analysis only.
    </div>
    """,
    unsafe_allow_html=True,
)
