import streamlit as st
import pandas as pd
import google.generativeai as genai
import re
from typing import List, Dict

# --- 1. CONFIGURAZIONE E STILE ---
st.set_page_config(page_title="MTGA AI Builder Pro", page_icon="🔥", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: #e0e0e0; }
    .stButton>button { 
        background: linear-gradient(45deg, #28a745, #1e7e34);
        color: white; border: none; font-weight: bold;
        transition: 0.3s; border-radius: 8px;
    }
    .stButton>button:hover { transform: scale(1.02); box-shadow: 0 4px 15px rgba(40,167,69,0.4); }
    .card-stats { background-color: #1c2128; padding: 15px; border-radius: 10px; border-left: 5px solid #28a745; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. DATI ARCHETIPI (Sincronizzati con meta Untapped.gg 2026) ---
META_ARCHETYPES = {
    "Standard": ["Mono-Red Aggro", "Azorius Control", "Golgari Midrange", "Boros Convoke", "Dimir Midrange", "Esper Legends", "5-Color Ramp"],
    "Explorer": ["Rakdos Vampires", "Izzet Phoenix", "Amalia Combo", "Mono-White Humans", "Azorius Control", "Abzan Greasefang"],
    "Historic": ["Izzet Wizards", "Mono-Green Elves", "Rakdos Midrange", "Sultai Yawgmoth", "Kethis Combo"],
    "Brawl": ["100-Card Singleton (Commander)", "Aggro", "Control", "Combo", "Tribal"],
    "Alchemy": ["Heist Decks", "Mono-Black Control", "Red Deck Wins"]
}

# --- 3. LOGICA CORE ---
def inizializza_ai():
    if "GEMINI_API_KEY" not in st.secrets:
        st.error("🔑 API Key non trovata!")
        return None
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    return genai.GenerativeModel('gemini-1.5-flash')

def get_mana_icons(colors):
    mapping = {"White": "☀️", "Blue": "💧", "Black": "💀", "Red": "🔥", "Green": "🌳"}
    return " ".join([mapping[c] for c in colors])

def analizza_mazzo(testo_mazzo, df_collezione):
    wc_costo = {"Common": 0, "Uncommon": 0, "Rare": 0, "Mythic": 0}
    mancanti = []
    
    linee = re.findall(r"(\d+)\s+(.+)", testo_mazzo)
    for qta, nome in linee:
        qta = int(qta)
        nome = nome.strip()
        
        # Matching flessibile
        match = df_collezione[df_collezione['Name'].str.contains(nome, case=False, na=False)]
        
        if not match.empty:
            possedute = match['Count'].iloc[0]
            rarita = match['Rarity'].iloc[0]
        else:
            possedute, rarita = 0, "Rare" # Default se ignota

        if possedute < qta:
            diff = qta - possedute
            if rarita in wc_costo: wc_costo[rarita] += diff
            mancanti.append({"Carta": nome, "Mancano": diff, "Rarità": rarita})
            
    return wc_costo, mancanti

# --- 4. INTERFACCIA ---
model = inizializza_ai()

with st.sidebar:
    st.title("⚙️ Configurazione")
    file = st.file_uploader("Carica Collezione (CSV)", type="csv")
    st.divider()
    formato = st.selectbox("Formato Meta", list(META_ARCHETYPES.keys()))
    archetipo = st.selectbox("Scegli Archetipo", META_ARCHETYPES[formato])
    colori = st.multiselect("Identità di Colore", ["White", "Blue", "Black", "Red", "Green"], default=["Red"])
    
    st.info("L'AI darà priorità alle carte che già possiedi per risparmiare Wildcards.")

st.title("🃏 MTGA AI Strategy Builder")

if file:
    df = pd.read_csv(file)
    # Pulizia minima colonne
    df.columns = [c.strip() for c in df.columns]
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        if st.button(f"🚀 Genera {archetipo} {get_mana_icons(colori)}"):
            # Campionamento intelligente delle tue top cards
            top_cards = df[df['Count'] > 0].sort_values(by='Rarity', ascending=False).head(100)
            contesto_csv = top_cards[['Name', 'Count', 'Rarity']].to_string(index=False)
            
            prompt = f"""
            Sei un esperto di Magic Arena e Untapped.gg. Crea un mazzo {formato} archetipo {archetipo}.
            Colori: {', '.join(colori)}.
            
            REGOLE TECNICHE:
            1. Analizza la SINERGIA tra le carte e ottimizza la CURVA DI MANA.
            2. Usa i nomi delle carte in ITALIANO.
            3. Includi una lista ESPORTABILE (es: 4 Nome Carta).
            4. Se possibile, integra queste carte della mia collezione:
            {contesto_csv}
            
            Restituisci solo la lista mazzo e una breve spiegazione della strategia.
            """
            
            with st.spinner("Analizzando il meta e la tua collezione..."):
                try:
                    res = model.generate_content(prompt)
                    testo_output = res.text
                    
                    # Separazione Lista e Strategia
                    parti = testo_output.split("\n\n")
                    lista_testo = "\n".join([line for line in testo_output.split('\n') if re.match(r'^\d+\s', line)])
                    
                    st.subheader("📋 Lista Esportabile")
                    st.code(lista_testo, language="text")
                    
                    with st.expander("📖 Strategia e Sinergie"):
                        st.write(testo_output)
                        
                    # Calcolo costi
                    wcs, list_mancanti = analizza_mazzo(lista_testo, df)
                    
                    with col2:
                        st.subheader("💰 Costo Stimato")
                        st.metric("Rare", wcs['Rare'])
                        st.metric("Mitiche", wcs['Mythic'])
                        
                        if list_mancanti:
                            st.warning("Carte da creare:")
                            st.table(list_mancanti)
                        else:
                            st.success("Puoi montarlo subito!")
                            st.balloons()
                            
                except Exception as e:
                    st.error(f"Errore: {e}")
else:
    st.warning("👈 Carica il tuo file CSV per iniziare l'analisi.")
    st.markdown("""
    ### Come ottenere il file CSV:
    1. Usa un tracker come **Untapped.gg** o **MTGA Assistant**.
    2. Vai nella sezione 'Collection' ed esporta in formato CSV.
    3. Caricalo qui per ricevere consigli personalizzati.
    """)
