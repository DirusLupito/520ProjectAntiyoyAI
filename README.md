# 520ProjectAntiyoyAI
Project for CSC 520. An AI which can play a replica of Antiyoy by yiotro.

## AlphaZero Branch

This branch was used for testing the AlphaZero algorithm on Antiyoy. Because of its special dependencies and large size, we decided to keep it in a separate branch. Running `main.py`, tournaments, and playing against the trained AI is the same as in the main branch. See `origin/main` for details.

### `alpha-zero-general`

This project uses the [`alpha-zero-general`](https://github.com/suragnair/alpha-zero-general) project to integrate with the AlphaZero algorithm. It's installed as a git submodule in `/azg`.

### Dependencies

This project uses torch and numpy, among other libraries. 

Dependencies can be installed using:
`pip install -r requirements.txt`.

It's recommended to do this in a virtual environment.

### Installation 

This project depends on the `alpha-zero-general` library. It's important to use:
`git submodule init`
before trying to run the project.

### How to run

#### To train:

Use: `python -m alpha_zero.run_training` to begin training.

This will run locally, and torch will attempt to use a GPU if one is available. 

There are several important hyperparameters that can be adjusted to alter training. They can be found in `alpha_zero/main.py` alongside detailed comments about what they do. 

#### To play against it:

Generally the same as the main branch. The trained model will be stored in `temp/best.pth.tar`, and `./main.py` will read from that to determine moves. 

Running tournaments is the same process. 