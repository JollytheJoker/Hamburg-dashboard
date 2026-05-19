import streamlit as st
import pandas as pd
import plotly.express as px
import json
import geopandas as gpd

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
all_districts = df["Bezirk"].dropna().unique()
col1, col2 = st.sidebar.columns(2)
with col1:
    if st.button("Alle Bezirke"):
        selected_districts = st.sidebar.multiselect(
            "Bezirke auswählen",
            options=all_districts,
            default=all_districts,
        )
    else:
        selected_districts = st.sidebar.multiselect(
            "Bezirke auswählen",
            options=all_districts,
            default=["Eimsbüttel", "Altona"]
        )

if len(selected_districts) == 0:
    filtered_df = df.copy()
else:
    filtered_df = df[df["Bezirk"].isin(selected_districts)]

# STADTTEILE
all_stadtteile = filtered_df["Stadtteile"].unique()
col3, col4 = st.sidebar.columns(2)
with col3:
    if st.button("Alle Stadtteile"):
        selected_stadtteile = st.sidebar.multiselect(
            "Stadtteile auswählen",
            options=filtered_df["Stadtteile"].unique(),
            default=filtered_df["Stadtteile"].unique()
        )
    else:
        selected_stadtteile = st.sidebar.multiselect(
            "Stadtteile auswählen",
            options=filtered_df["Stadtteile"].unique(),
            default=filtered_df["Stadtteile"].unique()
        )

final_df = filtered_df[filtered_df["Stadtteile"].isin(selected_stadtteile)]
numeric_cols = final_df.select_dtypes(include="number").columns

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
    points="all"
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

x_axis = st.selectbox("X-Achse", numeric_cols, index=2)
y_axis = st.selectbox("Y-Achse", numeric_cols, index=1)

chart_type = st.selectbox(
    "Diagrammtyp",
    ["Linien", "Punkte"]
)

if chart_type == "Punkte":
    fig = px.scatter(
        final_df,
        x=x_axis,
        y=y_axis,
        hover_name="Stadtteile",
        color="Bezirk",
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