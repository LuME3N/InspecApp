import streamlit as st
import google.generativeai as genai
from PIL import Image
import json
import pandas as pd
import re

# 1. Veilig de API Key ophalen
try:
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
except:
    st.error("⚠️ API Key niet gevonden in Secrets!")
    st.stop()

st.set_page_config(page_title="Interactieve Scope 8 AI", layout="wide", page_icon="⚡")
st.title("⚡ Scope 8 Interactief Meetrapport")

model = genai.GenerativeModel('models/gemini-2.5-flash')

bron = st.radio("Kies invoer:", ["Camera", "Bladeren (Galerij)"], horizontal=True)

if bron == "Camera":
    img_file = st.camera_input("Maak een foto van de groepenkast")
else:
    img_file = st.file_uploader("Kies een afbeelding", type=['png', 'jpg', 'jpeg'])

# Functie om de NEN1010 regels te checken
def controleer_metingen(df):
    beoordeling = []
    
    for index, row in df.iterrows():
        fouten = []
        type_comp = str(row.get("Type", "")).upper()
        
        # 1. Controle Isolatieweerstand (> 1.0 MOhm)
        r_iso = row.get("R_iso (MΩ)")
        if pd.notna(r_iso) and r_iso != "":
            try:
                if float(r_iso) < 1.0:
                    fouten.append("R_iso < 1.0 MΩ")
            except: pass
            
        # 2. Controle Uitschakelstroom (I_k) vs Karakteristiek
        i_k = row.get("I_k (A)")
        if pd.notna(i_k) and i_k != "":
            try:
                gemeten_stroom = float(i_k)
                # Zoek naar B16, C20, etc. in de Type kolom
                match = re.search(r'([BCDK])(\d+)', type_comp)
                if match:
                    karakteristiek = match.group(1)
                    i_nom = int(match.group(2))
                    
                    # Bepaal de factor (B=5, C=10, D=20)
                    if karakteristiek == 'B': factor = 5
                    elif karakteristiek == 'C': factor = 10
                    elif karakteristiek == 'D': factor = 20
                    else: factor = 5
                    
                    vereiste_stroom = factor * i_nom
                    
                    if gemeten_stroom < vereiste_stroom:
                        fouten.append(f"I_k te laag! Moet >{vereiste_stroom}A zijn ({factor}xIn bij {type_comp})")
            except: pass

        # 3. Eindbeoordeling opmaken
        if not fouten:
            # Check of er wel íets is ingevuld, anders laten we hem leeg
            if pd.notna(r_iso) or pd.notna(i_k):
                beoordeling.append("✅ Akkoord")
            else:
                beoordeling.append("-")
        else:
            beoordeling.append("❌ NIET AKKOORD: " + " | ".join(fouten))
            
    df["NEN1010 Beoordeling"] = beoordeling
    return df

# De Analyse
if img_file is not None:
    img = Image.open(img_file)
    
    col1, col2 = st.columns([1, 2])
    with col1:
        st.image(img, caption="Foto Verdeelkast", use_container_width=True)
    
    with col2:
        if st.button("Analyseer en Maak Tabel", type="primary"):
            with st.spinner("AI zet foto om naar interactieve data..."):
                try:
                    # We vragen nu om JSON (computer-data) in plaats van een getekende tekst-tabel
                    prompt = """
                    Kijk naar deze foto van een verdeelkast.
                    Maak een lijst van alle groepen en componenten.
                    Geef het antwoord UITSLUITEND in puur JSON formaat terug, als een array van objecten.
                    Sleutels die je moet gebruiken: "Component", "Type", "Functie".
                    Voorbeeld:
                    [{"Component": "Groep 1", "Type": "B16", "Functie": "Wasmachine"}, {"Component": "ALS 1", "Type": "40A/30mA", "Functie": ""}]
                    Zorg dat er GEEN markdown (zoals ```json) omheen staat, alleen de pure data.
                    """
                    
                    response = model.generate_content([prompt, img])
                    
                    # Haal de JSON data uit het antwoord
                    ruwe_tekst = response.text.replace("```json", "").replace("```", "").strip()
                    groepen_data = json.loads(ruwe_tekst)
                    
                    # Voeg lege meet-kolommen toe
                    for item in groepen_data:
                        item["R_iso (MΩ)"] = None
                        item["I_k (A)"] = None
                        item["Z_s (Ω)"] = None
                        item["t_a ALS (ms)"] = None
                        item["Testknop"] = False
                    
                    # Sla op in het 'geheugen' van Streamlit
                    st.session_state['meet_data'] = pd.DataFrame(groepen_data)
                    st.success("Tabel klaar voor invoer!")
                    
                except Exception as e:
                    st.error(f"Er ging iets mis bij het lezen van de data: {e}")
                    st.info("Tip: Soms helpt het om de knop nog een keer in te drukken.")

        # Als de data in het geheugen staat, toon het interactieve schema
        if 'meet_data' in st.session_state:
            st.write("### Vul je metingen in:")
            
            # De interactieve tabel!
            bewerkte_df = st.data_editor(
                st.session_state['meet_data'],
                num_rows="dynamic",
                hide_index=True,
                use_container_width=True
            )
            
            # Knop om de beoordeling uit te voeren
            if st.button("Check NEN 1010 Normen"):
                gecontroleerde_df = controleer_metingen(bewerkte_df)
                st.session_state['meet_data'] = gecontroleerde_df # Update het geheugen
                st.rerun() # Herlaad het scherm om de rode kruisjes/groene vinkjes te laten zien
