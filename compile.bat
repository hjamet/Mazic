python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r .\requirements.txt
pyinstaller --noconfirm --onefile --console --icon "C:/Users/Jamet/Documents/Projet Info Perso/Mazic-main/assets/icone.ico" --add-data "C:/Users/Jamet/Documents/Projet Info Perso/Mazic-main/assets;assets/"  "C:/Users/Jamet/Documents/Projet Info Perso/Mazic-main/src/main.py"