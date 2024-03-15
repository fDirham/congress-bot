from ocr_extract_house_data import get_content_lines
from os.path import join
import json
from os import listdir
from os.path import join
from custom_helpers_py.utilities import get_percentage_string, remove_non_alphanumeric
from custom_helpers_py.get_paths import get_out_folder_house
import argparse


def main():
    # Get arguments
    parser = argparse.ArgumentParser()

    parser.add_argument("-s", "--start-index", type=int, default=0)
    parser.add_argument("-e", "--end-index", type=int, default=-1)
    parser.add_argument("--doc-str", type=str)
    args, _ = parser.parse_known_args()

    start_index = args.start_index
    end_index = args.end_index
    doc_str = args.doc_str

    OUT_FOLDER_PATH = get_out_folder_house()
    RAW_CONTENT_FOLDER_PATH = join(OUT_FOLDER_PATH, "raw_content")
    INFO_EXTRACT_FOLDER_PATH = join(OUT_FOLDER_PATH, "info_extract")

    file_names = listdir(RAW_CONTENT_FOLDER_PATH)
    file_names.sort()
    if end_index == -1:
        end_index = len(file_names)

    for i, file_name in enumerate(file_names):
        if i < start_index or i >= end_index:
            continue

        if doc_str and doc_str not in file_name:
            continue

        print("Processing", i, file_name)

        raw_content = ""
        with open(
            join(RAW_CONTENT_FOLDER_PATH, file_name), "r", encoding="utf-8"
        ) as raw_file:
            raw_content = raw_file.read()

        if raw_content:
            new_content_lines = get_content_lines(raw_content)

            # Save extract
            info_extract_file_path = join(
                INFO_EXTRACT_FOLDER_PATH, file_name.replace("txt", "json")
            )
            with open(info_extract_file_path, "w", encoding="utf-8") as outfile:
                outfile.write(json.dumps(new_content_lines, indent=4))
            print("Done", i, file_name)
        else:
            print("Skipped, no content", i, file_name)

        pct = get_percentage_string(i + 1, start_index, end_index)
        print(pct)


if __name__ == "__main__":
    main()
