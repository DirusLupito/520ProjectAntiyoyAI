sudo apt install pip
rm -r .venv
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 alpha-zero/run_training.py
