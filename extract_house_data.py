import cv2
import pytesseract
from custom_helpers_py.get_paths import get_out_folder_house
from custom_helpers_py.cli_args_helpers import get_args
from custom_helpers_py.utilities import get_percentage_string
from os.path import join
from os import listdir

cli_args = get_args()
start_idx = cli_args[0] or 0
start_idx = int(start_idx)

# Tesseract path
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

IMAGES_FOLDER = join(get_out_folder_house(), "doc_images")
OUT_TEXT_EXTRACTS_FOLDER = join(get_out_folder_house(), "text_extracts")

img_file_list = listdir(IMAGES_FOLDER)
img_file_list.sort()
list_len = len(img_file_list)
for i, filename in enumerate(img_file_list):
    if i < start_idx:
        continue

    print("Converting", i, get_percentage_string(i + 1, start_idx, list_len))
    print(filename)
    try:
        file_path = join(IMAGES_FOLDER, filename)
        # read image
        img = cv2.imread(file_path)

        # get grayscale image
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Configuration
        config = "-l eng — oem 3 — psm 3"
        # pytessercat
        text = pytesseract.image_to_string(img, config=config)

        base_name = filename.replace(".png", "")
        out_path = join(OUT_TEXT_EXTRACTS_FOLDER, base_name + ".txt")

        with open(out_path, "w") as outfile:
            outfile.write(text)

        print("Finished", i)
    except Exception as error:
        print("ERROR")
        print(error)
        print(i, filename)
