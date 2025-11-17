sudo apt-get update
sudo apt install pip
sudo apt install python3.12-venv
rm -r .venv
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 alpha-zero/run_training.py
