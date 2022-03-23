# MaxGrooVAE

March 2022 Universitat Pompeu Fabra - Computational Creativity Class Project

Recep Oğuz Araz: oguza97@gmail.com
Julian Lenz: julianlenz981@gmail.com

This repository contains a GrooVAE-Max for Live duo for taking a constant velocity groove pattern from the user, turning it to a 2 bar drum composition and playing it back in Ableton Live.

It works only with 4-4 time signature for 2 bars with 1/16th note steps. The system can work in real-time in the sense that the composition of the next 2 bars would be completed before 2 bars worth of time until about 150 BPMs.

Installing Instructions:

1) It can be hard to install magenta on your computer. Follow the instructions from https://github.com/magenta/magenta

Running Instructions:

1) Activate the virtual environments and run the python code using

python MaxGrooVAE.py --send-ip=<Max IP> --send-port=<Max Port> --receive-ip=<Local IP> --receive-port=<Local port>

2) Open the Max patch and enter the ports as above and IPs

3) Draw your groove, specify some parameters and send it!

4) Playbak from Ableton.
