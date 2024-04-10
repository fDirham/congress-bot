from os import listdir
from os.path import join, splitext
from custom_helpers_py.utilities import read_json_file
from shutil import copyfile
import img2pdf
from PIL import Image


"""
Get all non jsons from senate
Get all blanks from house ocr info extract
Start at 2014
"""

HOUSE_INFO_EXTRACT_FP = "./.outFiles/house/ocr_out/info_extract"
HOUSE_DOCS_FP = "./.outFiles/house/documents"
SENATE_DOCS_FP = "./.outFiles/senate/documents"
START_YEAR = "2014"

master_file_list: tuple[str, str] = []
house_file_list = listdir(HOUSE_INFO_EXTRACT_FP)
for file_name in house_file_list:
    if not file_name.startswith(START_YEAR):
        continue
    fp = join(HOUSE_INFO_EXTRACT_FP, file_name)
    obj = read_json_file(fp)
    if len(obj) == 0:
        file_name = file_name.replace(".json", ".pdf")
        to_add_fp = join(HOUSE_DOCS_FP, file_name)
        master_file_list.append((to_add_fp, file_name))

senate_file_list = listdir(SENATE_DOCS_FP)
for file_name in senate_file_list:
    if not file_name.startswith(START_YEAR) or file_name.endswith(".json"):
        continue
    fp = join(SENATE_DOCS_FP, file_name)
    master_file_list.append((fp, file_name))


def img_to_pdf(img_fp: str, dst_fp: str):
    image = Image.open(img_fp)

    # converting into chunks using img2pdf
    pdf_bytes = img2pdf.convert(image.filename)

    # opening or creating pdf file
    file = open(dst_fp, "wb")

    # writing pdf files with chunks
    file.write(pdf_bytes)

    # closing image file
    image.close()

    # closing pdf file
    file.close()


OUT_FOLDER_PATH = "./.outFiles/manual_entry/documents"
for obj in master_file_list:
    fp, file_name = obj
    if not fp.endswith("pdf"):
        ext = splitext(file_name)[1]
        dst_fp = join(OUT_FOLDER_PATH, file_name.replace(ext, ".pdf"))
        img_to_pdf(fp, dst_fp)
        continue

    dst = join(OUT_FOLDER_PATH, file_name)
    copyfile(fp, dst)
