import streamlit as st
import pandas as pd
from datetime import datetime
import os
from filelock import FileLock

# Nazwy plików bazy danych, blokady oraz listy mediów
PARQUET_FILE = "drill.parquet"
LOCK_FILE = "drill.parquet.lock"
MEDIA_FILE = "media.txt"

# Inicjalizacja pliku z mediami, jeśli jeszcze nie istnieje
if not os.path.exists(MEDIA_FILE):
    with open(MEDIA_FILE, "w", encoding="utf-8") as f:
        f.write("HF\nVHF\nUHF\nInternet\nSatelita\nD-STAR\nDMR")

# Funkcja wczytująca dostępne media z pliku tekstowego
def load_media():
    with open(MEDIA_FILE, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]

# Bezpieczny odczyt pliku Parquet z użyciem blokady (dla wielu użytkowników)
def read_parquet_safe():
    if not os.path.exists(PARQUET_FILE):
        # Definicja struktury tabeli (dodano pole NOTES)
        return pd.DataFrame(columns=[
            "FROM_TIME", "FROM_CALL", "FROM_MSG", 
            "TO_CALL", "TO_MSG", "MEDIUM", "NOTES"
        ])
    
    lock = FileLock(LOCK_FILE, timeout=10)
    with lock:
        try:
            df = pd.read_parquet(PARQUET_FILE)
            # Zapewnienie kompatybilności wstecznej, jeśli plik istniał przed dodaniem NOTES
            if "NOTES" not in df.columns:
                df["NOTES"] = ""
            return df
        except Exception as e:
            st.error(f"Błąd podczas odczytu pliku bazy danych: {e}")
            return pd.DataFrame()

# Bezpieczny zapis struktury do pliku Parquet z użyciem blokady
def write_parquet_safe(df):
    lock = FileLock(LOCK_FILE, timeout=10)
    with lock:
        df.to_parquet(PARQUET_FILE, index=False)

# Ustawienia strony głównej interfejsu Streamlit
st.set_page_config(page_title="Rejestrator Łączności Drill", layout="wide")
st.title("📟 Radioamatorski Rejestrator Łączności (Drill)")

# Załadowanie listy dostępnych mediów transmisji
media_options = load_media()

# =========================================================================
# SEKCJA 1: FORMULARZ WPROWADZANIA NOWYCH DANYCH
# =========================================================================
st.subheader("📝 Dodaj nowy wpis do rejestru")

with st.form(key="drill_form", clear_on_submit=True):
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("### SEKCJA FROM (Nadawca)")
        from_call = st.text_input("Znak krótkofalarski (CALL)", key="f_call", placeholder="np. SP5Z").upper()
        from_msg = st.text_area("Wiadomość (MSG)", key="f_msg", placeholder="Treść komunikatu nadawcy...")
        
    with col2:
        st.markdown("### SEKCJA TO (Odbiorca)")
        to_call = st.text_input("Znak krótkofalarski (CALL)", key="t_call", placeholder="np. SP3Y").upper()
        to_msg = st.text_area("Wiadomość (MSG)", key="t_msg", placeholder="Treść komunikatu odbiorcy...")
        
    with col3:
        st.markdown("### PARAMETRY & NOTATKI")
        selected_medium = st.selectbox("Medium transmisji", options=media_options)
        # Nowe pole NOTES dodane do formularza
        notes = st.text_area("Uwagi / Notatki (NOTES)", key="notes", placeholder="Dodatkowe informacje o łączności...")
        st.write("")
        submit_button = st.form_submit_button(label="Zapisz łączność", use_container_width=True)

# Obsługa logiki po naciśnięciu przycisku "Zapisz łączność"
if submit_button:
    if not from_call.strip() or not to_call.strip():
        st.error("Wprowadzenie znaku (CALL) dla nadawcy oraz odbiorcy jest wymagane!")
    else:
        # Generowanie aktualnego czasu serwera
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Przygotowanie nowego rekordu danych (w tym nowego pola NOTES)
        new_row = pd.DataFrame([{
            "FROM_TIME": current_time,
            "FROM_CALL": from_call.strip(),
            "FROM_MSG": from_msg.strip(),
            "TO_CALL": to_call.strip(),
            "TO_MSG": to_msg.strip(),
            "MEDIUM": selected_medium,
            "NOTES": notes.strip()
        }])
        
        try:
            # Odczyt aktualnej bazy, dodanie wiersza i bezpieczny zapis
            current_db = read_parquet_safe()
            updated_db = pd.concat([current_db, new_row], ignore_index=True)
            write_parquet_safe(updated_db)
            st.success("Dane (wraz z notatką) zostały pomyślnie dodane!")
            st.rerun()  # Odświeżenie widoku tabeli
        except Exception as e:
            st.error(f"Nie udało się zapisać danych: {e}")

# =========================================================================
# SEKCJA 2: WYŚWIETLANIE, EDYCJA ORAZ USUWANIE DANYCH
# =========================================================================
st.markdown("---")
st.subheader("🗂️ Aktualna baza danych łączności")

# Pobranie świeżych danych z pliku przed wyrenderowaniem tabeli
df_display = read_parquet_safe()

if not df_display.empty:
    st.info("💡 Możesz edytować dowolną komórkę (w tym kolumnę NOTES) bezpośrednio w tabeli. Aby usunąć wiersz, zaznacz go i naciśnij klawisz 'Delete'.")
    
    # Interaktywny edytor danych (kolumna NOTES pojawi się automatycznie na końcu)
    edited_df = st.data_editor(
        df_display, 
        num_rows="dynamic",  
        use_container_width=True,
        key="parquet_data_editor"
    )
    
    col_actions, col_spacer = st.columns([1, 3])
    
    with col_actions:
        if st.button("Zapisz zmiany w tabeli", use_container_width=True, type="primary"):
            try:
                write_parquet_safe(edited_df)
                st.success("Wprowadzone zmiany zostały zapisane!")
                st.rerun()
            except Exception as e:
                st.error(f"Błąd podczas aktualizacji bazy danych: {e}")
                
    # =========================================================================
    # SEKCJA 3: EKSPORT DO PLIKU CSV
    # =========================================================================
    st.markdown("### 📥 Eksport do formatu zewnętrznego")
    
    csv_data = edited_df.to_csv(index=False).encode('utf-8')
    
    st.download_button(
        label="Pobierz aktualny stan jako plik CSV",
        data=csv_data,
        file_name=f"drill_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv",
        use_container_width=False
    )
else:
    st.warning("Brak zarejestrowanych danych w pliku drill.parquet. Użyj formularza powyżej, aby dodać pierwszą łączność.")
