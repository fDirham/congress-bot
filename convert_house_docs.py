from pdf2image import convert_from_path
from custom_helpers_py.get_paths import get_out_folder_house
from custom_helpers_py.cli_args_helpers import get_args
from custom_helpers_py.utilities import get_percentage_string
from os.path import join
from os import listdir

cli_args = get_args()
start_idx = cli_args[0] or 0
start_idx = int(start_idx)

DOCUMENTS_FOLDER = join(get_out_folder_house(), "documents")
OUT_IMAGES_FOLDER = join(get_out_folder_house(), "doc_images")

doc_file_list = listdir(DOCUMENTS_FOLDER)
doc_file_list.sort()
list_len = len(doc_file_list)
for i, filename in enumerate(doc_file_list):
    if i < int(start_idx):
        continue

    print("Converting", i, get_percentage_string(i + 1, start_idx, list_len))
    print(filename)
    try:
        file_path = join(DOCUMENTS_FOLDER, filename)
        images = convert_from_path(file_path)
        base_name = filename.replace(".pdf", "")

        for i, img in enumerate(images):
            print("Saved page", i)
            out_path = join(OUT_IMAGES_FOLDER, base_name + "_" + str(i) + ".png")
            img.save(out_path)

        print("Finished", i)
    except Exception as error:
        print("ERROR")
        print(error)
        print(i, filename)
