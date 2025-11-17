from setuptools import setup, find_packages
import os

setup(
    name="antiyoy_ai",
    version="0.1.0",
    packages=find_packages(include=['ai', 'ai.*', 'game', 'game.*', 'rl', 'rl.*',
                                     'tournaments', 'tournaments.*', 'azg', 'azg.*']),
    package_dir={
        '': '.',
    },
    install_requires=[
        'numpy>=1.24.0,<3.0.0',
        'torch>=2.0.0',
        'tqdm>=4.67.0',
        'coloredlogs>=15.0.0',
        'dotdict>=0.1',
    ],
    python_requires='>=3.8',
    description="Antiyoy AI using AlphaZero and other RL techniques",
)
