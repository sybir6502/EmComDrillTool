import os
import sys
import streamlit.web.cli as stcli

if __name__ == '__main__':
    # Ustalamy realną ścieżkę do katalogu, w którym znajduje się plik .exe
    if getattr(sys, 'frozen', False):
        script_dir = os.path.dirname(sys.executable)
    else:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        
    os.chdir(script_dir)
    
    # Ścieżka do ukrytego wewnątrz .exe pliku aplikacji
    target_app = os.path.join(os.path.dirname(__file__), "main.py")
    
    sys.argv = [
        "streamlit", 
        "run", 
        target_app, 
        "--global.developmentMode=false",
        f"--server.headless=true"
    ]
    
    sys.exit(stcli.main())
