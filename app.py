import streamlit as st
import requests
import base64

# Oldal alapbeállításai
st.set_page_config(page_title="Saját Privát Tárhely", page_icon="🔒", layout="centered")

def check_password():
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False
    if st.session_state["authenticated"]:
        return True
    st.title("🔒 Privát Tárhely Belépés")
    password_input = st.text_input("Kérlek, add meg a jelszót:", type="password")
    if st.button("Belépés"):
        if password_input == st.secrets["ACCESS_PASSWORD"]:
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("❌ Helytelen jelszó!")
    return False

if check_password():
    st.title("📁 Saját Felhő Tárhelyem")

    TOKEN = st.secrets["GITHUB_TOKEN"]
    REPO = st.secrets["GITHUB_REPO"]
    
    headers = {"Authorization": f"token {TOKEN}", "Accept": "application/vnd.github.v3+json"}
    raw_headers = {"Authorization": f"token {TOKEN}", "Accept": "application/vnd.github.v3.raw"}

    # --- FÁJLOK ÉS KATEGÓRIÁK LEKÉRÉSE ---
    with st.spinner("Tárhely beolvasása..."):
        res = requests.get(f"https://api.github.com/repos/{REPO}/git/trees/main?recursive=1", headers=headers)
    
    categories = ["Főkönyvtár"]
    all_files = []
    
    if res.status_code == 200:
        tree = res.json().get("tree", [])
        for item in tree:
            if item["type"] == "tree":
                categories.append(item["path"])
            elif item["type"] == "blob":
                all_files.append(item)
    
    categories = sorted(list(set(categories)))

    # --- KATEGÓRIA KEZELÉS SECTION (SIDEBAR) ---
    st.sidebar.header("🛠️ Kategóriák kezelése")
    new_cat = st.sidebar.text_input("Új kategória neve:")
    if st.sidebar.button("➕ Kategória létrehozása"):
        if new_cat:
            clean_cat = new_cat.strip().replace("/", "_")
            with st.spinner("Kategória létrehozása..."):
                url = f"https://api.github.com/repos/{REPO}/contents/{clean_cat}/.gitkeep"
                cat_res = requests.put(url, json={"message": f"Kategória létrehozva: {clean_cat}", "content": "XA=="}, headers=headers)
                if cat_res.status_code in [200, 201]:
                    st.sidebar.success(f"'{clean_cat}' létrehozva!")
                    st.rerun()
                else:
                    st.sidebar.error("Nem sikerült létrehozni.")
        else:
            st.sidebar.warning("Adj meg egy nevet!")

    st.sidebar.write("---")
    
    # Inicializáljuk a kategória törlés megerősítés állapotát
    if "cat_delete_confirm" not in st.session_state:
        st.session_state["cat_delete_confirm"] = False

    cat_to_delete = st.sidebar.selectbox("Kategória törlése:", [c for c in categories if c != "Főkönyvtár"])
    
    # Ha még nem nyomott a törlésre, mutatjuk az alap Törlés gombot
    if not st.session_state["cat_delete_confirm"]:
        if st.sidebar.button("🗑️ Kategória törlése", type="secondary"):
            if cat_to_delete:
                st.session_state["cat_delete_confirm"] = True
                st.rerun()
    
    # Ha rányomott a törlésre, elrejtjük az alap gombot és mutatjuk a megerősítést az oldalsávban
    if st.session_state["cat_delete_confirm"]:
        st.sidebar.warning(f"⚠️ Biztosan törlöd a(z) '{cat_to_delete}' kategóriát ÉS AZ ÖSSZES benne lévő fájlt?")
        
        c_yes, c_no = st.sidebar.columns([1, 1])
        
        if c_yes.button("🔥 Igen, mindent törölj", type="primary", key="cat_del_yes"):
            with st.spinner("Törlés..."):
                # 1. Töröljük a mappában lévő összes fájlt
                files_in_cat = [f for f in all_files if f["path"].startswith(cat_to_delete + "/")]
                for f in files_in_cat:
                    del_url = f"https://api.github.com/repos/{REPO}/contents/{f['path']}"
                    requests.delete(del_url, json={"message": "Kategória törlés miatt eltávolítva", "sha": f["sha"]}, headers=headers)
                
                # 2. Töröljük a mappa rejtett rendszerfájlját is, hogy teljesen megszűnjön
                requests.delete(f"https://api.github.com/repos/{REPO}/contents/{cat_to_delete}/.gitkeep", json={"message": "Mappa véglegesen törölve"}, headers=headers)
                
                # Állapot alaphelyzetbe tétele és frissítés
                st.session_state["cat_delete_confirm"] = False
                st.sidebar.success(f"'{cat_to_delete}' sikeresen törölve!")
                st.rerun()
                
        if c_no.button("❌ Mégse", key="cat_del_no"):
            st.session_state["cat_delete_confirm"] = False
            st.rerun()

    # --- FELTÖLTÉS SECTION ---
    st.write("---")
    st.subheader("📤 Új fájl feltöltése")
    target_cat = st.selectbox("Hova szeretnéd feltölteni?", categories)
    uploaded_file = st.file_uploader("Válassz ki egy fájlt:")
    
    if uploaded_file is not None:
        file_name = uploaded_file.name
        file_size_mb = len(uploaded_file.getvalue()) / (1024 * 1024)
        st.write(f"Mért fájlméret: **{file_size_mb:.1f} MB**")
        
        if file_size_mb > 50.0:
            st.error(f"⚠️ A GitHub API miatt maximum 50 MB-os fájlt tölthetsz fel így.")
        else:
            if st.button("🚀 Biztonságos feltöltés indítása"):
                with st.spinner("Feltöltés..."):
                    encoded_content = base64.b64encode(uploaded_file.read()).decode("utf-8")
                    final_path = f"{target_cat}/{file_name}" if target_cat != "Főkönyvtár" else file_name
                    url = f"https://api.github.com/repos/{REPO}/contents/{final_path}"
                    res = requests.put(url, json={"message": f"Feltöltve ide: {final_path}", "content": encoded_content}, headers=headers)
                    if res.status_code in [200, 201]:
                        st.success("Sikeres feltöltés!")
                        st.rerun()
                    else:
                        st.error("Hiba történt a feltöltésnél.")

    st.write("---")

    # --- LISTÁZÁS ÉS ELŐNÉZET SECTION ---
    st.subheader("📚 Tárolt fájljaid")
    selected_view_cat = st.selectbox("Melyik kategóriát nézed?", categories)
    
    if "preview_sha" not in st.session_state: st.session_state["preview_sha"] = None
    if "delete_confirm_sha" not in st.session_state: st.session_state["delete_confirm_sha"] = None

    filtered_files = []
    for f in all_files:
        path_parts = f["path"].split("/")
        if selected_view_cat == "Főkönyvtár" and len(path_parts) == 1:
            filtered_files.append(f)
        elif selected_view_cat != "Főkönyvtár" and f["path"].startswith(selected_view_cat + "/") and not f["path"].endswith(".gitkeep"):
            filtered_files.append(f)

    if not filtered_files:
        st.info("Ez a kategória jelenleg üres.")
    else:
        for f in filtered_files:
            display_name = f["path"].split("/")[-1]
            col_name, col_prev, col_dl, col_del = st.columns([2, 1, 1, 1])
            col_name.write(f"📄 {display_name}")
            
            file_api_url = f"https://api.github.com/repos/{REPO}/contents/{f['path']}"
            
            if col_prev.button("👁️", key=f"prev_{f['sha']}"):
                st.session_state["preview_sha"] = f["sha"] if st.session_state["preview_sha"] != f["sha"] else None
                st.rerun()
            
            if col_dl.button("📥", key=f"dl_{f['sha']}"):
                file_res = requests.get(file_api_url, headers=raw_headers)
                if file_res.status_code == 200:
                    st.download_button(label="💾 Mentés", data=file_res.content, file_name=display_name, key=f"save_{f['sha']}")
            
            if col_del.button("🗑️", key=f"del_{f['sha']}"):
                st.session_state["delete_confirm_sha"] = f["sha"]
                st.rerun()

            if st.session_state["preview_sha"] == f["sha"]:
                with st.expander("✨ Előnézet bezárása", expanded=True):
                    with st.spinner("Betöltés..."):
                        file_res = requests.get(file_api_url, headers=raw_headers)
                        if file_res.status_code == 200:
                            raw_bytes = file_res.content
                            filename_lower = display_name.lower()
                            
                            if filename_lower.endswith(('.png', '.jpg', '.jpeg', '.webp', '.gif')):
                                st.image(raw_bytes, use_container_width=True)
                            elif filename_lower.endswith(('.mp4', '.mov', '.avi', '.webm')):
                                st.video(raw_bytes)
                            elif filename_lower.endswith(('.mp3', '.wav', '.ogg', '.m4a')):
                                st.audio(raw_bytes)
                            elif filename_lower.endswith('.pdf'):
                                base64_pdf = base64.b64encode(raw_bytes).decode('utf-8')
                                pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="600" type="application/pdf"></iframe>'
                                st.markdown(pdf_display, unsafe_allow_html=True)
                            else:
                                st.warning("Ehhez a fájltípushoz nem elérhető online előnézet.")

            if st.session_state["delete_confirm_sha"] == f["sha"]:
                st.warning(f"⚠️ Biztosan törlöd: '{display_name}'?")
                c_yes, c_no = st.columns([1, 1])
                if c_yes.button("🔥 Igen", key=f"y_{f['sha']}", type="primary"):
                    requests.delete(file_api_url, json={"message": "Törölve", "sha": f["sha"]}, headers=headers)
                    st.session_state["delete_confirm_sha"] = None
                    st.rerun()
                if c_no.button("❌ Mégse", key=f"n_{f['sha']}"):
                    st.session_state["delete_confirm_sha"] = None
                    st.rerun()
                st.write("---")