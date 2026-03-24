import streamlit as st
import pandas as pd
import google.generativeai as genai
import re

# 1. SETUP
st.set_page_config(page_title="MTGA AI Builder", page_icon="🃏")

# Stile dark per mobile
st.markdown("<style>.stButton>button {width: 100%; height: 3em; background-color: #ff4b4b; color: white;}</style>", unsafe_allow_html=True)

# 2. CONNESSIONE AI (Con fallback su modelli stabili)
def get_model():
    if "GEMINI_API_KEY" not in st.secrets:
        st.error("❌ Chiave API mancante nei Secrets!")
        return None
    
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    
    # Proviamo diversi nomi di modelli per sicurezza
    for m_name in ['gemini-1.5-flash', 'gemini-1.5-pro']:
        try:
            m = genai.GenerativeModel(m_name)
            # Test rapido di connessione
            m.generate_content("test", generation_config={"max_output_tokens": 1})
            return m
        except:
            continue
    st.error("❌ Impossibile connettersi ai modelli Gemini. Controlla la tua API Key.")
    return None

model = get_model()

# 3. LOGICA DI PULIZIA
def pulisci_nome(n):
    return re.sub(r'\s\(.*?\)\s\d+|\s\(.*?\)', '', str(n)).strip()

# 4. UI
st.title("🃏 MTGA AI Builder")

file = st.file_uploader("Carica CSV", type="csv")

if file:
    df = pd.read_csv(file)
    st.write(f"✅ CSV caricato. Colonne trovate: {', '.join(df.columns)}")
    
    formato = st.selectbox("Formato", ["Standard", "Brawl", "Explorer"])
    archetipo = st.selectbox("Archetipo", ["Aggro", "Control", "Midrange"])

    if st.button("🚀 GENERA MAZZO"):
        st.write("🔍 Fase 1: Analisi collezione...")
        
        # VERIFICA COLONNE (Il tuo CSV ha: Id,Name,Set,Color,Rarity,Count,PrintCount)
        try:
            # Filtro carte che possiedi
            mie_rare = df[(df['Count'] > 0) & (df['Rarity'].str.contains('Rare|Mythic', na=False, case=False))]
            
            if mie_rare.empty:
                st.warning("⚠️ Non ho trovato Rare o Mitiche nel tuo CSV. Userò le comuni.")
                mie_rare = df[df['Count'] > 0].head(50)
            
            contesto = mie_rare[['Name', 'Count']].head(100).to_string(index=False)
            st.write("📡 Fase 2: Invio richiesta a Gemini...")
            
            prompt = f"Crea un mazzo {formato} {archetipo} per MTG Arena. Usa queste mie carte: {contesto}. Rispondi SOLO con la lista esportabile."
            
            with st.spinner("L'AI sta ragionando..."):
                res = model.generate_content(prompt)
                
                if res and res.text:
                    st.subheader("📋 Ecco il tuo mazzo:")
                    st.code(res.text)
                    
                    # Calcolo Wildcards veloce
                    st.write("📊 Fase 3: Calcolo Wildcards...")
                    # (Qui andrebbe la logica wildcards che abbiamo già scritto)
                else:
                    st.error("L'AI ha risposto ma il testo è vuoto.")
        
        except Exception as e:
            st.error(f"💥 Si è verificato un errore: {e}")

else:
    st.info("Carica il file per iniziare.")
