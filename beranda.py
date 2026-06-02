import os

import pandas as pd
import plotly.express as px
import streamlit as st

# 1. Konfigurasi Halaman Utama Dashboard
st.set_page_config(
    page_title="GSMaP Blend Rainfall Dashboard",
    page_icon="🛰️",
    layout="wide"
)

st.title("🛰️ Dashboard Grid Data Blend GSMaP")
st.markdown("Aplikasi visualisasi data spasial iklim berbasis grid dari satelit GSMaP Blending.")
st.markdown("---")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")


@st.cache_data
def load_gsmap_data(file_path):
    extension = os.path.splitext(file_path)[1].lower()
    if extension == ".csv":
        df = pd.read_csv(file_path)
    else:
        df = pd.read_excel(file_path)

    df.columns = df.columns.str.strip().str.lower()
    return df


def find_column(df, possible_names):
    for name in possible_names:
        if name in df.columns:
            return name
    return None


def klasifikasi_sifat_hujan(persen):
    if persen < 85:
        return "Bawah Normal (BN)"
    elif 85 <= persen <= 115:
        return "Normal (N)"
    else:
        return "Atas Normal (AN)"


st.sidebar.header("📋 Pengaturan & Filter")

available_files = []
if os.path.isdir(DATA_DIR):
    available_files = sorted(
        [f for f in os.listdir(DATA_DIR) if f.lower().endswith((".csv", ".xls", ".xlsx"))]
    )

if not available_files:
    st.sidebar.error("⚠️ Folder data kosong atau tidak ditemukan. Pastikan ada file .csv/.xls/.xlsx di folder 'data'.")
    st.stop()

selected_file = st.sidebar.selectbox("Pilih file data dari folder data:", available_files)
file_path = os.path.join(DATA_DIR, selected_file)

try:
    df_raw = load_gsmap_data(file_path)

    actual_lon = find_column(df_raw, ["lon"])
    actual_lat = find_column(df_raw, ["lat"])
    actual_ch = find_column(df_raw, ["ch"])
    actual_sh_pct = find_column(df_raw, ["sh%", "shpercent"])
    actual_anom = find_column(df_raw, ["anomch"])

    if not (actual_lon and actual_lat and actual_ch):
        st.error("❌ Struktur kolom tidak sesuai! Pastikan file memiliki kolom: lon, lat, dan ch.")
        st.stop()

    for col in [actual_lon, actual_lat, actual_ch]:
        df_raw[col] = pd.to_numeric(df_raw[col], errors='coerce')

    if actual_sh_pct:
        df_raw[actual_sh_pct] = pd.to_numeric(df_raw[actual_sh_pct], errors='coerce')
        df_raw['sifat_hujan_kategori'] = df_raw[actual_sh_pct].apply(klasifikasi_sifat_hujan)

    if actual_anom:
        df_raw[actual_anom] = pd.to_numeric(df_raw[actual_anom], errors='coerce')

    required_columns = [actual_lon, actual_lat, actual_ch]
    if actual_sh_pct:
        required_columns.append(actual_sh_pct)
    if actual_anom:
        required_columns.append(actual_anom)

    df_clean = df_raw.dropna(subset=required_columns).reset_index(drop=True)

    st.sidebar.markdown("### Filter Nilai Parameter")

    min_ch = float(df_clean[actual_ch].min())
    max_ch = float(df_clean[actual_ch].max())

    slider_ch = st.sidebar.slider(
        "Range Curah Hujan (mm):",
        min_value=min_ch,
        max_value=max_ch,
        value=(min_ch, max_ch)
    )

    df_filtered = df_clean[
        (df_clean[actual_ch] >= slider_ch[0]) &
        (df_clean[actual_ch] <= slider_ch[1])
    ]

    if actual_sh_pct:
        kategori_opsional = ['Bawah Normal (BN)', 'Normal (N)', 'Atas Normal (AN)']
        available_kategori = [k for k in kategori_opsional if k in df_filtered['sifat_hujan_kategori'].unique()]
        selected_kategori = st.sidebar.multiselect(
            "Pilih Kategori Sifat Hujan:",
            kategori_opsional,
            default=available_kategori
        )
        if selected_kategori:
            df_filtered = df_filtered[df_filtered['sifat_hujan_kategori'].isin(selected_kategori)]

    if df_filtered.empty:
        st.warning("⚠️ Tidak ada data grid yang cocok dengan filter Anda.")
        st.stop()

    total_grid = len(df_filtered)
    rerata_ch = df_filtered[actual_ch].mean()
    max_val_ch = df_filtered[actual_ch].max()
    idx_max = df_filtered[actual_ch].idxmax()
    coord_max = f"({df_filtered.loc[idx_max, actual_lat]}, {df_filtered.loc[idx_max, actual_lon]})"

    kpi1, kpi2, kpi3 = st.columns(3)
    with kpi1:
        st.metric(label="Total Titik Grid Teranalisis", value=f"{total_grid} Titik")
    with kpi2:
        st.metric(label="Rata-rata Curah Hujan Grid", value=f"{rerata_ch:.2f} mm")
    with kpi3:
        st.metric(label="Curah Hujan Maksimum", value=f"{max_val_ch:.2f} mm", delta=f"Koordinat: {coord_max}")

    st.markdown("---")

    st.subheader("🗺️ Peta Distribusi Spasial Grid GSMaP")
    hover_list = [actual_ch]
    if actual_sh_pct:
        hover_list += [actual_sh_pct, 'sifat_hujan_kategori']
    if actual_anom:
        hover_list.append(actual_anom)

    fig_map = px.scatter_mapbox(
        df_filtered,
        lat=actual_lat,
        lon=actual_lon,
        color=actual_ch,
        color_continuous_scale=px.colors.sequential.Jet,
        hover_data=hover_list,
        zoom=7,
        height=600
    )
    fig_map.update_traces(marker=dict(size=6))
    fig_map.update_layout(mapbox_style="open-street-map", margin={"r":0, "t":0, "l":0, "b":0})
    st.plotly_chart(fig_map, use_container_width=True)

    st.markdown("---")

    chart_col1, chart_col2 = st.columns(2)
    with chart_col1:
        st.subheader("📊 Grafik Distribusi Nilai Curah Hujan (Box Plot)")
        fig_box = px.box(
            df_filtered,
            y=actual_ch,
            points="all",
            labels={actual_ch: 'Curah Hujan (mm)'},
            color_discrete_sequence=['#1f77b4']
        )
        st.plotly_chart(fig_box, use_container_width=True)

    with chart_col2:
        if actual_sh_pct:
            st.subheader("🍩 Proporsi Sifat Hujan BMKG")
            proporsi = df_filtered['sifat_hujan_kategori'].value_counts().reset_index()
            proporsi.columns = ['Kategori', 'Jumlah Grid']
            color_map = {"Normal (N)": "#2ca02c", "Atas Normal (AN)": "#1f77b4", "Bawah Normal (BN)": "#d62728"}
            fig_pie = px.pie(
                proporsi,
                values='Jumlah Grid',
                names='Kategori',
                hole=0.4,
                color='Kategori',
                color_discrete_map=color_map
            )
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.subheader("📊 Proporsi Data Grid")
            st.info("Kolom SH% tidak tersedia, jadi proporsi kategori BMKG tidak dapat ditampilkan.")

    st.markdown("---")

    trend_col, corr_col = st.columns(2)
    with trend_col:
        st.subheader("📈 Histogram Frekuensi Curah Hujan")
        fig_hist = px.histogram(
            df_filtered,
            x=actual_ch,
            nbins=30,
            marginal="rug",
            labels={actual_ch: 'Curah Hujan (mm)'},
            opacity=0.8,
            color_discrete_sequence=['#636efa']
        )
        st.plotly_chart(fig_hist, use_container_width=True)

    with corr_col:
        if actual_anom:
            st.subheader("🔍 Korelasi CH vs Anomali CH")
            fig_corr = px.scatter(
                df_filtered,
                x=actual_ch,
                y=actual_anom,
                color='sifat_hujan_kategori' if actual_sh_pct else None,
                labels={actual_ch:'Curah Hujan (mm)', actual_anom:'Anomali Curah Hujan'},
                color_discrete_sequence=px.colors.qualitative.Plotly
            )
            st.plotly_chart(fig_corr, use_container_width=True)
        else:
            st.info("Kolom 'anomch' tidak tersedia untuk menampilkan korelasi anomali.")

    st.markdown("---")

    profile_col1, profile_col2 = st.columns(2)
    with profile_col1:
        st.subheader("📍 Profil Barat-Timur")
        fig_west_east = px.scatter(
            df_filtered,
            x=actual_lon,
            y=actual_ch,
            labels={actual_lon:'Longitude', actual_ch:'Curah Hujan (mm)'},
            trendline='ols'
        )
        st.plotly_chart(fig_west_east, use_container_width=True)

    with profile_col2:
        st.subheader("📍 Profil Utara-Selatan")
        fig_north_south = px.scatter(
            df_filtered,
            x=actual_lat,
            y=actual_ch,
            labels={actual_lat:'Latitude', actual_ch:'Curah Hujan (mm)'},
            trendline='ols'
        )
        st.plotly_chart(fig_north_south, use_container_width=True)

    st.markdown("---")

    st.subheader("📋 DataFrame Final Hasil Filter")
    st.dataframe(df_filtered, use_container_width=True)

except Exception as e:
    st.error(f"❌ Terjadi kesalahan pemrosesan file: {str(e)}")
