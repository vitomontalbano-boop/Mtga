import streamlit as st
import pandas as pd
import google.generativeai as genai
import re

# --- 1. CONFIGURAZIONE INTERFACCIA ---
st.set_page_config(page_title="MTGA AI Builder", page_icon="🃏", layout="centered")

# Style CSS per Android (Dark Mode e Bottoni Grandi)
st.markdown("""
    <style>
    .main { background-color: #0e1117; color: white; }
    .stButton>button { 
        width: 100%; border-radius: 12px; height: 3.5em; 
        background-color: #ff4b4b; color: white; font-weight: bold; border: none;
    }
    div[data-testid="stMetricValue"] { color: #ff4b4b; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CONNESSIONE AI DINAMICA (Fix per Errore 404) ---
def inizializza_ai():
    if "GEMINI_API_KEY" not in st.secrets:
        st.error("❌ Chiave API mancante nei Secrets di Streamlit!")
        return None
    
    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        # Cerchiamo i modelli disponibili che supportano la generazione di contenuti
        available_models = [
            m.name for m in genai.list_models() 
            if 'generateContent' in m.supported_generation_methods
        ]
        
        if not available_models:
            st.error("❌ Nessun modello compatibile trovato per questa API Key.")
            return None
        
        # Priorità: Gemini 3 Flash -> Gemini 1.5 Flash -> Il primo disponibile
        selected = next((m for m in available_models if "gemini-3-flash" in m), 
                   next((m for m in available_models if "gemini-1.5-flash" in m), 
                   available_models[0]))
        
        return genai.GenerativeModel(selected), selected
    except Exception as e:
        st.error(f"❌ Errore durante la connessione a Google AI: {e}")
        return None, None

model_result = inizializza_ai()
model = model_result[0] if model_result else None
model_name = model_result[1] if model_result else ""

# --- 3. LOGICA DI CALCOLO ---
def pulisci_nome(nome):
    # Rimuove (SET) e numeri di collezione (es: "Sheoldred (DMU) 107" -> "Sheoldred")
    return re.sub(r'\s\(.*?\)\s\d+|\s\(.*?\)', '', str(nome)).strip()

def analizza_costi(deck_text, df_collezione):
    wc_needed = {"Common": 0, "Uncommon": 0, "Rare": 0, "Mythic": 0}
    missing_details = []
    
    lines = deck_text.strip().split('\n')
    for line in lines:
        line = line.strip()
        if not line or not line[0].isdigit(): continue
        
        try:
            parts = line.split(' ', 1)
            qty = int(parts[0])
            name = pulisci_nome(parts[1])
            
            # Match con la collezione (Case Insensitive)
            match = df_collezione[df_collezione['Name'].str.lower() == name.lower()]
            
            if not match.empty:
                owned = match['Count'].iloc[0]
                rarity = match['Rarity'].iloc[0]
            else:
                owned, rarity = 0, "Rare"

            diff = max(0, qty - owned)
            if diff > 0:
                if rarity in wc_needed: wc_needed[rarity] += diff
                missing_details.append({"Carta": name, "Mancanti": diff, "Rarità": rarity})
        except: continue
            
    return wc_needed, missing_details

# --- 4. INTERFACCIA UTENTE ---
st.title("🃏 MTGA AI Builder")
if model_name:
    st.caption(f"🤖 Connesso via: {model_name}")

file = st.file_uploader("Carica il tuo CSV di MTGA", type="csv")

if file:
    df = pd.read_csv(file)
    st.success(f"✅ {len(df)} carte caricate correttamente.")

    col1, col2 = st.columns(2)
    with col1:
        fmt = st.selectbox("Formato", ["Standard", "Brawl", "Explorer", "Historic"])
    with col2:
        arc = st.selectbox("Archetipo", ["Aggro", "Control", "Midrange", "Tempo", "Combo"])

    if st.button("🚀 GENERA MAZZO E CALCOLA COSTI"):
        if not model:
            st.error("AI non pronta. Controlla la chiave API.")
        else:
            # Filtriamo le Rare/Mitiche possedute per dare contesto all'AI
            owned_cards = df[(df['Count'] > 0) & (df['Rarity'].str.contains('Rare|Mythic', na=False))]
            context = owned_cards[['Name', 'Count']].sample(min(len(owned_cards), 60)).to_string(index=False)

            prompt = f"""
            Sei un esperto di MTG Arena. Crea un mazzo {fmt} di tipo {arc}.
            Usa prioritariamente queste carte che possiedo:
            {context}
            
            Rispondi SOLO con la lista in formato ESPORTABILE MTGA (es: 4 Nome Carta).
            Includi terre base. Niente commenti o introduzioni.
            """

            with st.spinner("L'AI sta creando la tua strategia..."):
                try:
                    response = model.generate_content(prompt)
                    deck_list = response.text
                    
                    if deck_list:
                        st.subheader("📋 Lista Mazzo")
                        st.code(deck_list, language="text")

                        # Calcolo Wildcards
                        wcs, details = analizza_costi(deck_list, df)
                        
                        st.divider()
                        st.subheader("💰 Wildcards Necessarie")
                        c1, c2, c3, c4 = st.columns(4)
                        c1.metric("C", wcs['Common'])
                        c2.metric("U", wcs['Uncommon'])
                        c3.metric("R", wcs['Rare'])
                        c4.metric("M", wcs['Mythic'])

                        if details:
                            with st.expander("🔎 Dettaglio carte da creare"):
                                st.table(details)
                    else:
                        st.error("L'AI ha restituito una risposta vuota. Riprova.")
                except Exception as e:
                    st.error(f"Errore durante la generazione: {e}")
else:
    st.info("Carica il file CSV per iniziare la creazione.")
