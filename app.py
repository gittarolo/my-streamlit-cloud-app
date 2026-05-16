import streamlit as st
import requests
import base64

# Oldal alapbeállításai
st.set_page_config(page_title="Saját Privát Tárhely", page_icon="🔒", layout="centered")

# 1. BIZTONSÁG: Jelszó ellenőrzése
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
            st.error("❌ Helytelen jelszó! Hozzáférés megtagadva.")
    return False

# Ha a jelszó helyes, betöltődik az app többi része
if check_password():
    st.title("📁 Saját Felhő Tárhelyem")
    st.info("Ez a felület közvetlenül a privát GitHub tárhelyedhez kapcsolódik.")

    # Környezeti változók beolvasása a biztonságos tárolóból
    TOKEN = st.secrets["GITHUB_TOKEN"]
    REPO = st.secrets["GITHUB_REPO"]
    
    headers = {
        "Authorization": f"token {TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }

    # --- FÁJL FELTÖLTÉS SECTION ---
    st.subheader("📤 Új fájl feltöltése")
    uploaded_file = st.file_uploader("Válassz ki egy fájlt a készülékedről:")

    if uploaded_file is not None:
        file_name = uploaded_file.name
        file_bytes = uploaded_file.read()
        encoded_content = base64.b64encode(file_bytes).decode("utf-8")
        
        if st.button("🚀 Biztonságos feltöltés indítása"):
            with st.spinner("Fájl küldése a GitHubra..."):
                url = f"https://api.github.com/repos/{REPO}/contents/{file_name}"
                data = {
                    "message": f"Feltöltve Streamlit-ről: {file_name}",
                    "content": encoded_content
                }
                response = requests.put(url, json=data, headers=headers)
                if response.status_code in [200, 201]:
                    st.success(f"✅ A(z) '{file_name}' sikeresen elmentve!")
                    st.rerun()
                else:
                    st.error("❌ Hiba történt a feltöltés során.")

    st.write("---")

    # --- FÁJL LISTÁZÁS, LETÖLTÉS ÉS TÖRLES SECTION ---
    st.subheader("📚 Tárolt fájljaid elérése")
    
    list_url = f"https://api.github.com/repos/{REPO}/contents/"
    
    with st.spinner("Fájllista frissítése..."):
        res = requests.get(list_url, headers=headers)
        
    if res.status_code == 200:
        files = res.json()
        valid_files = [f for f in files if f["type"] == "file"]
        
        if not valid_files:
            st.write("A tárhelyed jelenleg üres.")
        else:
            # Inicializáljuk a törlési fázist a memóriában, ha még nem létezik
            if "delete_confirm_sha" not in st.session_state:
                st.session_state["delete_confirm_sha"] = None

            for f in valid_files:
                col_name, col_dl, col_del = st.columns([2, 1, 1])
                col_name.write(f"📄 {f['name']}")
                
                # 1. Letöltés gomb
                if col_dl.button("📥 Letölt", key=f"dl_btn_{f['sha']}"):
                    file_res = requests.get(f["url"], headers=headers)
                    if file_res.status_code == 200:
                        raw_data = base64.b64decode(file_res.json()["content"])
                        st.download_button(
                            label="💾 Mentés",
                            data=raw_data,
                            file_name=f["name"],
                            key=f"save_{f['sha']}"
                        )
                
                # 2. Törlés gomb (Első megnyomás)
                if col_del.button("🗑️ Töröl", key=f"del_btn_{f['sha']}"):
                    # Elmentjük a memóriába, hogy épp MELYIK fájlt akarja törölni a felhasználó
                    st.session_state["delete_confirm_sha"] = f["sha"]
                    st.rerun()

                # --- MEGERŐSÍTŐ PANEL ---
                # Ha a felhasználó rákattintott a törlésre, és ez az a fájl, akkor mutatjuk a kérdést
                if st.session_state["delete_confirm_sha"] == f["sha"]:
                    st.warning(f"⚠️ Biztosan törölni szeretnéd a(z) '{f['name']}' fájlt?")
                    col_yes, col_no = st.columns([1, 1])
                    
                    # IGEN gomb - Végrehajtja a törlést
                    if col_yes.button("🔥 Igen, töröld!", key=f"yes_{f['sha']}", type="primary"):
                        with st.spinner("Törlés folyamatban..."):
                            delete_url = f"https://api.github.com/repos/{REPO}/contents/{f['name']}"
                            delete_data = {
                                "message": f"Törölve: {f['name']}",
                                "sha": f["sha"]
                            }
                            del_res = requests.delete(delete_url, json=delete_data, headers=headers)
                            
                            if del_res.status_code == 200:
                                st.session_state["delete_confirm_sha"] = None # Törlési állapot visszaállítása
                                st.success("Sikeres törlés!")
                                st.rerun()
                            else:
                                st.error("❌ Hiba történt a törlés során.")
                    
                    # NEM gomb - Elveti a műveletet
                    if col_no.button("❌ Mégse", key=f"no_{f['sha']}"):
                        st.session_state["delete_confirm_sha"] = None # Törlési állapot törlése
                        st.rerun()
                    
                    st.write("---") # Kis elválasztó vonal a megerősítő panel alá
    else:
        st.error("Nem sikerült elérni a GitHub tárhelyet.")