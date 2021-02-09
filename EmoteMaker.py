import os
import subprocess
import struct
import imghdr
import time
import sys
import shutil
from PIL import Image
import argparse


class EmoteMaker:
    CWD = os.path.dirname(os.path.realpath(__file__))
    FOLDER_INPUT = "inputFrames"
    PATH_FOLDER_INPUT = os.path.join(CWD, FOLDER_INPUT)
    FOLDER_OUTPUT = "output"
    PATH_FOLDER_OUTPUT = os.path.join(CWD, FOLDER_OUTPUT)
    FOLDER_WORKING_COPY = "temp"
    PATH_FOLDER_WORKING_COPY = os.path.join(CWD, FOLDER_WORKING_COPY)
    SCALINGS = [1, 2, 4]

    program = None
    desired_frame_delay = 0.07
    number_of_loops = 0
    reverse_animation = False

    @staticmethod
    def init():
        if not os.path.exists(EmoteMaker.PATH_FOLDER_INPUT):
            os.mkdir(EmoteMaker.PATH_FOLDER_INPUT)
        if not os.path.exists(EmoteMaker.PATH_FOLDER_OUTPUT):
            os.mkdir(EmoteMaker.PATH_FOLDER_OUTPUT)
        if not os.path.exists(EmoteMaker.PATH_FOLDER_WORKING_COPY):
            os.mkdir(EmoteMaker.PATH_FOLDER_WORKING_COPY)

        if os.path.isfile(os.path.join(EmoteMaker.CWD, "ffmpeg.exe")):
            EmoteMaker.program = os.path.join(EmoteMaker.CWD, "ffmpeg")
        else:
            EmoteMaker.program = "ffmpeg"

    @staticmethod
    def create_filename(filename):
        while len(filename) < 3:
            filename = "0" + filename
        filename = filename + ".png"
        return filename

    @staticmethod
    def get_image_size(fname):
        """Determine the image type of fhandle and return its size. from draco"""

        with open(fname, 'rb') as fhandle:
            head = fhandle.read(24)
            if len(head) != 24:
                return
            if imghdr.what(fname) == 'png':
                check = struct.unpack('>i', head[4:8])[0]
                if check != 0x0d0a1a0a:
                    return
                width, height = struct.unpack('>ii', head[16:24])
            elif imghdr.what(fname) == 'gif':
                width, height = struct.unpack('<HH', head[6:10])
            elif imghdr.what(fname) == 'jpeg':
                try:
                    fhandle.seek(0)  # Read 0xff next
                    size = 2
                    ftype = 0
                    while not 0xc0 <= ftype <= 0xcf:
                        fhandle.seek(size, 1)
                        byte = fhandle.read(1)
                        while ord(byte) == 0xff:
                            byte = fhandle.read(1)
                        ftype = ord(byte)
                        size = struct.unpack('>H', fhandle.read(2))[0] - 2
                    # We are at a SOFn block
                    fhandle.seek(1, 1)  # Skip `precision' byte.
                    height, width = struct.unpack('>HH', fhandle.read(4))
                except Exception:  # IGNORE:W0703
                    return
            else:
                return
            return width, height

    @staticmethod
    def cleanup(path):
        for file in os.listdir(path):
            os.remove(os.path.join(path, file))

    @staticmethod
    def determine_framerate():
        return round(1 / EmoteMaker.desired_frame_delay)

    @staticmethod
    def build_framestrip(basename):
        frame_size = EmoteMaker.get_image_size(
            os.path.join(EmoteMaker.PATH_FOLDER_WORKING_COPY, os.listdir(EmoteMaker.PATH_FOLDER_WORKING_COPY)[0]))
        count = len(os.listdir(EmoteMaker.PATH_FOLDER_WORKING_COPY))
        name = f"{basename}_{str(frame_size[1])}.png"
        param = f" -i {os.path.join(EmoteMaker.PATH_FOLDER_WORKING_COPY, '%03d.png')}" \
                f" -filter_complex scale={str(frame_size[0])}:-1," \
                f"tile={str(count)}x1 {os.path.join(EmoteMaker.PATH_FOLDER_OUTPUT, name)}"
        subprocess.call(EmoteMaker.program + param, shell=True)

    @staticmethod
    def build_apng(basename):
        frame_size = EmoteMaker.get_image_size(
            os.path.join(EmoteMaker.PATH_FOLDER_WORKING_COPY, os.listdir(EmoteMaker.PATH_FOLDER_WORKING_COPY)[0]))

        name = f"{basename}_ANIM_{str(frame_size[1])}.png"
        loop_param = f" -plays {EmoteMaker.number_of_loops} -vf setpts=PTS-STARTPTS"

        param = f" -framerate {EmoteMaker.determine_framerate()}" \
                f" -i {os.path.join(EmoteMaker.PATH_FOLDER_WORKING_COPY, '%03d.png')}{loop_param}" \
                f" -f apng {os.path.join(EmoteMaker.PATH_FOLDER_OUTPUT, name)}"
        subprocess.call(EmoteMaker.program + param, shell=True)

    @staticmethod
    def create_working_image(factor_scaling):
        files = os.listdir(EmoteMaker.PATH_FOLDER_INPUT)

        if EmoteMaker.reverse_animation:
            files.reverse()

        for i in range(len(files)):
            file = files[i]
            print(file)
            frame = Image.open(os.path.join(EmoteMaker.PATH_FOLDER_INPUT, str(file)))
            frame_size = EmoteMaker.get_image_size(os.path.join(EmoteMaker.PATH_FOLDER_INPUT, str(file)))
            new_frame = frame.resize((int(frame_size[0] / factor_scaling), int(frame_size[1] / factor_scaling)))
            new_name = EmoteMaker.create_filename(str(i))
            new_frame.save(os.path.join(EmoteMaker.PATH_FOLDER_WORKING_COPY, new_name))

    @staticmethod
    def run():
        for scaling in EmoteMaker.SCALINGS:
            EmoteMaker.create_working_image(scaling)
            basename = str(time.time())
            # create framestrip
            EmoteMaker.build_framestrip(basename)
            # create apng
            EmoteMaker.build_apng(basename)
            #EmoteMaker.cleanup(EmoteMaker.PATH_FOLDER_WORKING_COPY)
        #EmoteMaker.cleanup(EmoteMaker.PATH_FOLDER_INPUT)


def print_examples():
    print("####################### Examples #######################\n")
    print("Default settings(0.07s delay between each frame for the apng,"
          " animation loops indefinitely")
    print("\t\t-> EmoteMaker.py\n")
    print("Custom delay of 0.5 seconds between each frame for the apng")
    print("\t\t-> EmoteMaker.py -d 0.5\n")
    print("Only loop once")
    print("\t\t-> EmoteMaker.py -l 1\n")
    print("Reverse the animation")
    print("\t\t-> EmoteMaker.py -r\n")
    print("Loop 3 times with a delay of 1.5 seconds between each frame for the apng")
    print("\t\t-> EmoteMaker.py -l 3 -d 1.5\n")
    print("Loop 3 times with a delay of 1.5 seconds between each frame for the apng and reverse the animation")
    print("\t\t-> EmoteMaker.py -l 3 -d 1.5 -r\n")
    print("==> The order in which the d/l/r flags are used does not matter\n")
    print("########################################################")


def inits_arg():
    argumentparser = argparse.ArgumentParser(
        description='Calls ffmpeg to create resized images, framestrips and apng for the files in the input folder')
    argumentparser.add_argument('-e',
                                action='store_true',
                                required=False,
                                help='Show examples')
    argumentparser.add_argument('-l',
                                required=False,
                                type=int,
                                help='Set number of loops for the apng. Default is 0 which loops forever')
    argumentparser.add_argument('-d',
                                required=False,
                                type=float,
                                help='Sets the delay between each frame for the apng. Default is 0.07s')
    argumentparser.add_argument('-r',
                                action='store_true',
                                required=False,
                                help='Reverses the animation')
    args, leftovers = argumentparser.parse_known_args()

    if len(leftovers) != 0:
        print(f"Unrecognized arguments: {leftovers}")
        print(f"Use 'Emotemaker.py -h' for available arguments and usage")
        sys.exit(1)

    if args.e is not None and args.e is True:
        print_examples()
        sys.exit(0)

    if args.l is not None:
        print(f"Setting number of loops to {args.l}")
        EmoteMaker.number_of_loops = int(args.l)

    if args.d is not None:
        print(f"Setting frame delay to {args.d}s")
        EmoteMaker.desired_frame_delay = float(args.d)

    if args.r is not None and args.r is True:
        print("Reversing animation")
        EmoteMaker.reverse_animation = True


if __name__ == "__main__":
    inits_arg()
    EmoteMaker.init()
    EmoteMaker.run()
