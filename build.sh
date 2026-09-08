pyinstaller --onefile --additional-hooks-dir=./hooks --add-data="main.py:." --copy-metadata=streamlit --collect-all=pandas --collect-all=pyarrow --collect-all=filelock run_app.py --clean
