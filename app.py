import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta
import random
import io

st.set_page_config(page_title="Lab Quality Analyzer", page_icon="⚗️", layout="wide")

PARAMETERS = {
    "pH":           {"min": 6.5,  "max": 7.5,  "unit": "pH"},
    "Conduttività": {"min": 100,  "max": 500,  "unit": "µS/cm"},
    "TOC":          {"min": 0.0,  "max": 5.0,  "unit": "mg/L"},
    "Torbidità":    {"min": 0.0,  "max": 1.0,  "unit": "NTU"},
    "Cloro_libero": {"min": 0.2,  "max": 0.6,  "unit": "mg/L"},
}

@st.cache_data
def generate_data(n_days=90):
    random.seed(42)
    np.random.seed(42)
    records = []
    base = datetime.now() - timedelta(days=n_days)
    for day in range(n_days):
        date = base + timedelta(days=day)
        for s in range(3):
            rec = {"data": date.date(), "lotto": f"LOT-{date.strftime('%Y%m%d')}-{s+1:02d}"}
            for p, lim in PARAMETERS.items():
                center = (lim["min"] + lim["max"]) / 2
                spread = (lim["max"] - lim["min"]) / 2
                if random.random() < 0.08:
                    val = center + spread * random.uniform(1.1, 1.6) * random.choice([-1, 1])
                else:
                    val = center + spread * np.random.normal(0, 0.35)
                rec[p] = round(float(val), 3)
            records.append(rec)
    df = pd.DataFrame(records)
    df["data"] = pd.to_datetime(df["data"])
    mask = pd.Series([True] * len(df))
    for p, lim in PARAMETERS.items():
        mask = mask & df[p].between(lim["min"], lim["max"])
    df["esito"] = mask.map({True: "OK", False: "NC"})
    return df

with st.sidebar:
    st.markdown("### ⚗️ Lab Quality Analyzer")
    st.markdown("---")
    n_days = st.slider("Giorni analisi", 30, 180, 90, step=10)
    selected = st.multiselect("Parametri", list(PARAMETERS.keys()), default=list(PARAMETERS.keys()))
    soglia = st.slider("Soglia NC alert (%)", 1, 20, 5)
    filtro = st.radio("Mostra", ["Tutti", "Solo OK", "Solo NC"])
    st.markdown("---")
    st.caption("Portfolio · Diego R.\nQuality Data Analyst\nPython · SQL · Streamlit")

df = generate_data(n_days)
df_view = df if filtro == "Tutti" else df[df["esito"] == filtro.split()[-1]]

st.markdown("<h1 style='text-align:center;color:#c9a84c;'>⚗ Lab Quality Analyzer</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align:center;color:#8899aa;font-style:italic;margin-bottom:24px;'>Analisi automatizzata parametri chimici · Controllo qualità laboratorio</p>", unsafe_allow_html=True)

total = len(df)
conformi = (df["esito"] == "OK").sum()
nc = total - conformi
pct = round(conformi / total * 100, 1)
pct_color = "#4caf82" if pct >= 95 else "#e6a817" if pct >= 85 else "#c05050"

c1, c2, c3, c4 = st.columns(4)
for col, val, label, color in [
    (c1, total,    "Campioni Totali",  "#c9a84c"),
    (c2, conformi, "Conformi",         "#4caf82"),
    (c3, nc,       "Non Conformi",     "#c05050"),
    (c4, f"{pct}%","Tasso Conformità", pct_color)]:
    with col:
        st.metric(label=label, value=val)

st.markdown("---")
st.markdown("### 📈 Trend Conformità Settimanale")
df["week"] = df["data"].dt.isocalendar().week.astype(int)
weekly = df.groupby("week").apply(
    lambda x: round((x["esito"] == "OK").sum() / len(x) * 100, 1)
).reset_index(name="pct")
bar_colors = ["#4caf82" if v >= 95 else "#e6a817" if v >= 85 else "#c05050" for v in weekly["pct"]]
fig = go.Figure(go.Bar(
    x=[f"W{w}" for w in weekly["week"]],
    y=weekly["pct"],
    marker_color=bar_colors
))
fig.add_hline(y=95, line_dash="dash", line_color="#c9a84c", annotation_text="Target 95%")
fig.update_layout(height=260, margin=dict(l=10,r=10,t=10,b=10), yaxis=dict(range=[60,102]))
st.plotly_chart(fig, use_container_width=True)

st.markdown("---")
col_l, col_r = st.columns(2)

with col_l:
    st.markdown("### ⚖️ NC per Parametro")
    nc_rows = []
    for p in (selected or list(PARAMETERS.keys())):
        lim = PARAMETERS[p]
        out = ((df[p] < lim["min"]) | (df[p] > lim["max"])).sum()
        nc_rows.append({"Parametro": p, "NC%": round(out/len(df)*100, 1), "NC#": int(out)})
    nc_df = pd.DataFrame(nc_rows).sort_values("NC%", ascending=True)
    bc = ["#c05050" if v > soglia else "#e6a817" if v > soglia/2 else "#4caf82" for v in nc_df["NC%"]]
    fig2 = go.Figure(go.Bar(
        x=nc_df["NC%"], y=nc_df["Parametro"], orientation="h",
        marker_color=bc, text=[f"{v}%" for v in nc_df["NC%"]], textposition="outside"
    ))
    fig2.add_vline(x=soglia, line_dash="dash", line_color="#c9a84c")
    fig2.update_layout(height=280, margin=dict(l=10,r=40,t=10,b=10))
    st.plotly_chart(fig2, use_container_width=True)

with col_r:
    st.markdown("### 🔬 Distribuzione Parametro")
    p_sel = st.selectbox("Parametro", selected or list(PARAMETERS.keys()))
    lim = PARAMETERS[p_sel]
    s = df[p_sel]
    ok_v = s[(s >= lim["min"]) & (s <= lim["max"])]
    nc_v = s[(s < lim["min"]) | (s > lim["max"])]
    fig3 = go.Figure()
    fig3.add_trace(go.Histogram(x=ok_v, name="OK", marker_color="#4caf82", opacity=0.75, nbinsx=30))
    fig3.add_trace(go.Histogram(x=nc_v, name="NC", marker_color="#c05050", opacity=0.85, nbinsx=30))
    fig3.add_vline(x=lim["min"], line_dash="dash", line_color="#c9a84c")
    fig3.add_vline(x=lim["max"], line_dash="dash", line_color="#c9a84c")
    fig3.update_layout(height=280, barmode="overlay", margin=dict(l=10,r=10,t=10,b=10))
    st.plotly_chart(fig3, use_container_width=True)

st.markdown("---")
st.markdown("### 📋 Riepilogo Statistico")
rows = []
for p in (selected or list(PARAMETERS.keys())):
    lim = PARAMETERS[p]
    s = df[p]
    out = ((s < lim["min"]) | (s > lim["max"])).sum()
    pct_p = round(out / len(s) * 100, 1)
    rows.append({
        "Parametro": p, "Unità": lim["unit"],
        "Min": lim["min"], "Max": lim["max"],
        "Media": round(float(s.mean()), 3),
        "Std": round(float(s.std()), 3),
        "NC#": int(out), "NC%": pct_p,
        "Stato": "✓ OK" if pct_p <= soglia/2 else "⚠ Warn" if pct_p <= soglia else "✗ Critico"
    })
st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

st.markdown("---")
st.markdown("### 🗄️ Dati Grezzi")
buf = io.StringIO()
df_view.to_csv(buf, index=False)
st.download_button("⬇ Scarica CSV", buf.getvalue(), f"lab_{datetime.now().strftime('%Y%m%d')}.csv", "text/csv")
st.dataframe(df_view.sort_values("data", ascending=False).head(100), use_container_width=True, hide_index=True)

st.caption("Portfolio · Diego R. · Python · Pandas · Plotly · Streamlit")
