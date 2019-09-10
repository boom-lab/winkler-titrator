# winkler-titrator
software to control WHOI Nicholson Lab Winkler titrator

## Installation instructions:

recommended software pre-installed
Anaconda or miniconda (https://conda.io/docs/user-guide/install/download.html)

1. Install git.  If using Homebrew package manager, from terminal:
```bash
$ brew install git
```
2. Install miniconda for python 3.x: [(Instructions)](https://conda.io/miniconda.html)
3. The following steps should be completed from a terminal (macOS/Linux) or from the Anandondas Command Prompt (WINDOWS). Clone repository into directory of choice:
```bash
cd ~/Documents/github
git clone https://github.com/whoi-glider/winkler-titrator
```
4. create a new conda environment:
```bash
cd winkler-env
conda env create -f environment.yml
```
This will create a new python environment called ```winkler-env``` containing all the necessary packages that are listed in the ```environment.yml``` file.

5. Activate the new environment:
```bash
source activate winkler-env # macOS
active winkler-env #git shell in WINDOWS
```
6. Start tritrator GUI:
```bash
python app.py
```
Once setup, only steps 5. and 6. are needed to start the software
