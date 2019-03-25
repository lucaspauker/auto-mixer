Here is a guide on how to install the dependencies for this project:

Install python3:
  https://www.python.org/downloads/

First install pip (package manager):
  easy_install pip

psutil:
  pip install psutil

aubio:
  python -m pip install aubio

eyed3:
  pip install eyeD3

numpy:
  pip install numpy

ctcsound:
  For Mac:
    Install homebrew: http://www.brew.sh
    brew tap kunstmusik/csound
    brew install --HEAD csound
  Unfortunately, this package is difficult to install. Here is more info: https://github.com/csound/csound/blob/develop/BUILD.md

pygame:
  python3 -m pip install -U pygame --user
  (see here for more specific instructions: https://www.pygame.org/wiki/GettingStarted)

pydub:
  pip install pydub

--

Here are all the packages except ctcsound in one place so you can copy and paste:

pip install psutil
python -m pip install aubio
pip install eyeD3
pip install numpy
python3 -m pip install -U pygame --user
pip install pydub
