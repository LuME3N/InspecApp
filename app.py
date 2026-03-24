import streamlit as st
import google.generativeai as genai
from PIL import Image
import json
import pandas as pd
import re
import io

# 1. Veilig de API Key ophalen
try:
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
except:
    st.error("⚠️ API Key niet gevonden in Secrets!")
    st.stop()

st.set_page_config(page_title="Scope 8 Pro", layout="wide", page_icon="⚡")
st.title("⚡ Scope 8 Keurmeester AI")

model = genai.GenerativeModel('models/gemini-2.5-flash')

bron = st.radio("Kies invoer:", ["Camera", "Bladeren (Galerij)"], horizontal=True)

if bron == "Camera":
    img_file = st.camera_input("Maak een foto van de groepenkast")
else:
    img_file = st.file_uploader("Kies een afbeelding", type=['png', 'jpg', 'jpeg'])

# Functie om de NEN1010 regels te checken (NU NOG SLIMMER)
def controleer_metingen(df):
    beoordeling = []
    als_groepen_telling = {} # Om bij te houden hoeveel groepen achter een ALS zitten
    
    # Eerst tellen we even hoeveel groepen er per ALS zijn ingedeeld
    for index, row in df.iterrows():
        achter_als = str(row.get("Achter ALS", "")).strip()
        cat = str(row.get("Categorie", "")).upper()
        if "AUTOMAAT" in cat and achter_als and achter_als != "N.v.t." and achter_als != "None":
            als_groepen_telling[achter_als] = als_groepen_telling.get(achter_als, 0) + 1

    for index, row in df.iterrows():
        fouten = []
        type_comp = str(row.get("Type", "")).upper()
        cat = str(row.get("Categorie", "")).upper()
        achter_als = str(row.get("Achter ALS", "")).strip()
        
        # 1. Max 4 groepen per ALS check
        if "AUTOMAAT" in cat and achter_als in als_groepen_telling:
            if als_groepen_telling[achter_als] > 4:
                fouten.append(f"Te veel groepen (>4) achter {achter_als}")

        # 2. Controle Isolatieweerstand (> 1.0 MOhm)
        for iso_col in ["R_iso L-N (MΩ)", "R_iso L-PE (MΩ)", "R_iso N-PE (MΩ)"]:
            r_iso = row.get(iso_col)
            if pd.notna(r_iso) and str(r_iso).strip() not in ["", "N.v.t.", "None"]:
                try:
                    if float(r_iso) < 1.0:
                        fouten.append(f"{iso_col} te laag")
                except: pass
            
        # 3. Slimme Automaat Controles (Z_s en I_k)
        if "AUTOMAAT" in cat:
            match = re.search(r'([BCDK])(\d+)', type_comp)
            if match:
                karakteristiek = match.group(1)
                i_nom = int(match.group(2))
                factor = 5 if karakteristiek == 'B' else 10 if karakteristiek == 'C' else 20 if karakteristiek == 'D' else 5
                
                i_a = factor * i_nom # Uitschakelstroom
                max_zs = round(230 / i_a, 2) # Maximale Z_s berekening (U0 / Ia)

                # Controleer Z_s
                z_s = row.get("Z_s (Ω)")
                if pd.notna(z_s) and str(z_s).strip() not in ["", "N.v.t.", "None"]:
                    try:
                        if float(z_s) > max_zs:
                            fouten.append(f"Z_s te hoog (Max {max_zs}Ω voor {type_comp})")
                    except: pass
                    
                # Controleer I_k (Als men liever I_k invult in plaats van Z_s)
                i_k = row.get("I_k (A)")
                if pd.notna(i_k) and str(i_k).strip() not in ["", "N.v.t.", "None"]:
                    try:
                        if float(i_k) < i_a:
                            fouten.append(f"I_k te laag (<{i_a}A)")
                    except: pass

        # 4. Controle ALS Uitschakeltijd (t_a) en Testknop
        if "ALS" in cat or "AARDLEK" in cat:
            t_a = row.get("t_a (ms)")
            if pd.notna(t_a) and str(t_a).strip() not in ["", "N.v.t.", "None"]:
                try:
                    if float(t_a) > 300:
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
        if st.button("Start AI Inspectie", type="primary"):
            with st.spinner("AI analyseert componenten en koppelingen..."):
                try:
                    # Nieuwe prompt die OOK vraagt om de ALS te koppelen!
                    prompt = """
                    Kijk naar deze foto van een verdeelkast.
                    Maak een lijst van alle componenten.
                    Geef het antwoord UITSLUITEND in puur JSON formaat (array van objecten).
                    Sleutels: "Component", "Type", "Categorie", "Achter ALS", "Functie".
                    Categorie MOET zijn: "Automaat", "ALS", of "Hoofdschakelaar".
                    "Achter ALS": Geef hier de naam van de ALS waar deze automaat achter zit (bijv. "ALS 1" of "ALS A"). Als het een ALS of Hoofdschakelaar is, vul in "N.v.t.".
                    
                    Voorbeeld:
                    [{"Component": "Groep 1", "Type": "B16", "Categorie": "Automaat", "Achter ALS": "ALS 1", "Functie": "Wasmachine"}]
                    Zorg dat er GEEN markdown omheen staat.
                    """
                    
                    response = model.generate_content([prompt, img])
                    ruwe_tekst = response.text.replace("```json", "").replace("```", "").strip()
                    groepen_data = json.loads(ruwe_tekst)
                    
                    # Kolommen klaarzetten
                    for item in groepen_data:
                        cat = str(item.get("Categorie", "")).upper()
                        item["R_iso L-N (MΩ)"] = None
                        item["R_iso L-PE (MΩ)"] = None
                        item["R_iso N-PE (MΩ)"] = None
                        
                        if "ALS" in cat:
                            item["Z_s (Ω)"] = "N.v.t."
                            item["I_k (A)"] = "N.v.t."
                            item["t_a (ms)"] = None
                            item["Testknop OK?"] = False
                        elif "AUTOMAAT" in cat:
                            item["Z_s (Ω)"] = None
                            item["I_k (A)"] = None
                            item["t_a (ms)"] = "N.v.t."
                            item["Testknop OK?"] = "N.v.t."
                        else: # Hoofdschakelaar
                            item["Z_s (Ω)"] = "N.v.t."
                            item["I_k (A)"] = "N.v.t."
                            item["t_a (ms)"] = "N.v.t."
                            item["Testknop OK?"] = "N.v.t."
                    
                    st.session_state['meet_data'] = pd.DataFrame(groepen_data)
                    st.success("Tabel is klaar voor invoer!")
                    
                except Exception as e:
                    st.error(f"Fout bij het maken van de tabel: {e}")

        # Laat de tabel zien als hij bestaat
        if 'meet_data' in st.session_state:
            st.write("### 📝 Invulformulier (Scope 8)")
            
            bewerkte_df = st.data_editor(
                st.session_state['meet_data'],
                num_rows="dynamic",
                hide_index=True,
                use_container_width=True
            )
            
            col_btn1, col_btn2 = st.columns(2)
            
            with col_btn1:
                if st.button("Voer NEN 1010 Controles uit", use_container_width=True):
                    gecontroleerde_df = controleer_metingen(bewerkte_df)
                    st.session_state['meet_data'] = gecontroleerde_df
                    st.rerun()
            
            with col_btn2:
                # EXCEL EXPORT FUNCTIE
                def to_excel(df):
                    output = io.BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        df.to_excel(writer, index=False, sheet_name='Scope 8 Metingen')
                    processed_data = output.getvalue()
                    return processed_data
                    
                excel_data = to_excel(bewerkte_df)
                st.download_button(
                    label="📥 Download als Excel (.xlsx)",
                    data=excel_data,
                    file_name="scope8_meetrapport.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
