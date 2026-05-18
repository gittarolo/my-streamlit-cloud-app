import streamlit as st
import requests
import base64
import urllib.parse
import pandas as pd
import io
from streamlit_sortables import sort_items  # Biztosítsd, hogy benne van a requirements.txt-ben!

# Oldal alapbeállításai
st.set_page_config(page_title="Saját Privát Tárhely", page_icon="🔒", layout="wide")

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
    
    detected_categories = ["Főkönyvtár"]
    all_files = []
    
    if res.status_code == 200:
        tree = res.json().get("tree", [])
        for item in tree:
            if item["type"] == "tree":
                detected_categories.append(item["path"])
            elif item["type"] == "blob":
                all_files.append(item)
    
    detected_categories = sorted(list(set(detected_categories)))

    # --- 🎛️ DRAG-AND-DROP PANEL AZ OLDALSÁVBAN ---
    st.sidebar.header("🔀 Fülek sorrendje")
    st.sidebar.caption("Fogd meg az egérrel a kártyákat és rendezd át a felső fülek sorrendjét:")
    
    if "current_order" not in st.session_state or set(st.session_state["current_order"]) != set(detected_categories):
        st.session_state["current_order"] = detected_categories

    # Megjelenik az egérrel húzgálható lista a Sidebarban
    sorted_categories = sort_items(st.session_state["current_order"], direction="vertical", key="category_sortable_panel")
    
    if sorted_categories != st.session_state["current_order"]:
        st.session_state["current_order"] = sorted_categories
        st.rerun()

    categories = st.session_state["current_order"]
    st.sidebar.write("---")

    # --- KATEGÓRIA KEZELÉS SECTION (SIDEBAR) ---
    st.sidebar.header("🛠️ Kategóriák kezelése")
    new_cat = st.sidebar.text_input("Új kategória neve:")
    if st.sidebar.button("➕ Kategória létrehozása"):
        if new_cat:
            clean_cat = new_cat.strip().replace("/", "_")
            with st.spinner("Kategória létrekozása..."):
                url = f"https://api.github.com/repos/{REPO}/contents/{clean_cat}/.gitkeep"
                cat_res = requests.put(url, json={"message": f"Kategória létrekozva: {clean_cat}", "content": "XA=="}, headers=headers)
                if cat_res.status_code in [200, 201]:
                    if "current_order" in st.session_state:
                        del st.session_state["current_order"]
                    st.sidebar.success(f"'{clean_cat}' létrekozva!")
                    st.rerun()
                else:
                    st.sidebar.error("Nem sikerült létrehozni.")
        else:
            st.sidebar.warning("Adj meg egy nevet!")

    st.sidebar.write("---")
    
    if "cat_delete_confirm" not in st.session_state:
        st.session_state["cat_delete_confirm"] = False

    cat_to_delete = st.sidebar.selectbox("Kategória törlése:", [c for c in categories if c != "Főkönyvtár"])
    
    if not st.session_state["cat_delete_confirm"]:
        if st.sidebar.button("🗑️ Kategória törlése", type="secondary"):
            if cat_to_delete:
                st.session_state["cat_delete_confirm"] = True
                st.rerun()
    
    if st.session_state["cat_delete_confirm"]:
        st.sidebar.warning(f"⚠️ Biztosan törlöd a(z) '{cat_to_delete}' kategóriát ÉS AZ ÖSSZES benne lévő fájlt?")
        c_yes, c_no = st.sidebar.columns([1, 1])
        if c_yes.button("🔥 Igen, mindent törölj", type="primary", key="cat_del_yes"):
            with st.spinner("Törlés..."):
                files_in_cat = [f for f in all_files if f["path"].startswith(cat_to_delete + "/")]
                for f in files_in_cat:
                    del_url = f"https://api.github.com/repos/{REPO}/contents/{f['path']}"
                    requests.delete(del_url, json={"message": "Kategória törlés miatt eltávolítva", "sha": f["sha"]}, headers=headers)
                requests.delete(f"https://api.github.com/repos/{REPO}/contents/{cat_to_delete}/.gitkeep", json={"message": "Mappa véglegen törölve"}, headers=headers)
                st.session_state["cat_delete_confirm"] = False
                if "current_order" in st.session_state:
                    del st.session_state["current_order"]
                st.sidebar.success(f"'{cat_to_delete}' sikeresen törölve!")
                st.rerun()
        if c_no.button("❌ Mégse", key="cat_del_no"):
            st.session_state["cat_delete_confirm"] = False
            st.rerun()

    # --- FELTÖLTÉS SECTION ---
    st.write("---")
    st.subheader("📤 Új fájl feltöltése")
    target_cat = st.selectbox("Hova szeretnéd feltölteni?", categories)
    uploaded_file = st.file_uploader("Válassz ki egy fájlt:", type=None)
    
    if uploaded_file is not None:
        file_name = uploaded_file.name
        file_bytes = uploaded_file.read()
        file_size_mb = len(file_bytes) / (1024 * 1024)
        st.write(f"Mért fájlméret: **{file_size_mb:.1f} MB**")
        
        if file_size_mb > 100.0:
            st.error("⚠️ Ingyenes verzióban a maximális fájlméret 100 MB.")
        else:
            if st.button("🚀 Biztonságos feltöltés indítása"):
                # ITT JAVÍTVA A NAGYBETŰS St.spinner -> st.spinner hiba!
                with st.spinner("Fájl beolvasása és biztonságos feldolgozása..."):
                    final_path = f"{target_cat}/{file_name}" if target_cat != "Főkönyvtár" else file_name
                    encoded_content = base64.b64encode(file_bytes).decode("utf-8")
                    
                    if file_size_mb > 40.0:
                        blob_url = f"https://api.github.com/repos/{REPO}/git/blobs"
                        blob_res = requests.post(blob_url, json={"content": encoded_content, "encoding": "base64"}, headers=headers)
                        if blob_res.status_code in [200, 201]:
                            blob_sha = blob_res.json().get("sha")
                            tree_url = f"https://api.github.com/repos/{REPO}/contents/{final_path}"
                            res = requests.put(tree_url, json={"message": f"Nagy fájl feltöltve: {final_path}", "sha": blob_sha}, headers=headers)
                        else:
                            res = blob_res
                    else:
                        url = f"https://api.github.com/repos/{REPO}/contents/{final_path}"
                        res = requests.put(url, json={"message": f"Feltöltve: {final_path}", "content": encoded_content}, headers=headers)
                    
                    if res.status_code in [200, 201]:
                        st.success("✨ Sikeres feltöltés!")
                        st.rerun()
                    else:
                        st.error(f"Hiba történt a feltöltésnél. Kód: {res.status_code}")

    st.write("---")

    # --- LISTÁZÁS SECTION ---
    st.subheader("📚 Tárolt fájljaid")
    
    if "move_file_path" not in st.session_state: st.session_state["move_file_path"] = None
    if "move_file_sha" not in st.session_state: st.session_state["move_file_sha"] = None
    if "move_file_name" not in st.session_state: st.session_state["move_file_name"] = None
    if "preview_sha" not in st.session_state: st.session_state["preview_sha"] = None
    if "delete_confirm_sha" not in st.session_state: st.session_state["delete_confirm_sha"] = None

    tabs = st.tabs(categories)

    for i, tab in enumerate(tabs):
        selected_view_cat = categories[i]
        
        with tab:
            if st.session_state["move_file_sha"] is not None and st.session_state["move_file_path"].startswith(selected_view_cat if selected_view_cat != "Főkönyvtár" else ""):
                with st.container(border=True):
                    st.markdown(f"📂 **Fájl áthelyezése:** `{st.session_state['move_file_name']}`")
                    available_destinations = [c for c in categories if c != selected_view_cat]
                    dest_cat = st.selectbox("Válassz új célkategóriát:", available_destinations, key=f"move_sel_{selected_view_cat}")
                    
                    c_move_ok, c_move_cancel = st.columns([1, 1])
                    if c_move_ok.button("✔️ Áthelyezés indítása", type="primary", key=f"ok_{selected_view_cat}"):
                        with st.spinner("Áthelyezés..."):
                            old_api_url = f"https://api.github.com/repos/{REPO}/contents/{st.session_state['move_file_path']}"
                            file_res = requests.get(old_api_url, headers=raw_headers)
                            
                            if file_res.status_code == 200:
                                raw_bytes = file_res.content
                                encoded_content = base64.b64encode(raw_bytes).decode("utf-8")
                                new_path = f"{dest_cat}/{st.session_state['move_file_name']}" if dest_cat != "Főkönyvtár" else st.session_state['move_file_name']
                                create_url = f"https://api.github.com/repos/{REPO}/contents/{new_path}"
                                
                                put_res = requests.put(create_url, json={"message": f"Áthelyezve ide: {new_path}", "content": encoded_content}, headers=headers)
                                if put_res.status_code in [200, 201]:
                                    requests.delete(old_api_url, json={"message": "Áthelyezés miatt törölve", "sha": st.session_state['move_file_sha']}, headers=headers)
                                    st.session_state["move_file_sha"] = None
                                    st.session_state["move_file_path"] = None
                                    st.session_state["move_file_name"] = None
                                    st.success("Sikeresen áthelyezve!")
                                    st.rerun()
                                else:
                                    st.error("Nem sikerült másolni az új kategóriába.")
                            else:
                                st.error("Hiba történt a fájl olvasásakor.")
                                
                    if c_move_cancel.button("❌ Mégse", key=f"cancel_{selected_view_cat}"):
                        st.session_state["move_file_sha"] = None
                        st.session_state["move_file_path"] = None
                        st.session_state["move_file_name"] = None
                        st.rerun()
                st.write("---")

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
                    col_name, col_prev, col_move, col_dl, col_del = st.columns([2, 1, 1, 1, 1])
                    col_name.write(f"📄 {display_name}")
                    
                    file_api_url = f"https://api.github.com/repos/{REPO}/contents/{f['path']}"
                    
                    if col_prev.button("👁️", key=f"prev_{f['sha']}", help="Előnézet"):
                        st.session_state["preview_sha"] = f["sha"] if st.session_state["preview_sha"] != f["sha"] else None
                        st.rerun()
                    
                    if col_move.button("📂", key=f"move_{f['sha']}", help="Áthelyezés"):
                        st.session_state["move_file_sha"] = f["sha"]
                        st.session_state["move_file_path"] = f["path"]
                        st.session_state["move_file_name"] = display_name
                        st.rerun()
                    
                    if col_dl.button("📥", key=f"dl_{f['sha']}", help="Letöltés"):
                        file_res = requests.get(file_api_url, headers=raw_headers)
                        if file_res.status_code == 200:
                            st.download_button(label="💾 Mentés", data=file_res.content, file_name=display_name, key=f"save_{f['sha']}")
                    
                    if col_del.button("🗑️", key=f"del_{f['sha']}", help="Törlés"):
                        st.session_state["delete_confirm_sha"] = f["sha"]
                        st.rerun()

                    if st.session_state["preview_sha"] == f["sha"]:
                        with st.expander("✨ Előnézet bezárása", expanded=True):
                            filename_lower = display_name.lower()
                            
                            if filename_lower.endswith(('.xlsx', '.xls', '.csv')):
                                with st.spinner("Táblázat beolvasása..."):
                                    file_res = requests.get(file_api_url, headers=raw_headers)
                                    if file_res.status_code == 200:
                                        try:
                                            if filename_lower.endswith('.csv'):
                                                df = pd.read_csv(io.BytesIO(file_res.content))
                                            elif filename_lower.endswith('.xls'):
                                                df = pd.read_excel(io.BytesIO(file_res.content), engine='xlrd')
                                            else:
                                                df = pd.read_excel(io.BytesIO(file_res.content))
                                            st.success(f"📊 {df.shape[0]} sor, {df.shape[1]} oszlop betöltve.")
                                            st.dataframe(df, use_container_width=True)
                                        except Exception as e:
                                            st.error("Nem sikerült beolvasni a táblázatot.")
                                    else:
                                        st.error("Hiba a fájl letöltésekor.")

                            elif filename_lower.endswith(('.pdf', '.docx', '.doc', '.pptx', '.ppt')):
                                with st.spinner("Dokumentum előkészítése..."):
                                    meta_res = requests.get(file_api_url, headers=headers)
                                    if meta_res.status_code == 200:
                                        download_url = meta_res.json().get("download_url")
                                        encoded_url = urllib.parse.quote(download_url)
                                        google_viewer_url = f"https://docs.google.com/gview?url={encoded_url}&embedded=true"
                                        iframe_code = f'<iframe src="{google_viewer_url}" width="100%" height="700px" frameborder="0"></iframe>'
                                        st.markdown(iframe_code, unsafe_allow_html=True)

                            else:
                                with st.spinner("Médiafájl betöltése..."):
                                    file_res = requests.get(file_api_url, headers=raw_headers)
                                    if file_res.status_code == 200:
                                        raw_bytes = file_res.content
                                        if filename_lower.endswith(('.png', '.jpg', '.jpeg', '.webp', '.gif')):
                                            st.image(raw_bytes, use_container_width=True)
                                        elif filename_lower.endswith(('.mp4', '.mov', '.avi', '.webm')):
                                            st.video(raw_bytes)
                                        elif filename_lower.endswith(('.mp3', '.wav', '.ogg', '.m4a')):
                                            st.audio(raw_bytes)

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