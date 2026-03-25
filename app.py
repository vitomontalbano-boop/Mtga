import streamlit as st
import pandas as pd
import google.generativeai as genai
import re

# --- 1. CONFIGURAZIONE INTERFACCIA (Ripristino Layout Originale) ---
st.set_page_config(page_title="MTGA AI Builder 3.1", page_icon="🃏", layout="centered")

# CSS personalizzato: Dark Mode Arena
st.markdown("""
    <style>
    .main { background-color: #0e1117; color: white; }
    .stButton>button { 
        width: 100%; border-radius: 12px; height: 3.5em; 
        background-color: #28a745; color: white; font-weight: bold; border: none;
        box-shadow: 0px 4px 10px rgba(0,0,0,0.2);
    }
    div[data-testid="stMetricValue"] { color: #28a745; }
    .stSelectbox, .stMultiSelect { color: white; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CONNESSIONE AI (Gemini 3 Flash) ---
def inizializza_ai():
    if "GEMINI_API_KEY" not in st.secrets:
        st.error("❌ Chiave API mancante!")
        return None
    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        # Utilizzo del modello richiesto
        return genai.GenerativeModel("gemini-3-flash")
    except Exception as e:
        st.error(f"Errore di connessione: {e}")
        return None

model_ai = inizializza_ai()

# --- 3. DATI ARCHETIPI (Sync Untapped.gg 2026) ---
META_DATA = {
    "Standard": ["Golgari Midrange", "Azorius Control", "Mono-Red Aggro", "Boros Convoke", "Dimir Tempo", "Simic Artifacts"],
    "Explorer": ["Rakdos Vampires", "Izzet Phoenix", "Amalia Combo", "Azorius Control", "Abzan Greasefang"],
    "Historic": ["Izzet Wizards", "Mono-Green Devotion", "Sultai Yawgmoth", "Boros Energy"],
    "Brawl": ["Standard Brawl", "Historic Brawl (100 Cards)"],
    "Alchemy": ["Heist Control", "Mono-White Lifegain"]
}

# --- 4. LOGICA DI ANALISI ---
def analizza_mazzo_ita(testo_mazzo, df_collezione):
    wc_necessarie = {"Common": 0, "Uncommon": 0, "Rare": 0, "Mythic": 0}
    dettaglio_mancanti = []
    
    # Regex per catturare "Quantità NomeCarta"
    linee = re.findall(r"(\d+)\s+(.+)", testo_mazzo)
    for qta_str, nome_carta in linee:
        qta_richiesta = int(qta_str)
        nome_carta = nome_carta.strip()
        
        # Match flessibile nel CSV
        match = df_collezione[df_collezione['Name'].str.contains(nome_carta, case=False, na=False)]
        
        if not match.empty:
            possedute = match['Count'].iloc[0]
            rarita = match['Rarity'].iloc[0]
        else:
            possedute, rarita = 0, "Rare" # Default cautelativo

        mancanti = max(0, qta_richiesta - possedute)
        if mancanti > 0:
            if rarita in wc_necessarie: wc_necessarie[rarita] += mancanti
            dettaglio_mancanti.append({"Carta": nome_carta, "Mancanti": mancanti, "Rarità": rarita})
            
    return wc_necessarie, dettaglio_mancanti

# --- 5. INTERFACCIA UTENTE ---
st.title("🃏 MTGA AI Builder 3.1")
st.write("Generatore di mazzi basato sul meta di **Untapped.gg** e la tua collezione.")

file = st.file_uploader("Carica il tuo export CSV", type="csv")

if file:
    df = pd.read_csv(file)
    df.columns = [c.strip() for c in df.columns] # Pulizia nomi colonne
    st.success(f"✅ Collezione caricata con successo.")

    # Selettori Archetipo e Colori
    formato = st.selectbox("Seleziona Formato", list(META_DATA.keys()))
    archetipo = st.selectbox("Archetipo (Meta Untapped.gg)", META_DATA[formato])
    colori = st.multiselect("Colori del Mazzo", ["White", "Blue", "Black", "Red", "Green"])

    if st.button("🚀 GENERA E ANALIZZA MAZZO"):
        # Campionamento collezione per contesto (Priorità Rare/Mitiche)
        mie_carte = df[df['Count'] > 0].sort_values(by='Rarity', ascending=False).head(80)
        contesto = mie_carte[['Name', 'Count']].to_string(index=False)

        prompt = f"""
        Sei un Pro Player di MTG Arena. Crea un mazzo {formato} di tipo {archetipo}.
        Colori richiesti: {', '.join(colori)}.
        
        REGOLE FONDAMENTALI:
        1. ANALISI: Controlla gli effetti delle carte, il costo di mana (CMC) e la SINERGIA complessiva.
        2. LISTA: Fornisci SOLO la lista esportabile MTGA (es: 4 Nome Carta).
        3. LINGUA: Usa esclusivamente i nomi delle carte in ITALIANO.
        4. OTTIMIZZAZIONE: Usa il più possibile queste carte che possiedo:
        {contesto}
        """

        with st.spinner("L'AI sta assemblando il mazzo perfetto..."):
            try:
                risposta = model_ai.generate_content(prompt)
                testo_output = risposta.text
                
                # Pulizia testo per estrarre solo la lista
                lista_clean = "\n".join([l for l in testo_output.split('\n') if re.match(r'^\d+\s', l)])
                
                st.subheader("📋 Lista Mazzo Esportabile")
                st.code(lista_clean, language="text")
                
                # Analisi Wildcards
                wcs, mancanti = analizza_mazzo_ita(lista_clean, df)
                
                st.divider()
                st.subheader("💰 Bilancio Wildcards")
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Comuni", wcs['Common'])
                c2.metric("Non Comuni", wcs['Uncommon'])
                c3.metric("Rare", wcs['Rare'])
                c4.metric("Mitiche", wcs['Mythic'])

                if mancanti:
                    with st.expander("🔎 Dettaglio carte da craftare"):
                        st.table(mancanti)
                else:
                    st.balloons()
                    st.success("Ottimo! Hai tutte le carte per questo mazzo.")
                    
            except Exception as e:
                st.error(f"Errore nella generazione: {e}")
else:
    st.info("Trascina il tuo CSV per iniziare l'analisi personalizzata.")

st.divider()
st.caption("Powered by Gemini 3 Flash | Data based on Untapped.gg Meta 2026")
