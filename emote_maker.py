import argparse
import imghdr
import os
import struct
import subprocess
import time
from typing import List
from typing import Optional
from typing import Tuple

from PIL import Image

CWD = os.path.dirname(os.path.realpath(__file__))
PATH_FOLDER_INPUT = os.path.join(CWD, "inputFrames")
PATH_FOLDER_OUTPUT = os.path.join(CWD, "output")
PATH_FOLDER_WORKING_COPY = os.path.join(CWD, "temp")
SCALINGS: List[int] = [1, 2, 4]


class EmoteMaker:
    program: Optional[str] = None
    desired_frame_delay: float = 0.07
    number_of_loops: int = 0
    reverse_animation: bool = False

    def __init__(self) -> None:
        if not os.path.exists(PATH_FOLDER_INPUT):
            os.mkdir(PATH_FOLDER_INPUT)
        if not os.path.exists(PATH_FOLDER_OUTPUT):
            os.mkdir(PATH_FOLDER_OUTPUT)
        if not os.path.exists(PATH_FOLDER_WORKING_COPY):
            os.mkdir(PATH_FOLDER_WORKING_COPY)

        if os.path.isfile(os.path.join(CWD, "ffmpeg.exe")):
            self.program = os.path.join(CWD, "ffmpeg")
        else:
            self.program = "ffmpeg"

    @staticmethod
    def create_filename(filename: str) -> str:
        while len(filename) < 3:
            filename = "0" + filename
        return filename + ".png"

    @staticmethod
    def get_image_size(fname: str) -> Optional[Tuple[int, int]]:
        """Determine the image type of fhandle and return its size. from draco"""

        with open(fname, "rb") as fhandle:
            head = fhandle.read(24)
            if len(head) != 24:
                return None
            if imghdr.what(fname) == "png":
                check = struct.unpack(">i", head[4:8])[0]
                if check != 0x0D0A1A0A:
                    return None
                width, height = struct.unpack(">ii", head[16:24])
            elif imghdr.what(fname) == "gif":
                width, height = struct.unpack("<HH", head[6:10])
            elif imghdr.what(fname) == "jpeg":
                try:
                    fhandle.seek(0)  # Read 0xff next
                    size = 2
                    ftype = 0
                    while not 0xC0 <= ftype <= 0xCF:
                        fhandle.seek(size, 1)
                        byte = fhandle.read(1)
                        while ord(byte) == 0xFF:
                            byte = fhandle.read(1)
                        ftype = ord(byte)
                        size = struct.unpack(">H", fhandle.read(2))[0] - 2
                    # We are at a SOFn block
                    fhandle.seek(1, 1)  # Skip `precision' byte.
                    height, width = struct.unpack(">HH", fhandle.read(4))
                except Exception:  # IGNORE:W0703
                    return None
            else:
                return None
            return width, height

    @staticmethod
    def cleanup(path: str) -> None:
        for file in os.listdir(path):
            os.remove(os.path.join(path, file))

    def determine_framerate(self) -> int:
        return round(1 / self.desired_frame_delay)

    def build_framestrip(self, basename: str) -> None:
        frame_size = EmoteMaker.get_image_size(
            os.path.join(
                PATH_FOLDER_WORKING_COPY,
                os.listdir(PATH_FOLDER_WORKING_COPY)[0],
            )
        )
        if not frame_size or not self.program:
            return None

        count = len(os.listdir(PATH_FOLDER_WORKING_COPY))
        name = f"{basename}_{str(frame_size[1])}.png"
        param = (
            f" -i {os.path.join(PATH_FOLDER_WORKING_COPY, '%03d.png')}"
            f" -filter_complex scale={str(frame_size[0])}:-1,"
            f"tile={str(count)}x1 {os.path.join(PATH_FOLDER_OUTPUT, name)}"
        )
        subprocess.call(self.program + param, shell=True)

    def build_apng(self, basename: str) -> None:
        frame_size = EmoteMaker.get_image_size(
            os.path.join(
                PATH_FOLDER_WORKING_COPY,
                os.listdir(PATH_FOLDER_WORKING_COPY)[0],
            )
        )
        if not frame_size or not self.program:
            return None

        name = f"{basename}_ANIM_{str(frame_size[1])}.png"
        loop_param = f" -plays {self.number_of_loops} -vf setpts=PTS-STARTPTS"

        param = (
            f" -framerate {self.determine_framerate()}"
            f" -i {os.path.join(PATH_FOLDER_WORKING_COPY, '%03d.png')}{loop_param}"
            f" -f apng {os.path.join(PATH_FOLDER_OUTPUT, name)}"
        )
        subprocess.call(self.program + param, shell=True)

    def create_working_image(self, factor_scaling: float) -> None:
        files = os.listdir(PATH_FOLDER_INPUT)

        if self.reverse_animation:
            files.reverse()

        for i in range(len(files)):
            file = files[i]
            print(file)
            frame = Image.open(os.path.join(PATH_FOLDER_INPUT, str(file)))
            frame_size = EmoteMaker.get_image_size(
                os.path.join(PATH_FOLDER_INPUT, str(file))
            )
            if not frame_size:
                return None

            new_frame = frame.resize(
                (
                    int(frame_size[0] / factor_scaling),
                    int(frame_size[1] / factor_scaling),
                )
            )
            new_name = EmoteMaker.create_filename(str(i))
            new_frame.save(os.path.join(PATH_FOLDER_WORKING_COPY, new_name))

    def run(self) -> None:
        for scaling in SCALINGS:
            self.create_working_image(scaling)
            basename = str(time.time())
            # create framestrip
            self.build_framestrip(basename)
            # create apng
            self.build_apng(basename)


def print_examples() -> None:
    print("####################### Examples #######################\n")
    print(
        "Default settings(0.07s delay between each frame for the apng,"
        " animation loops indefinitely"
    )
    print("\t\t-> emote-maker\n")
    print("Custom delay of 0.5 seconds between each frame for the apng")
    print("\t\t-> emote-maker -d 0.5\n")
    print("Only loop once")
    print("\t\t-> emote-maker -l 1\n")
    print("Reverse the animation")
    print("\t\t-> emote-maker -r\n")
    print("Loop 3 times with a delay of 1.5 seconds between each frame for the apng")
    print("\t\t-> emote-maker -l 3 -d 1.5\n")
    print(
        "Loop 3 times with a delay of 1.5 seconds between each frame for the apng and reverse the animation"
    )
    print("\t\t-> emote-maker -l 3 -d 1.5 -r\n")
    print("==> The order in which the d/l/r flags are used does not matter\n")
    print("########################################################")


def main() -> int:
    argumentparser = argparse.ArgumentParser(
        description="Calls ffmpeg to create resized images, framestrips and apng for the files in the input folder"
    )
    argumentparser.add_argument(
        "-e", action="store_true", required=False, help="Show examples"
    )
    argumentparser.add_argument(
        "-l",
        required=False,
        type=int,
        help="Set number of loops for the apng. Default is 0 which loops forever",
    )
    argumentparser.add_argument(
        "-d",
        required=False,
        type=float,
        help="Sets the delay between each frame for the apng. Default is 0.07s",
    )
    argumentparser.add_argument(
        "-r", action="store_true", required=False, help="Reverses the animation"
    )
    args, leftovers = argumentparser.parse_known_args()

    if len(leftovers) != 0:
        print(f"Unrecognized arguments: {leftovers}")
        print("Use 'Emotemaker.py -h' for available arguments and usage")
        return 1

    if args.e and args.e:
        print_examples()
        return 0

    em = EmoteMaker()
    if args.l:
        print(f"Setting number of loops to {args.l}")
        em.number_of_loops = int(args.l)

    if args.d:
        print(f"Setting frame delay to {args.d}s")
        em.desired_frame_delay = float(args.d)

    if args.r:
        print("Reversing animation")
        em.reverse_animation = True

    em.run()
    return 0


if __name__ == "__main__":
    exit(main())
