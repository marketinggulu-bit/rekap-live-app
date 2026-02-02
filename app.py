import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime
import plotly.express as px

# --- CONFIGURASI GOOGLE SHEETS (VERSI ONLINE KEBAL ERROR) ---
scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

if "gcp_service_account" in st.secrets:
    # Kita bersihkan private_key dari karakter \n yang suka bikin error
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
    creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
else:
    # Cadangan kalau di laptop
    creds = Credentials.from_service_account_file("credentials.json", scopes=scope)

client = gspread.authorize(creds)
SHEET_NAME = "Rekap Live"
spreadsheet = client.open(SHEET_NAME)
worksheet_data = spreadsheet.worksheet("Data")
worksheet_setup = spreadsheet.worksheet("Setup")

# --- UI ESTETIK GEN Z ---
st.set_page_config(page_title="Rekap Live ✨", layout="wide")

st.markdown("""
    <style>
    .main { background: linear-gradient(to bottom right, #FFF0F5, #E6E6FA); }
    .stButton>button { 
        background: linear-gradient(to right, #FF69B4, #DA70D6); 
        color: white; border-radius: 20px; border: none; font-weight: bold;
    }
    .stMetric { background-color: white; padding: 20px; border-radius: 20px; border-left: 5px solid #FF69B4; }
    h1, h2, h3 { color: #C71585; text-align: center; }
    .host-card { background-color: #FFD1DC; padding: 10px 20px; border-radius: 15px; color: #C71585; font-weight: bold; margin: 5px; }
    .shop-card { background-color: #E0B0FF; padding: 10px 20px; border-radius: 15px; color: #4B0082; font-weight: bold; margin: 5px; }
    .card-container { display: flex; flex-wrap: wrap; justify-content: center; }
    </style>
    """, unsafe_allow_html=True)

st.sidebar.title("🎀 Menu ")
menu = st.sidebar.radio("Pilih Halaman:", ["🌸 Dashboard", "✍️ Input Live", "⚙️ Setup System"])

# --- MENU 1: DASHBOARD (MULTI-FILTER TIME RANGE) ---
if menu == "🌸 Dashboard":
    st.markdown("<h1 style='text-align: center; color: #FF1493;'>Live Performance Dashboard</h1>", unsafe_allow_html=True)
    
    raw_data = worksheet_data.get_all_records()
    if raw_data:
        df = pd.DataFrame(raw_data)
        df['Tanggal'] = pd.to_datetime(df['Tanggal']).dt.date
        today = datetime.now().date()
        
        # --- SEKSI FILTER WAKTU & DATA ---
        col_f1, col_f2, col_f3 = st.columns(3)
        
        with col_f1:
            # Menambahkan pilihan "Bulan Lalu"
            rentang = st.selectbox("📅 Rentang Waktu", ["Hari Ini", "7 Hari Terakhir", "Bulan Ini", "Bulan Lalu", "Custom"])
            
            if rentang == "Hari Ini":
                start_date, end_date = today, today
            elif rentang == "7 Hari Terakhir":
                start_date, end_date = today - pd.Timedelta(days=7), today
            elif rentang == "Bulan Ini":
                start_date = today.replace(day=1)
                end_date = today
            elif rentang == "Bulan Lalu":
                # Logika mengambil awal dan akhir bulan kemarin
                first_this_month = today.replace(day=1)
                end_date = first_this_month - pd.Timedelta(days=1)
                start_date = end_date.replace(day=1)
            else:
                # JIKA PILIH CUSTOM: Munculkan pilihan tanggal mulai dan selesai
                col_c1, col_c2 = st.columns(2)
                start_date = col_c1.date_input("Dari", today - pd.Timedelta(days=30))
                end_date = col_c2.date_input("Sampai", today)
        
        with col_f2:
            user_f = st.selectbox("👤 Pilih User", ["Semua User"] + sorted(list(df['Nama'].unique())))
        with col_f3:
            toko_f = st.selectbox("🛍️ Pilih Toko", ["Semua Toko"] + sorted(list(df['Toko'].unique())))
        
        # --- LOGIKA FILTER DATA ---
        mask = (df['Tanggal'] >= start_date) & (df['Tanggal'] <= end_date)
        df_filtered = df.loc[mask]
        
        if user_f != "Semua User": 
            df_filtered = df_filtered[df_filtered['Nama'] == user_f]
        if toko_f != "Semua Toko": 
            df_filtered = df_filtered[df_filtered['Toko'] == toko_f]

        # --- SEKSI GRAFIK TREN (MENGIKUTI FILTER) ---
        st.write("---")
        st.markdown(f"<h3 style='text-align: center; color: #DB7093;'>📈 Tren Omset per Toko ({rentang})</h3>", unsafe_allow_html=True)
        
        if not df_filtered.empty:
            # Akumulasi Omset per Toko per Tanggal sesuai filter
            df_trend = df_filtered.groupby(['Tanggal', 'Toko'])['Omset'].sum().reset_index()
            fig_trend = px.line(df_trend, x='Tanggal', y='Omset', color='Toko',
                                markers=True, color_discrete_sequence=px.colors.qualitative.Pastel)
            
            fig_trend.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_trend, use_container_width=True)
        else:
            st.warning("Tidak ada data untuk rentang waktu ini. ✨")
            
        st.write("---")
        
        # --- SEKSI SUMMARY (TOTAL SESUAI FILTER) ---
        st.markdown(f"<h4 style='text-align: center; color: #FF69B4;'>Total Rekap: {start_date} s/d {end_date}</h4>", unsafe_allow_html=True)
        m1, m2, m3 = st.columns(3)
        m1.metric("💰 Total Omset", f"Rp {df_filtered['Omset'].sum():,}")
        m2.metric("🎬 Total Video", f"{df_filtered['Total Video'].sum()}")
        m3.metric("📈 Total Sesi", len(df_filtered))

        # --- SEKSI TOP 3 PERFORMANCE ---
        st.write("---")
        if not df_filtered.empty:
            col_top3_a, col_top3_b = st.columns(2)
            with col_top3_a:
                st.markdown("<h3 style='text-align: center; color: #FF69B4;'>🥇 Top 3 User</h3>", unsafe_allow_html=True)
                top3_user = df_filtered.groupby('Nama')['Omset'].sum().sort_values(ascending=False).head(3)
                for i, (nama, total) in enumerate(top3_user.items(), 1):
                    medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉"
                    st.markdown(f"""
                        <div style="background-color: white; padding: 15px 20px; border-radius: 15px; border-left: 10px solid #FF69B4; margin-bottom: 10px; box-shadow: 2px 2px 10px rgba(0,0,0,0.05); display: flex; justify-content: space-between; align-items: center;">
                            <span style="font-weight: bold; color: #C71585;">{medal} {i}. {nama}</span>
                            <span style="color: #FF1493; font-weight: bold;">Rp {total:,.0f}</span>
                        </div>
                    """, unsafe_allow_html=True)

            with col_top3_b:
                st.markdown("<h3 style='text-align: center; color: #9370DB;'>🏆 Top 3 Toko</h3>", unsafe_allow_html=True)
                top3_toko = df_filtered.groupby('Toko')['Omset'].sum().sort_values(ascending=False).head(3)
                for i, (toko, total) in enumerate(top3_toko.items(), 1):
                    medal_t = "⭐" if i == 1 else "✨" if i == 2 else "💫"
                    st.markdown(f"""
                        <div style="background-color: white; padding: 15px 20px; border-radius: 15px; border-left: 10px solid #9370DB; margin-bottom: 10px; box-shadow: 2px 2px 10px rgba(0,0,0,0.05); display: flex; justify-content: space-between; align-items: center;">
                            <span style="font-weight: bold; color: #4B0082;">{medal_t} {i}. {toko}</span>
                            <span style="color: #6A5ACD; font-weight: bold;">Rp {total:,.0f}</span>
                        </div>
                    """, unsafe_allow_html=True)

# --- MENU 2: INPUT LIVE (CLEAN & CANTIK) ---
elif menu == "✍️ Input Live":
    # Header langsung rapi di tengah
    st.markdown("<h1 style='text-align: center; color: #FF1493; margin-bottom: 20px;'>Catat Rekap Live Hari Ini</h1>", unsafe_allow_html=True)
    
    # CSS minimalis untuk menghilangkan kotak kosong di atas form
    st.markdown("""
        <style>
        div.stForm {
            background: linear-gradient(135deg, #FFF0F5 0%, #F0F8FF 100%);
            padding: 30px;
            border-radius: 30px;
            border: 3px solid #FFB6C1;
            box-shadow: 10px 10px 20px rgba(255, 182, 193, 0.3);
        }
        .stSelectbox label, .stNumberInput label {
            color: #C71585 !important;
            font-weight: bold !important;
        }
        </style>
    """, unsafe_allow_html=True)

    # Ambil data terbaru dari GSheet
    users = [u for u in worksheet_setup.col_values(1)[1:] if u]
    shops = [s for s in worksheet_setup.col_values(2)[1:] if s]
    
    if users and shops:
        # Langsung masuk ke Form tanpa <div> tambahan di atasnya
        with st.form("input_form_baru", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                nama_input = st.selectbox("👱‍♀️ Siapa yang Live?", users)
            with col2:
                toko_input = st.selectbox("🛍️ Di Toko Mana?", shops)
            
            st.write("---")
            
            c_a, c_b = st.columns(2)
            with c_a:
                durasi = st.number_input("⏱️ Durasi Live (Menit)", min_value=1, value=1)
            with c_b:
                omset = st.number_input("💰 Omset didapat (Rp)", min_value=0, value=0, step=50000)
            
            video = st.number_input("🎬 Total Video Dibuat", min_value=0, value=0)
            
            st.write("")
            submit_btn = st.form_submit_button("SIMPAN REKAP SEKARANG 💖")
            
            if submit_btn:
                tgl_skrg = datetime.now().strftime("%Y-%m-%d")
                worksheet_data.append_row([tgl_skrg, nama_input, toko_input, durasi, omset, video])
                st.balloons()
                st.snow()
                st.success(f"Berhasil disimpan! Form otomatis kereset ya sis! ✨")
    else:
        st.warning("Isi data Host & Toko dulu di menu Setup System ya! 🥺")

# --- MENU 3: SETUP SYSTEM ---
elif menu == "⚙️ Setup System":
    st.header("Pengaturan Data")
    col_a, col_b = st.columns(2)
    with col_a:
        with st.form("add_user", clear_on_submit=True):
            st.subheader("👱‍♀️ Tambah Host")
            new_u = st.text_input("Nama Host:", placeholder="Sarah ✨", label_visibility="collapsed")
            if st.form_submit_button("Simpan Host 💖") and new_u:
                worksheet_setup.append_row([new_u])
                st.toast("Host added!")
                
    with col_b:
        with st.form("add_toko", clear_on_submit=True):
            st.subheader("🏪 Tambah Toko")
            new_t = st.text_input("Nama Toko:", placeholder="Official Shop 🛍️", label_visibility="collapsed")
            if st.form_submit_button("Simpan Toko 🛍️") and new_t:
                col_t = worksheet_setup.col_values(2)
                worksheet_setup.update_cell(len(col_t) + 1, 2, new_t)
                st.toast("Toko added!")

    st.write("---")
    c_list1, c_list2 = st.columns(2)
    with c_list1:
        st.markdown("<h3>👱‍♀️ Tim Host</h3>", unsafe_allow_html=True)
        u_list = [u for u in worksheet_setup.col_values(1)[1:] if u]
        html_u = '<div class="card-container">' + "".join([f'<div class="host-card">{i}. {n} ✨</div>' for i, n in enumerate(u_list, 1)]) + '</div>'
        st.markdown(html_u, unsafe_allow_html=True)
    with c_list2:
        st.markdown("<h3>🏪 Daftar Toko</h3>", unsafe_allow_html=True)
        s_list = [s for s in worksheet_setup.col_values(2)[1:] if s]
        html_s = '<div class="card-container">' + "".join([f'<div class="shop-card">{i}. {s} 🛍️</div>' for i, s in enumerate(s_list, 1)]) + '</div>'

        st.markdown(html_s, unsafe_allow_html=True)



