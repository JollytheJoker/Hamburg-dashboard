import streamlit as st
import pandas as pd
import plotly.express as px
import json
import geopandas as gpd
from scipy.stats import pearsonr

# -----------------
# --- LOAD DATA ---
# -----------------
df_districts = pd.read_excel("Stadtteile zu Bezirken.xlsx", index_col=0, header=0, engine="openpyxl")
df_districts = df_districts.reset_index()
df_districts.rename(columns={df_districts.columns[0]: "Stadtteile"}, inplace=True)

df = pd.read_excel("Stadtteilprofile2025.xlsx", index_col=0, header=1)
df = df.reset_index()
df.rename(columns={df.columns[0]: "Stadtteile"}, inplace=True)
df = df.merge(
    df_districts,
    on="Stadtteile",
    how="left"
)

gdf = gpd.read_file("Karte.geojson")

# falls nötig CRS setzen (wahrscheinlich 25832)
gdf = gdf.set_crs(epsg=25832)

# in WGS84 umwandeln
gdf = gdf.to_crs(epsg=4326)

geojson_fixed = gdf.__geo_interface__

# -----------------
# --- STREAMLIT ---
# -----------------
st.set_page_config(layout="wide")
# PRAMS
st.title("Hamburger Stadtteilanalyse")

st.sidebar.header("Filter")

# BEZIRKE
all_districts = sorted(df["Bezirk"].dropna().unique())

st.sidebar.subheader("Bezirke")

col1, col2 = st.sidebar.columns(2)

with col1:
    select_all_districts = st.button("Alle")

with col2:
    reset_districts = st.button("Reset")

default_districts = all_districts if select_all_districts else ["Eimsbüttel", "Altona"]

selected_districts = st.sidebar.multiselect(
    "Auswahl",
    options=all_districts,
    default=default_districts
)

if reset_districts:
    selected_districts = all_districts

filtered_df = df[df["Bezirk"].isin(selected_districts)] if selected_districts else df.copy()

# STADTTEILE
st.sidebar.subheader("Stadtteile")

all_stadtteile = sorted(filtered_df["Stadtteile"].dropna().unique())

col3, col4 = st.sidebar.columns(2)

with col3:
    select_all_stadtteile = st.button("Alle ")

with col4:
    reset_stadtteile = st.button("Reset ")

default_stadtteile = all_stadtteile if select_all_stadtteile else all_stadtteile

selected_stadtteile = st.sidebar.multiselect(
    "Auswahl",
    options=all_stadtteile,
    default=default_stadtteile
)

if reset_stadtteile:
    selected_stadtteile = all_stadtteile

final_df = filtered_df[filtered_df["Stadtteile"].isin(selected_stadtteile)]
numeric_like_cols = []

for col in final_df.columns:
    converted = pd.to_numeric(final_df[col], errors="coerce")

    if converted.notna().any():
        numeric_like_cols.append(col)

numeric_cols = numeric_like_cols

# BOXPLOTS
st.subheader("Boxplot")

box_col = st.selectbox(
    label="Vergleichswert",
    options=numeric_cols
)

fig_box = px.box(
    final_df,
    y=box_col,
    color="Bezirk",
    points="all",
custom_data=["Stadtteile"]
)

fig_box.update_traces(
    hovertemplate=
        "%{y}<br>" +
        "Stadtteil: %{customdata[0]}<br>" +
        "<extra></extra>"
)

st.plotly_chart(fig_box, use_container_width=True)

# MAP
fig_map = px.choropleth_mapbox(
    final_df,
    geojson=geojson_fixed,
    locations="Stadtteile",
    featureidkey="properties.Stadtteil",
    color=box_col,
    mapbox_style="open-street-map",
    center={"lat": 53.5511, "lon": 9.9937},
    zoom=9.3,
    opacity=0.9,
    color_continuous_scale="Viridis",
    height=700
)

st.plotly_chart(fig_map, use_container_width=True)


# DIAGRAMS
st.subheader("Realtion zwischen Daten")

x_axis = st.selectbox("X-Achse", numeric_cols, index=9)
y_axis = st.selectbox("Y-Achse", numeric_cols, index=22)

chart_type = st.selectbox(
    "Diagrammtyp",
    ["Punkte", "Linien"]
)


# --- Calculate Correlations ---
df_plot = final_df[[x_axis, y_axis, "Stadtteile", "Bezirk"]].copy()

# 1. alles zu string (wichtig gegen mixed types)
df_plot[x_axis] = df_plot[x_axis].astype(str)
df_plot[y_axis] = df_plot[y_axis].astype(str)

# 2. Problemwerte entfernen (z. B. "<", "nan", etc.)
for col in [x_axis, y_axis]:
    df_plot[col] = (
        df_plot[col]
        .str.replace("<", "", regex=False)
        .str.strip()
    )

# 3. in numerisch umwandeln (alles Ungültige -> NaN)
df_plot[x_axis] = pd.to_numeric(df_plot[x_axis], errors="coerce")
df_plot[y_axis] = pd.to_numeric(df_plot[y_axis], errors="coerce")

# 4. nur gültige Werte behalten
df_plot = df_plot.dropna(subset=[x_axis, y_axis])

r, p = pearsonr(df_plot[x_axis], df_plot[y_axis])

st.metric("Pearson-Korrelation (r)", f"{r:.3f}")
st.caption(f"p-Wert: {p:.3g}")

if abs(r) > 0.75:
    st.success("Starke Korrelation")
elif abs(r) > 0.5:
    st.info("Mittlere Korrelation")
else:
    st.warning("Keine Korrelation")

# --- Diagram ---
if chart_type == "Punkte":
    try: fig = px.scatter(
        final_df,
        x=x_axis,
        y=y_axis,
        hover_name="Stadtteile",
        color="Bezirk",
        trendline="ols",
        trendline_scope="overall"
    )
    except TypeError:
        fig = px.scatter(
            final_df,
            x=x_axis,
            y=y_axis,
            hover_name="Stadtteile",
            color="Bezirk"
        )
else:
    fig = px.line(
        final_df.sort_values(x_axis),
        x=x_axis,
        y=y_axis,
        hover_name="Stadtteile",
        color="Bezirk"
    )

st.plotly_chart(fig)

# DATA
st.subheader("Daten")

cols = ["Stadtteile", "Bezirk", *{x_axis, y_axis}]
cols = [c for c in cols if c in final_df.columns]

st.dataframe(final_df[cols], hide_index=True, use_container_width=True)
