# Soccer Clip Graphic Overlay System
Designed to provide an efficient and user-friendly solution for applying aesthetic overlays for soccer clips. Streamline the process of adding graphics, significantly reducing time and effort required compared to traditional manual methods.

# Features
Graphic Overlay System: Apply between two graphic packs including graphic elements such as scoreboard, introduction for match information and highlight information.

Customizable Templates: Ability to design and utilize customizable overlays.

Console user interface: A simple console-based interface that allows users to easily configure and apply a graphic overlay to videos.

# How to run
!! Requires MiniConda or Anaconda installed for handling conda environments !!

in a terminal, activate conda environment
    conda activate {filepath}/activate_me

Install python dependencies
    python -m pip install -r requirements.txt

Run reels.py
    python .\reels.py

# If MiniConda or Anaconda is NOT installed
Have a look at 'reels.py', module which is responsible for handling user-requests and commencing the process of applying a graphic overlay
'graphics.py'-module for the methods of applying graphics to video

At last, have a look at mp4-files in ./video. Examples are:
    