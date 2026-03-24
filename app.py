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

st.set_page_config(page_title="Scope 8 Pro AI", layout="wide", page_icon="⚡")
st.title("⚡ Scope 8 Pro - Interactief Rapport")

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
        cat = str(row.get("Categorie", "")).upper()
        
        # 1. Controle Isolatieweerstand (> 1.0 MOhm)
        for iso_col in ["R_iso L-N (MΩ)", "R_iso L-PE (MΩ)", "R_iso N-PE (MΩ)"]:
            r_iso = row.get(iso_col)
            if pd.notna(r_iso) and str(r_iso).strip() not in ["", "N.v.t.", "None"]:
                try:
                    if float(r_iso) < 1.0:
                        fouten.append(f"{iso_col} < 1.0")
                except: pass
            
        # 2. Controle Kortsluitstroom (I_k) - Alleen bij Automaten
        i_k = row.get("I_k (A)")
        if pd.notna(i_k) and str(i_k).strip() not in ["", "N.v.t.", "None"]:
            try:
                gemeten_stroom = float(i_k)
                match = re.search(r'([BCDK])(\d+)', type_comp)
                if match:
                    karakteristiek = match.group(1)
                    i_nom = int(match.group(2))
                    
                    if karakteristiek == 'B': factor = 5
                    elif karakteristiek == 'C': factor = 10
                    elif karakteristiek == 'D': factor = 20
                    else: factor = 5
                    
                    vereiste_stroom = factor * i_nom
                    if gemeten_stroom < vereiste_stroom:
                        fouten.append(f"I_k < {vereiste_stroom}A ({factor}xIn)")
            except: pass

        # 3. Controle ALS Uitschakeltijd (t_a) en Testknop
        if "ALS" in cat or "AARDLEK" in cat:
            t_a = row.get("t_a (ms)")
            if pd.notna(t_a) and str(t_a).strip() not in ["", "N.v.t.", "None"]:
                try:
                    if float(t_a) > 300: # Algemene NEN1010 grens voor foutbescherming
                        fouten.append("t_a > 300ms")
                except: pass
                
            testknop = row.get("Testknop OK?")
            if testknop is False or str(testknop).upper() == "NEE":
                fouten.append("Testknop weigert")

        # Eindbeoordeling
        if not fouten:
            beoordeling.append("✅ Akkoord")
        else:
            beoordeling.append("❌ " + " | ".join(fouten))
            
    df["Beoordeling"] = beoordeling
    return df

# De Analyse
if img_file is not None:
    img = Image.open(img_file)
    
    col1, col2 = st.columns([1, 2])
    with col1:
        st.image(img, caption="Foto Verdeelkast", use_container_width=True)
    
    with col2:
        if st.button("Analyseer Foto & Maak Tabel", type="primary"):
            with st.spinner("AI categoriseert de componenten..."):
                try:
                    prompt = """
                    Kijk naar deze foto van een verdeelkast.
                    Maak een lijst van alle componenten.
                    Geef het antwoord UITSLUITEND in puur JSON formaat terug, als een array van objecten.
                    Sleutels die je MOET gebruiken: "Component", "Type", "Categorie", "Functie".
                    
                    Let op: De "Categorie" MOET één van deze drie woorden zijn: "Automaat", "ALS", of "Hoofdschakelaar".
                    
                    Voorbeeld:
                    [{"Component": "Groep 1", "Type": "B16", "Categorie": "Automaat", "Functie": "Wasmachine"}, 
                     {"Component": "ALS 1", "Type": "40A/30mA", "Categorie": "ALS", "Functie": ""}]
                     
                    Zorg dat er GEEN markdown (zoals ```json) omheen staat.
                    """
                    
                    response = model.generate_content([prompt, img])
                    ruwe_tekst = response.text.replace("```json", "").replace("```", "").strip()
                    groepen_data = json.loads(ruwe_tekst)
                    
                    # Logica voor de N.v.t. velden
                    for item in groepen_data:
                        cat = str(item.get("Categorie", "")).upper()
                        
                        # Iedereen krijgt R_iso velden
                        item["R_iso L-N (MΩ)"] = None
                        item["R_iso L-PE (MΩ)"] = None
                        item["R_iso N-PE (MΩ)"] = None
                        item["Z_s (Ω)"] = None
                        
                        if "ALS" in cat or "AARDLEK" in cat:
                            item["I_k (A)"] = "N.v.t." # Geen Ik bij ALS
                            item["t_a (ms)"] = None
                            item["Testknop OK?"] = False # Checkbox voor ALS
                        elif "AUTOMAAT" in cat or "GROEP" in cat:
                            item["I_k (A)"] = None
                            item["t_a (ms)"] = "N.v.t." # Geen t_a bij automaat
                            item["Testknop OK?"] = "N.v.t." # Geen testknop
                        else: # Hoofdschakelaar
                            item["I_k (A)"] = "N.v.t."
                            item["t_a (ms)"] = "N.v.t."
                            item["Testknop OK?"] = "N.v.t."
                    
                    st.session_state['meet_data'] = pd.DataFrame(groepen_data)
                    st.success("Tabel is klaar voor invoer!")
                    
                except Exception as e:
                    st.error(f"Fout bij het maken van de tabel: {e}")
                    st.info("Tip: Druk nog eens op de knop, soms heeft de AI een hikje met JSON.")

        # Laat de tabel zien als hij bestaat
        if 'meet_data' in st.session_state:
            st.write("### Vul je Scope 8 metingen in:")
            
            bewerkte_df = st.data_editor(
                st.session_state['meet_data'],
                num_rows="dynamic",
                hide_index=True,
                use_container_width=True
            )
            
            if st.button("Voer NEN 1010 Controles uit"):
                gecontroleerde_df = controleer_metingen(bewerkte_df)
                st.session_state['meet_data'] = gecontroleerde_df
                st.rerun()
