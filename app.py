import streamlit as st
import pandas as pd
import google.generativeai as genai
import re

# --- 1. CONFIGURAZIONE INTERFACCIA ---
st.set_page_config(page_title="MTGA Deck Builder ITA", page_icon="🃏", layout="centered")

# Stile scuro con accenti verdi (stile Arena)
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

# --- 2. CONNESSIONE AI ---
def inizializza_ai():
    if "GEMINI_API_KEY" not in st.secrets:
        st.error("❌ Chiave API mancante nei Secrets di Streamlit!")
        return None, None
    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        # Cerchiamo il modello più recente
        selected = next((m for m in models if "gemini-3-flash" in m), models[0])
        return genai.GenerativeModel(selected), selected
    except Exception as e:
        st.error(f"Errore di connessione AI: {e}")
        return None, None

model_ai, model_name = inizializza_ai()

# --- 3. LOGICA DI CALCOLO (MATCH ITALIANO-ITALIANO) ---
def analizza_mazzo_ita(testo_mazzo, df_collezione):
    wc_necessarie = {"Common": 0, "Uncommon": 0, "Rare": 0, "Mythic": 0}
    dettaglio_mancanti = []
    
    linee = testo_mazzo.strip().split('\n')
    for linea in linee:
        linea = linea.strip()
        # Salta le linee che non iniziano con un numero (es. intestazioni "Mazzo")
        if not linea or not linea[0].isdigit(): continue
        
        try:
            # Esempio riga: "4 Tutore Illuminato"
            parti = linea.split(' ', 1)
            qta_richiesta = int(parti[0])
            nome_carta = parti[1].strip()
            
            # Cerchiamo il match nel CSV (colonna 'Name')
            match = df_collezione[df_collezione['Name'].str.lower() == nome_carta.lower()]
            
            if not match.empty:
                possedute = match['Count'].iloc[0]
                rarita = match['Rarity'].iloc[0]
            else:
                # Se la carta non è nel CSV, assumiamo sia una rara da creare
                possedute, rarita = 0, "Rare"

            mancanti = max(0, qta_richiesta - possedute)
            if mancanti > 0:
                if rarita in wc_necessarie: wc_necessarie[rarita] += mancanti
                dettaglio_mancanti.append({
                    "Carta": nome_carta, 
                    "Mancanti": mancanti, 
                    "Rarità": rarita
                })
        except:
            continue
            
    return wc_necessarie, dettaglio_mancanti

# --- 4. INTERFACCIA UTENTE ---
st.title("🃏 MTGA AI Builder")
st.write("Genera mazzi in italiano basati sulla tua collezione reale.")

if model_name:
    st.caption(f"🤖 Motore AI: {model_name}")

file = st.file_uploader("Carica il tuo CSV in italiano", type="csv")

if file:
    df = pd.read_csv(file)
    st.success(f"✅ Collezione caricata: {len(df)} carte trovate.")

    col1, col2 = st.columns(2)
    with col1:
        formato = st.selectbox("Formato", ["Standard", "Brawl", "Explorer", "Historic", "Alchemy"])
    with col2:
        archetipo = st.selectbox("Archetipo", ["Aggro", "Control", "Midrange", "Combo", "Tempo"])

    colori = st.multiselect("Colori preferiti", ["White", "Blue", "Black", "Red", "Green"])

    if st.button("🚀 GENERA E ANALIZZA MAZZO"):
        # Selezioniamo alcune carte Rare/Mitiche dal tuo CSV per ispirare l'AI
        mie_carte = df[(df['Count'] > 0) & (df['Rarity'].isin(['Rare', 'Mythic']))].sample(min(80, len(df[df['Count']>0])))
        contesto = mie_carte[['Name', 'Count']].to_string(index=False)

        prompt = f"""
        Sei un Pro Player di Magic Arena. Crea un mazzo {formato} di tipo {archetipo} in ITALIANO.
        Usa il più possibile queste carte che già possiedo nella mia collezione:
        {contesto}
        
        REGOLE:
        1. Rispondi SOLO con la lista esportabile in formato MTGA (es: 4 Nome Carta).
        2. Usa ESCLUSIVAMENTE i nomi delle carte in italiano.
        3. Includi le terre base necessarie.
        """

        with st.spinner("L'AI sta consultando la tua collezione..."):
            try:
                risposta = model_ai.generate_content(prompt)
                lista_mazzo = risposta.text
                
                # Mostriamo la lista
                st.subheader("📋 Lista Mazzo (Italiano)")
                st.code(lista_mazzo, language="text")
                
                # Calcoliamo i costi
                wcs, mancanti = analizza_mazzo_ita(lista_mazzo, df)
                
                st.divider()
                st.subheader("💰 Costo in Wildcards")
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
                    st.success("Mazzo pronto al 100%! Non devi spendere Wildcards.")
                    
            except Exception as e:
                st.error(f"Errore durante la generazione: {e}")
else:
    st.info("Trascina qui il tuo file CSV per iniziare.")
