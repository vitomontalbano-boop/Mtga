import streamlit as st
import pandas as pd
import google.generativeai as genai
import io

# 1. CONFIGURAZIONE PAGINA E AI
st.set_page_config(page_title="MTGA AI Deck Builder", page_icon="🃏", layout="centered")

# Recupero API Key dai Secrets di Streamlit
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-1.5-flash') # Versione veloce ed efficiente
except Exception as e:
    st.error("Configura la GEMINI_API_KEY nei Secrets di Streamlit per far funzionare l'AI.")

# Stile CSS per rendere l'interfaccia più "App" su Mobile
st.markdown("""
    <style>
    .main { background-color: #121212; color: #ffffff; }
    .stButton>button { width: 100%; border-radius: 10px; height: 3em; background-color: #ff4b4b; color: white; font-weight: bold; }
    .stSelectbox, .stRadio { background-color: #1e1e1e; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

# 2. FUNZIONE LOGICA: CALCOLO WILDCARDS
def calcola_mancanti(deck_text, df_collezione):
    wc_counts = {"Common": 0, "Uncommon": 0, "Rare": 0, "Mythic": 0}
    missing_list = []
    
    lines = deck_text.strip().split('\n')
    for line in lines:
        if not line or line[0].isalpha(): continue # Salta intestazioni tipo "Deck"
        try:
            parts = line.split(' ', 1)
            qty_needed = int(parts[0])
            card_name = parts[1].split('(')[0].strip() # Pulisce nomi tipo "Carta (SET) 123"
            
            # Cerca nel CSV (Case insensitive)
            match = df_collezione[df_collezione['Name'].str.lower() == card_name.lower()]
            
            if not match.empty:
                owned = match['Count'].values[0]
                rarity = match['Rarity'].values[0]
            else:
                owned = 0
                rarity = "Rare" # Default prudenziale se non trovata
            
            diff = max(0, qty_needed - owned)
            if diff > 0:
                if rarity in wc_counts: wc_counts[rarity] += diff
                missing_list.append({"Carta": card_name, "Mancanti": diff, "Rarità": rarity})
        except:
            continue
            
    return wc_counts, missing_list

# 3. INTERFACCIA UTENTE
st.title("🃏 MTGA AI Builder")
st.write("Crea mazzi basati sulla tua collezione reale.")

# Caricamento File
uploaded_file = st.file_uploader("Carica il tuo CSV di MTGA", type="csv")

if uploaded_file:
    # Lettura dati
    df = pd.read_csv(uploaded_file)
    st.success(f"Collezione caricata: {len(df)} carte trovate.")

    # Opzioni Mazzo
    col1, col2 = st.columns(2)
    with col1:
        formato = st.selectbox("Formato", ["Standard", "Brawl", "Explorer", "Alchemy", "Historic"])
    with col2:
        archetipo = st.selectbox("Archetipo", ["Aggro", "Control", "Midrange", "Combo", "Tempo"])

    colore = st.multiselect("Colori preferiti (opzionale)", ["White", "Blue", "Black", "Red", "Green"])

    # Pulsante Generazione
    if st.button("🚀 GENERA MAZZO OTTIMIZZATO"):
        # Filtriamo le carte Rare/Mitiche che l'utente ha già per dare spunti all'AI
        owned_top = df[(df['Count'] > 0) & (df['Rarity'].isin(['Rare', 'Mythic']))].sample(min(len(df), 50))
        lista_per_ai = owned_top[['Name', 'Rarity', 'Count']].to_string(index=False)

        prompt = f"""
        Sei un esperto di MTG Arena. Crea un mazzo {formato} di tipo {archetipo}.
        Colori richiesti: {', '.join(colore) if colore else 'Qualsiasi'}.
        
        Usa il più possibile queste carte che già possiedo:
        {lista_per_ai}
        
        Rispondi ESCLUSIVAMENTE con la lista nel formato ESPORTABILE di MTG Arena (es: 4 Nome Carta).
        Non aggiungere introduzioni o chiacchiere. Includi Terre Base necessarie.
        """

        with st.spinner("L'AI sta studiando la tua collezione..."):
            response = model.generate_content(prompt)
            deck_output = response.text
            
            # Mostra Risultato
            st.subheader("📋 Lista Mazzo")
            st.code(deck_output, language="text")

            # Calcolo Wildcards
            wcs, missing = calcola_mancanti(deck_output, df)
            
            st.divider()
            st.subheader("💰 Costo Wildcards")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("C", wcs['Common'])
            c2.metric("U", wcs['Uncommon'])
            c3.metric("R", wcs['Rare'])
            c4.metric("M", wcs['Mythic'])

            if missing:
                with st.expander("Dettaglio carte da creare"):
                    st.table(missing)
else:
    st.info("Trascina qui il file .csv esportato dal tuo tracker (Untapped, ecc.) per iniziare.")

st.markdown("---")
st.caption("Creato con ❤️ per i giocatori di MTG Arena.")
