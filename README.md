# 520ProjectAntiyoyAI
Project for CSC 520. An AI which can play a replica of Antiyoy by yiotro.

<!-- TODO: EXPLAIN HOW TO GET THE ALPHAZERO TOURNAMENT RUNNER FILE TO WORK -->

To generate test data used in our paper for every agent other than AlphaZero,
you will need the Torch library and the Gym library installed. I recommend using
a virtual environment for this.
To make a virtual environment, run the following command:
```
python -m venv .venv
```
Then, activate the virtual environment with the following command:
- On Windows:
```
.venv\Scripts\activate
```
- On MacOS/Linux:
```
source .venv/bin/activate
```
Once you have activated the virtual environment, install the required libraries with:
```
pip install torch gym
```
After this, you should be able to run any executable Python files in this repository
except for the AlphaZero tournament runner.

To play a game or pit two agents against each other, you can run main.py with the
very simple command:
```
python main.py
```
You can specify specific parameters for the game and what agents to use in
the game by responding to the prompts in the command line interface.
To generate test data for the SRB vs SRB matches, you can run:
```
python -m tournaments.runSRBTournament.py
```
This will output CSV files containing detailed statistics about each
AI's performance at each turn in each game played in the tournament, 
as well as a single text file per matchup containing a description of
the parameters of the tournament as well as the win percentages of each AI
involved in the matchup.

To generate test data for the minimax related matches, you can run:
```
python -m tournaments.runMinimaxTournament.py
```
Do not be surprised if this takes a long time, as minimax is very slow.
Like before, this will output results in CSV files and text files.

To generate test data for the PPO related matches, you can run:
```
python -m tournaments.runPPOTournament.py
```
Again, this will output results in CSV files and text files.

In every tournament, you can modify their respective Python files,
located in the tournaments folder to change parameters of the tournament.
Also, if you have many CPU cores available and plenty of RAM, 
you can increase the number of parallel workers used in the tournaments 
to speed up the process of running the tournaments.
