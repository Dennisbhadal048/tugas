import streamlit as st
import pandas as pd
import plotly.express as px

# 1. Konfigurasi Halaman Utama Dashboard
st.set_page_config(
    page_title="GSMaP Blend Rainfall Dashboard",
    page_icon="🛰️",
    layout="wide"
)

st.title("🛰️ Dashboard Grid Data Blend GSMaP")
st.markdown("Aplikasi visualisasi data spasial iklim berbasis grid dari satelit GSMaP Blending.")
st.markdown("---")

# 2. Fungsi Mengambil Data (.xls / .xlsx / .csv)
@st.cache_data
def load_gsmap_data(file, file_extension):
    if file_extension == 'csv':
        df = pd.read_csv(file)
    else:
        df = pd.read_excel(file)
        
    # Standardisasi nama kolom (menghilangkan spasi & huruf kecil)
    df.columns = df.columns.str.strip().str.lower()
    return df

# Fungsi untuk mengategorikan Sifat Hujan berdasarkan standar BMKG (dari nilai persen)
def klasifikasi_sifat_hujan(persen):
    if persen < 85:
        return "Bawah Normal (BN)"
    elif 85 <= persen <= 115:
        return "Normal (N)"
    else:
        return "Atas Normal (AN)"

# 3. SIDEBAR PANEL: Tempat Upload & Filter
st.sidebar.header("📋 Pengaturan & Filter")

uploaded_file = st.sidebar.file_uploader(
    "Unggah File Blend GSMaP (.xls, .xlsx, .csv)", 
    type=["xls", "xlsx", "csv"]
)

if not uploaded_file:
    st.warning("⚠️ Silakan unggah file data Blend GSMaP Anda pada sidebar di sebelah kiri untuk menampilkan visualisasi.")
else:
    file_ext = uploaded_file.name.split('.')[-1].lower()
    
    try:
        df_raw = load_gsmap_data(uploaded_file, file_ext)
        
        # Pemetaan nama kolom sesuai file kamu (lon, lat, ch, sh%, anomch)
        # Menangani variasi kolom persen 'sh%' atau 'shpercent'
        actual_lon = 'lon' if 'lon' in df_raw.columns else None
        actual_lat = 'lat' if 'lat' in df_raw.columns else None
        actual_ch = 'ch' if 'ch' in df_raw.columns else None
        actual_sh_pct = 'sh%' if 'sh%' in df_raw.columns else ('shpercent' if 'shpercent' in df_raw.columns else None)
        actual_anom = 'anomch' if 'anomch' in df_raw.columns else None

        # Validasi kolom krusial
        if not (actual_lon and actual_lat and actual_ch):
            st.error("❌ Struktur kolom tidak sesuai! Pastikan file memiliki kolom: LON, LAT, dan CH.")
            st.stop()

        # Pembersihan tipe data ke numerik & buang baris kosong
        for col in [actual_lon, actual_lat, actual_ch]:
            df_raw[col] = pd.to_numeric(df_raw[col], errors='coerce')
        
        if actual_sh_pct:
            df_raw[actual_sh_pct] = pd.to_numeric(df_raw[actual_sh_pct], errors='coerce')
            # Membuat kolom kategori baru 'sifat_hujan_kategori' berdasarkan nilai persennya
            df_raw['sifat_hujan_kategori'] = df_raw[actual_sh_pct].apply(klasifikasi_sifat_hujan)
            
        df_clean = df_raw.dropna(subset=[actual_lon, actual_lat, actual_ch]).reset_index(drop=True)

        # --- FITUR FILTER DATA ---
        st.sidebar.markdown("### Filter Nilai Parameter")
        
        # Filter 1: Range Curah Hujan (CH)
        min_ch = float(df_clean[actual_ch].min())
        max_ch = float(df_clean[actual_ch].max())
        
        slider_ch = st.sidebar.slider(
            "Range Curah Hujan (mm):",
            min_value=min_ch,
            max_value=max_ch,
            value=(min_ch, max_ch)
        )
        
        # Terapkan filter CH
        df_filtered = df_clean[
            (df_clean[actual_ch] >= slider_ch[0]) & 
            (df_clean[actual_ch] <= slider_ch[1])
        ]
        
        # Filter 2: Berdasarkan Kategori Sifat Hujan (jika ada data persentasenya)
        if actual_sh_pct:
            list_kategori = sorted(df_filtered['sifat_hujan_kategori'].unique())
            selected_kategori = st.sidebar.multiselect(
                "Pilih Kategori Sifat Hujan:", 
                list_kategori, 
                default=list_kategori
            )
            df_filtered = df_filtered[df_filtered['sifat_hujan_kategori'].isin(selected_kategori)]

        if df_filtered.empty:
            st.warning("⚠️ Tidak ada data grid yang cocok dengan filter Anda.")
            st.stop()

        # 4. MAIN PAGE: Row 1 - KPI Cards (Statistik Deskriptif Grid)
        kpi1, kpi2, kpi3 = st.columns(3)
        
        total_grid = len(df_filtered)
        rerata_ch = df_filtered[actual_ch].mean()
        max_val_ch = df_filtered[actual_ch].max()
        
        # Mencari koordinat dengan curah hujan tertinggi
        idx_max = df_filtered[actual_ch].idxmax()
        coord_max = f"({df_filtered.loc[idx_max, actual_lat]}, {df_filtered.loc[idx_max, actual_lon]})"

        with kpi1:
            st.metric(label="Total Titik Grid Teranalisis", value=f"{total_grid} Titik")
        with kpi2:
            st.metric(label="Rata-rata Curah Hujan Grid", value=f"{rerata_ch:.2f} mm")
        with kpi3:
            st.metric(label="Curah Hujan Maksimum", value=f"{max_val_ch:.2f} mm", delta=f"Koordinat: {coord_max}", delta_color="inverse")

        st.markdown("---")

        # 5. MAIN PAGE: Row 2 - Peta Grid Geospasial
        st.subheader("🗺️ Peta Distribusi Spasial Grid GSMaP")
        
        # Hover data yang ditampilkan saat kursor menunjuk titik di peta
        hover_list = [actual_ch]
        if actual_sh_pct:
            hover_list.append(actual_sh_pct)
            hover_list.append('sifat_hujan_kategori')
        if actual_anom:
            hover_list.append(actual_anom)

        # Menggunakan scatter_mapbox untuk memplot data grid berdasarkan koordinatnya
        fig_map = px.scatter_mapbox(
            df_filtered,
            lat=actual_lat,
            lon=actual_lon,
            size=actual_ch,
            color=actual_ch,  # Gradasi warna berdasarkan tinggi rendahnya curah hujan
            color_continuous_scale=px.colors.sequential.Jet,
            hover_data=hover_list,
            zoom=7,
            height=600
        )
        
        fig_map.update_layout(mapbox_style="open-street-map")
        fig_map.update_layout(margin={"r":0, "t":0, "l":0, "b":0})
        st.plotly_chart(fig_map, use_container_width=True)
        
        st.markdown("---")

        # 6. MAIN PAGE: Row 3 - Analisis Grafik Distribusi
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
                
                # Pemetaan warna khusus agar representatif (Normal = Hijau, dll)
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
                st.subheader("📊 Grafik Anomali Curah Hujan")
                if actual_anom:
                    fig_anom = px.histogram(
                        df_filtered, 
                        x=actual_anom, 
                        nbins=20,
                        color_discrete_sequence=['#ff7f0e'],
                        labels={actual_anom: 'Nilai Anomali'}
                    )
                    st.plotly_chart(fig_anom, use_container_width=True)
                else:
                    st.info("Kolom SH% atau Anomali tidak ditemukan untuk membuat grafik sekunder.")

        st.markdown("---")

        # 7. MAIN PAGE: Row 4 - Tabel Data Grid Mentah
        st.subheader("📋 Tabel Data Grid Terfilter")
        st.dataframe(df_filtered, use_container_width=True)

    except Exception as e:
        st.error(f"❌ Terjadi kesalahan pemrosesan file: {str(e)}")