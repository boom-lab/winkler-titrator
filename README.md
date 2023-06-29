[![DOI](https://zenodo.org/badge/116846502.svg)](https://zenodo.org/badge/latestdoi/116846502)

# winkler-titrator
software to control WHOI Nicholson Lab Winkler titrator

## Installation instructions:

recommended software pre-installed
Anaconda or miniconda (https://conda.io/docs/user-guide/install/download.html)

1. You should have git installed.  For MacOS using Homebrew package manager, you can do this from terminal:
```bash
$ brew install git
```
2. If you don't want a full Anacondas install, you can install miniconda for python 3.x: [(Instructions)](https://conda.io/miniconda.html)
3. The following steps should be completed from a terminal (macOS/Linux) or from the Anandondas Command Prompt (WINDOWS). Clone repository into directory of choice:
```bash
cd ~/Documents/github
git clone https://github.com/whoi-glider/winkler-titrator
```
4. create a new conda environment:
```bash
cd winkler-titrator
conda env create -f environment.yml
```
This will create a new python environment called ```winkler-fbs``` containing all the necessary packages that are listed in the ```environment.yml``` file.

5. Activate the new environment:
```bash
conda activate winkler-fbs # macOS
active winkler-fbs #git shell in WINDOWS
```
6. Start titrator GUI:
```bash
fbs run
```
Once setup, only steps 5. and 6. are needed to start the software.
