import streamlit as st
import pandas as pd
import google.generativeai as genai
import re

# 1. CONFIGURAZIONE PAGINA E STILE MOBILE-FIRST
st.set_page_config(page_title="MTGA AI Builder", page_icon="🃏", layout="centered")

st.markdown("""
    <style>
    .main { background-color: #0e1117; color: #ffffff; }
    .stButton>button { 
        width: 100%; 
        border-radius: 12px; 
        height: 3.5em; 
        background-color: #ff4b4b; 
        color: white; 
        font-weight: bold;
        border: none;
        box-shadow: 0px 4px 10px rgba(0,0,0,0.3);
    }
    .stSelectbox, .stRadio, .stMultiSelect { 
        background-color: #1e1e1e; 
        border-radius: 8px; 
    }
    div[data-testid="stMetricValue"] { font-size: 1.8rem; color: #ff4b4b; }
    </style>
    """, unsafe_allow_html=True)

# 2. INIZIALIZZAZIONE AI (GEMINI 3 FLASH - 2026)
try:
    if "GEMINI_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        # Utilizziamo il modello più aggiornato del 2026
        model = genai.GenerativeModel('gemini-3-flash')
    else:
        st.warning("⚠️ API Key non trovata nei Secrets di Streamlit.")
except Exception as e:
    st.error(f"Errore inizializzazione AI: {e}")

# 3. FUNZIONI DI SUPPORTO
def pulisci_nome_carta(nome_raw):
    """Rimuove set e numeri di collezione (es: 'Sheoldred (DMU) 107' -> 'Sheoldred')"""
    return re.sub(r'\s\(.*?\)\s\d+|\s\(.*?\)', '', nome_raw).strip()

def calcola_wildcards(deck_text, df_collezione):
    wc_necessarie = {"Common": 0, "Uncommon": 0, "Rare": 0, "Mythic": 0}
    mancanti_dettaglio = []
    
    linee = deck_text.strip().split('\n')
    for linea in linee:
        linea = linea.strip()
        if not linea or not linea[0].isdigit(): continue
        
        try:
            parti = linea.split(' ', 1)
            qta_richiesta = int(parti[0])
            nome_full = parti[1]
            nome_pulito = pulisci_nome_carta(nome_full)
            
            # Cerca nel CSV (Case Insensitive)
            match = df_collezione[df_collezione['Name'].str.lower() == nome_pulito.lower()]
            
            if not match.empty:
                possedute = match['Count'].iloc[0]
                rarita = match['Rarity'].iloc[0]
            else:
                possedute = 0
                rarita = "Rare" # Default se non trovata nel CSV

            diff = max(0, qta_richiesta - possedute)
            if diff > 0:
                if rarita in wc_necessarie:
                    wc_necessarie[rarita] += diff
                mancanti_dettaglio.append({
                    "Carta": nome_pulito, 
                    "Mancanti": diff, 
                    "Rarità": rarita
                })
        except Exception:
            continue
            
    return wc_necessarie, mancanti_dettaglio

# 4. INTERFACCIA UTENTE (UI)
st.title("🃏 MTGA AI Builder")
st.caption("Il tuo Lead Developer personale per scalare la Mythic Rank.")

uploaded_file = st.file_uploader("📤 Carica la tua collezione (file .csv)", type="csv")

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    st.success(f"Analizzate {len(df)} carte della tua collezione.")

    # Opzioni di Creazione
    with st.container():
        formato = st.selectbox("Formato di Gioco", ["Standard", "Brawl", "Explorer", "Historic", "Alchemy"])
        archetipo = st.select_slider("Stile del Mazzo", options=["Aggro", "Tempo", "Midrange", "Control", "Combo"])
        colori = st.multiselect("Colori preferiti", ["White", "Blue", "Black", "Red", "Green"])

    if st.button("🚀 GENERA E CALCOLA COSTO"):
        # Selezioniamo un campione delle tue Rare/Mitiche per guidare l'AI
        rare_possedute = df[(df['Count'] > 0) & (df['Rarity'].isin(['Rare', 'Mythic']))].sample(min(80, len(df[df['Count']>0])))
