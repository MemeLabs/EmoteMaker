# EmoteMaker
## What is this for?
EmoteMaker is used to create a framestrip and apng in various resolutions from a set of images using FFmpeg.
It creates a framestrip and apng for the original resolution of images used as input, as well as a 50% and 25% resolution version, 
i.e. if the input is 128px it creates a 128px, 64px and 32px framestrip and apng version.

EmoteMaker also supports setting the animation speed for the apng.
## Requirements
- Python 3.7+
- FFmpeg

## Development
Install locally:
```
pip install -e .
```

## Installation
```
pip install -e git+https://github.com/MemeLabs/EmoteMaker.git#egg=emote_maker
```
