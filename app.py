import streamlit as st
import pandas as pd
import google.generativeai as genai
import re

# --- 1. CONFIGURAZIONE INTERFACCIA (Layout Centered) ---
st.set_page_config(page_title="MTGA AI Builder 3.1", page_icon="🃏", layout="centered")

# Stile Arena: Dark Mode con accenti verdi
st.markdown("""
    <style>
    .main { background-color: #0e1117; color: white; }
    .stButton>button { 
        width: 100%; border-radius: 12px; height: 3.5em; 
        background-color: #28a745; color: white; font-weight: bold; border: none;
        box-shadow: 0px 4px 10px rgba(0,0,0,0.2);
    }
    div[data-testid="stMetricValue"] { color: #28a745; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CONNESSIONE AI (Fix 404 & Supporto 3.1) ---
def inizializza_ai():
    if "GEMINI_API_KEY" not in st.secrets:
        st.error("❌ Chiave API mancante nei Secrets!")
        return None, None
    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        # Cerchiamo i modelli disponibili per evitare il 404
        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        
        # Priorità: 3.1 Flash -> 3 Flash -> fallback su 1.5
        selected = next((m for m in models if "gemini-3.1-flash" in m), None)
        if not selected:
            selected = next((m for m in models if "gemini-3-flash" in m), models[0])
            
        return genai.GenerativeModel(selected), selected
    except Exception as e:
        st.error(f"Errore connessione AI: {e}")
        return None, None

model_ai, model_name = inizializza_ai()

# --- 3. DATI ARCHETIPI (Untapped.gg 2026) ---
META_ARCHETYPES = {
    "Standard": ["Golgari Midrange", "Azorius Control", "Boros Convoke", "Mono-Red Aggro", "Dimir Tempo", "Simic Artifacts"],
    "Explorer": ["Rakdos Vampires", "Izzet Phoenix", "Amalia Combo", "Mono-White Humans", "Azorius Control"],
    "Historic": ["Izzet Wizards", "Mono-Green Elves", "Rakdos Midrange", "Boros Energy"],
    "Brawl": ["Standard Brawl", "Historic Brawl (100 Carte)"]
}

# --- 4. LOGICA DI CALCOLO ---
def analizza_mazzo_ita(testo_mazzo, df_collezione):
    wc_necessarie = {"Common": 0, "Uncommon": 0, "Rare": 0, "Mythic": 0}
    dettaglio_mancanti = []
    
    # Estrazione righe: es "4 Tutore Illuminato"
    linee = re.findall(r"(\d+)\s+(.+)", testo_mazzo)
    for qta, nome_carta in linee:
        qta = int(qta)
        nome_carta = nome_carta.strip()
        
        # Match flessibile (case-insensitive e parziale)
        match = df_collezione[df_collezione['Name'].str.contains(nome_carta, case=False, na=False)]
        
        if not match.empty:
            possedute = match['Count'].iloc[0]
            rarita = match['Rarity'].iloc[0]
        else:
            possedute, rarita = 0, "Rare"

        mancanti = max(0, qta - possedute)
        if mancanti > 0:
            if rarita in wc_necessarie: wc_necessarie[rarita] += mancanti
            dettaglio_mancanti.append({"Carta": nome_carta, "Mancanti": mancanti, "Rarità": rarita})
            
    return wc_necessarie, dettaglio_mancanti

# --- 5. INTERFACCIA UTENTE ---
st.title("🃏 MTGA AI Builder 3.1")
st.write("Crea mazzi ottimizzati basati sulla tua collezione reale.")

if model_name:
    st.caption(f"🤖 Modello Attivo: **{model_name}**")

file = st.file_uploader("Carica il tuo file CSV (Italiano)", type="csv")

if file:
    df = pd.read_csv(file)
    df.columns = [c.strip() for c in df.columns]
    st.success(f"✅ Collezione caricata: {len(df)} carte trovate.")

    # Input Utente
    formato = st.selectbox("Formato", list(META_ARCHETYPES.keys()))
    archetipo = st.selectbox("Archetipo (Meta Untapped.gg)", META_ARCHETYPES[formato])
    colori = st.multiselect("Colori preferiti", ["White", "Blue", "Black", "Red", "Green"])

    if st.button("🚀 GENERA E ANALIZZA MAZZO"):
        # Campionamento collezione per contesto (Top 80 carte rare/mitiche)
        mie_carte = df[df['Count'] > 0].sort_values(by='Rarity', ascending=False).head(80)
        contesto = mie_carte[['Name', 'Count']].to_string(index=False)

        prompt = f"""
        Sei un Pro Player di Magic Arena. Crea un mazzo {formato} di tipo {archetipo} in ITALIANO.
        Colori: {', '.join(colori)}.
        
        REGOLE:
        1. Analizza attentamente la SINERGIA e la CURVA DI MANA.
        2. Rispondi SOLO con la lista esportabile MTGA (es: 4 Nome Carta).
        3. Usa NOMI IN ITALIANO.
        4. Priorità massima a queste carte che già possiedo:
        {contesto}
        """

        with st.spinner("L'AI sta consultando il meta e la tua collezione..."):
            try:
                risposta = model_ai.generate_content(prompt)
                lista_mazzo = risposta.text
                
                # Pulizia lista per il calcolo
                lista_clean = "\n".join([l for l in lista_mazzo.split('\n') if re.match(r'^\d+\s', l)])
                
                st.subheader("📋 Lista Mazzo (Italiano)")
                st.code(lista_clean, language="text")
                
                # Analisi Wildcards
                wcs, mancanti = analizza_mazzo_ita(lista_clean, df)
                
                st.divider()
                st.subheader("💰 Costo Wildcards")
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Comuni", wcs['Common'])
                c2.metric("Non Comuni", wcs['Uncommon'])
                c3.metric("Rare", wcs['Rare'])
                c4.metric("Mitiche", wcs['Mythic'])

                if mancanti:
                    with st.expander("🔎 Dettaglio carte mancanti"):
                        st.table(mancanti)
                else:
                    st.balloons()
                    st.success("Mazzo pronto! Hai tutte le carte necessarie.")
                    
            except Exception as e:
                st.error(f"Errore generazione: {e}")
else:
    st.info("Trascina qui il tuo CSV per iniziare.")
