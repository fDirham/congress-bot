import cv2
import pytesseract
from os.path import join
import json
import re
from os import listdir
from os.path import join
from custom_helpers_py.utilities import (
    get_percentage_string,
    remove_non_alphanumeric,
    mkdir_if_not_exists,
)
from custom_helpers_py.img_helpers import convert_pil_to_opencv_img
from custom_helpers_py.get_paths import get_out_folder_house
from pdf2image import convert_from_path
import argparse
from shutil import rmtree


# Mention the installed location of Tesseract-OCR in your system
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


IN_FOLDER_PATH = join(get_out_folder_house(), "documents")
OUT_FOLDER_PATH = join(get_out_folder_house(), "ocr_out")

RAW_CONTENT_FOLDER_PATH = join(OUT_FOLDER_PATH, "raw_content")
PROCESSED_IMAGES_FOLDER_PATH = join(OUT_FOLDER_PATH, "processed_images")
CNG_FOLDER_PATH = join(OUT_FOLDER_PATH, "cng")
INFO_EXTRACT_FOLDER_PATH = join(OUT_FOLDER_PATH, "info_extract")


def main():
    # Get arguments
    parser = argparse.ArgumentParser()

    parser.add_argument("-s", "--start-index", type=int, default=0)
    parser.add_argument("-e", "--end-index", type=int, default=-1)
    parser.add_argument(
        "-r", "--reset", type=bool, default=False, action=argparse.BooleanOptionalAction
    )
    parser.add_argument("--start-year", type=int, default=0)
    parser.add_argument("--end-year", type=int, default=0)
    parser.add_argument("--file-substring", type=str, default="")
    parser.add_argument(
        "--skip-ocr", type=bool, default=False, action=argparse.BooleanOptionalAction
    )
    parser.add_argument(
        "--skip-cng", type=bool, default=False, action=argparse.BooleanOptionalAction
    )
    args, _ = parser.parse_known_args()

    start_index = args.start_index
    end_index = args.end_index
    is_reset = args.reset
    start_year = args.start_year
    end_year = args.end_year
    file_substring = args.file_substring
    is_skip_ocr = args.skip_ocr
    is_skip_cng = args.skip_cng

    # Reset everything
    if is_reset:
        rmtree(OUT_FOLDER_PATH)

    mkdir_if_not_exists(
        [
            OUT_FOLDER_PATH,
            RAW_CONTENT_FOLDER_PATH,
            PROCESSED_IMAGES_FOLDER_PATH,
            CNG_FOLDER_PATH,
            INFO_EXTRACT_FOLDER_PATH,
        ]
    )

    raw_file_names = listdir(IN_FOLDER_PATH)
    if end_index == -1:
        end_index = len(raw_file_names)

    to_process_file_list: list[str] = []
    for i, file_name in enumerate(raw_file_names):
        if start_year:
            file_year = int(file_name[0:4])
            if file_year < start_year:
                continue

        if end_year:
            file_year = int(file_name[0:4])
            if file_year >= end_year:
                continue

        if file_substring:
            if file_substring not in file_name:
                continue

        to_process_file_list.append(file_name)

    to_process_file_list.sort()
    for file_idx, file_name in enumerate(to_process_file_list):
        # Convert pdf to image
        if file_idx < start_index or file_idx >= end_index:
            continue

        print("Processing", file_idx, file_name)
        file_path = join(IN_FOLDER_PATH, file_name)

        # OCR image
        raw_content_list = []
        raw_content_base_name = (
            join(RAW_CONTENT_FOLDER_PATH, file_name.replace(".pdf", "")) + "_page_"
        )

        processed_img_base_name = (
            join(PROCESSED_IMAGES_FOLDER_PATH, file_name.replace(".pdf", "")) + "_page_"
        )

        if not is_skip_ocr:
            page_image_list = convert_from_path(file_path)
            num_pages = len(page_image_list)

            for j, img_obj in enumerate(page_image_list):
                print("> OCR", file_name, "page", j)
                processed_img, raw_content = ocr_img(img_obj)
                raw_content_list.append(raw_content)

                raw_content_file_path = raw_content_base_name + str(j) + ".json"
                with open(raw_content_file_path, "w", encoding="utf-8") as outfile:
                    outfile.write(json.dumps(raw_content, indent=4))

                img_file_path = processed_img_base_name + str(j) + ".png"

                cv2.imwrite(img_file_path, processed_img)

                print("> OCR PAGE DONE", j)

                pct = get_percentage_string(j + 1, 0, num_pages)
                print(pct)
        else:
            raw_content_file_list = listdir(RAW_CONTENT_FOLDER_PATH)
            for raw_file_name in raw_content_file_list:
                raw_file_path = join(RAW_CONTENT_FOLDER_PATH, raw_file_name)
                if raw_file_path.startswith(raw_content_base_name):
                    with open(raw_file_path, "r") as in_file:
                        content = in_file.read()
                    to_add = json.loads(content)
                    raw_content_list.append(to_add)

        # Correct and sort image
        cng_save_path = join(CNG_FOLDER_PATH, file_name.replace(".pdf", "")) + ".json"
        cng_obj = None
        if not is_skip_cng:
            row_list, failed_page_list = cng(raw_content_list)
            cng_obj = {
                "num_rows": len(row_list),
                "failed_page_list": failed_page_list,
                "row_list": row_list,
            }

            with open(cng_save_path, "w", encoding="utf-8") as outfile:
                outfile.write(json.dumps(cng_obj, indent=4))
        else:
            with open(cng_save_path, "r") as in_file:
                content = in_file.read()
                cng_obj: dict = json.loads(content)

        # Extract info
        info_extract_res = extract_info(cng_obj)
        info_extract_save_path = join(
            INFO_EXTRACT_FOLDER_PATH, file_name.replace(".pdf", ".json")
        )

        with open(info_extract_save_path, "w", encoding="utf-8") as outfile:
            outfile.write(json.dumps(info_extract_res, indent=4))

        print("Analysis complete", file_idx, file_name)

        pct = get_percentage_string(file_idx + 1, 0, len(to_process_file_list))
        print(pct)


"""
raw_content return is a list of objects representing the text in a page.
"""


def ocr_img(pil_img):
    img = convert_pil_to_opencv_img(pil_img)

    # Preprocessing the image starts
    # Convert the image to gray scale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Performing OTSU threshold
    _, thresh1 = cv2.threshold(gray, 0, 255, cv2.THRESH_OTSU | cv2.THRESH_BINARY_INV)

    # Specify structure shape and kernel size.
    # Kernel size increases or decreases the area
    # of the rectangle to be detected.
    # A smaller value like (10, 10) will detect
    # each word instead of a sentence.
    rect_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (10, 10))

    # Applying dilation on the threshold image
    dilation = cv2.dilate(thresh1, rect_kernel, iterations=1)

    # Finding contours
    contours, _ = cv2.findContours(dilation, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)

    # Creating a copy of image
    im2 = img.copy()

    raw_content = []
    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)

        # Cropping the text block for giving input to OCR
        padding = 3
        h += 2 * padding
        w += 2 * padding
        x -= padding
        if x < 0:
            x = 0
        y -= padding
        if y < 0:
            y = 0

        # Drawing a rectangle on copied image
        cv2.rectangle(im2, (x, y), (x + w, y + h), (0, 255, 0), 2)

        cropped = im2[y : y + h, x : x + w]

        # Apply OCR on the cropped image
        text: str = pytesseract.image_to_string(cropped, lang="eng")
        text = text.strip()

        # Redo OCR with stricter psm
        is_small = cropped.shape[0] < 50 and cropped.shape[1] < 50
        if not text and is_small:
            text: str = pytesseract.image_to_string(
                cropped, lang="eng", config="--psm 10"
            )
            text = remove_non_alphanumeric(text)
            if len(text) > 2:
                text = ""

        if text:
            raw_content.append({"text": text, "x": x, "y": y, "width": w, "height": h})

    return im2, raw_content


"""
CnG => Correct and group
Take in raw content list of pages and get content grouped by entries in the table

Returns a list of lists, with each item in the list being a list representing features in a table row
"""


ERROR_FULL_STRING_DICT = {"SS": "S"}

ERROR_SUBSTRING_DICT = {
    "CIASS": "CLASS",
    "SUUBHOLDING": "SUBHOLDING",
    "PUBLIICC": "PUBLIC",
    "PUBLIICC": "PUBLIC",
    "PUSBIIC": "PUBLIC",
    "FITINC": "FILING",
    "FIIINC": "FILING",
    "FIUINC": "FILING",
    "FILINC": "FILING",
    "FIUINE": "FILING",
    "FITINE": "FILING",
    "FILINGC": "FILING",
    "FININC": "FILING",
    "SUBHOLDING OR": "SUBHOLDING OF",
    "SUBHOLDING O}": "SUBHOLDING OF",
    "SUBHOLDING O)": "SUBHOLDING OF",
    "SUBHOLDING O:": "SUBHOLDING OF",
    "FIINE STATUS": "FILING STATUS",
    "LOCATTION": "LOCATION",
    "DESCRRIPTION": "DESCRIPTION",
    "DEESCRIPTION": "DESCRIPTION",
    "INE.": "INC.",
    " PLE ": " PLC ",
    "(OFFERINGS": "OFFERINGS",
}


def clean_text(in_text: str):
    to_return = ""
    ALLOWED_CHARS = ["(", ")", "[", "]", " ", "|", "'", "/", "$", ".", "-"]
    for char in in_text:
        if char.isalnum():
            to_return += char
        elif char in ALLOWED_CHARS:
            to_return += char

    return to_return


def fix_closing_chars(in_text: str):
    in_text = in_text.replace("[", "|").replace("]", "|")
    in_text = re.sub(r"\|+", "|", in_text)
    in_text = in_text.replace("|", " | ")

    in_text = re.sub(r"\(+", "(", in_text)
    in_text = re.sub(r"\)+", ")", in_text)
    return in_text


def combine_group_to_string(in_row: list[dict]) -> str:
    to_return = ""
    for text_obj in in_row:
        to_add = text_obj["text"]
        if not to_return.endswith(to_add):
            to_return += " " + to_add

    to_return = to_return.strip()
    to_return = to_return.removeprefix("|")
    to_return = to_return.strip()

    return to_return


def cng(raw_content_list: list[list[dict]]):
    # line_list is a list full of lines.
    # A line is a list of text objects

    to_return_row_list = []
    failed_page_list = []
    for page_num, page_list in enumerate(raw_content_list):

        # Fix text
        page_fixed_list = []
        for obj in page_list:
            new_text: str = obj["text"]
            new_text = new_text.upper()

            # Standardize []
            new_text = fix_closing_chars(new_text)
            new_text = new_text.replace("\n", " ")
            new_text = clean_text(new_text)

            # Remove newlines
            new_text = re.sub(" +", " ", new_text)
            new_text = new_text.strip()

            # Error full strings
            if ERROR_FULL_STRING_DICT.get(new_text):
                new_text = ERROR_FULL_STRING_DICT[new_text]

            # Error substrings
            for in_key, in_val in ERROR_SUBSTRING_DICT.items():
                new_text = new_text.replace(in_key, in_val)

            obj["text"] = new_text
            page_fixed_list.append(obj)

        # Sort by y value
        page_fixed_list = sorted(page_fixed_list, key=lambda obj: obj["y"])

        # Get horizontal lines
        hor_line_list: list[list[dict]] = []
        last_y_start = 0
        LINE_Y_THRESHOLD = 5

        for text_obj in page_fixed_list:
            if last_y_start < 1:
                last_y_start = text_obj["y"]
                hor_line_list.append([text_obj])
                continue

            obj_y = text_obj["y"]
            if obj_y <= last_y_start + LINE_Y_THRESHOLD:
                hor_line_list[-1].append(text_obj)
            else:
                last_y_start = obj_y
                hor_line_list.append([text_obj])

        # Sort each line by x value
        tmp_list = []
        for hor_line in hor_line_list:
            to_add = sorted(hor_line, key=lambda obj: obj["x"])
            tmp_list.append(to_add)
        hor_line_list = tmp_list

        # Filter some lines out
        START_CROP_SUBSTRING_LIST = ["TRANSACTIONS"]
        END_CROP_SUBSTRING_LIST = [
            "COMPLETE LIST OF ASSET TYPE ABBREVIATIONS",
            "ASSET CLASS DETA",
        ]
        start_idx = 0
        end_idx = len(hor_line_list)

        for line_idx, hor_line in enumerate(hor_line_list):
            combined_line = combine_group_to_string(hor_line)
            for substr in START_CROP_SUBSTRING_LIST:
                if substr in combined_line:
                    start_idx = line_idx
                    continue
            for substr in END_CROP_SUBSTRING_LIST:
                if substr in combined_line:
                    if line_idx < end_idx:
                        end_idx = line_idx
                    continue

        hor_line_list = hor_line_list[start_idx:end_idx]

        # Get interesting lines
        header_line = None
        interesting_lines = []
        INTERESTING_LINES_MIN_OBJECT_COUNT = 4
        IS_HEADER_LINE_SUBSTRING = "OWNER ASSET TRANSACTION DATE"
        for hor_line in hor_line_list:
            is_interesting = len(hor_line) >= INTERESTING_LINES_MIN_OBJECT_COUNT
            if is_interesting:
                combined_line = combine_group_to_string(hor_line)

                is_header = IS_HEADER_LINE_SUBSTRING in combined_line

                if is_header:
                    header_line = hor_line
                # Append to interesting lines only if header is found already
                elif header_line:
                    interesting_lines.append(hor_line)

        if not header_line:
            failed_page_list.append(page_num)
            continue

        # Determine row y coords
        row_start_y_list = []
        for hor_line in interesting_lines:
            y_coord = hor_line[0]["y"]
            row_start_y_list.append(y_coord)

        # Put content in rows
        # TODO: This is inefficient but lmao. Should fix
        row_list = []
        num_rows = len(row_start_y_list)
        for j, y_start in enumerate(row_start_y_list):
            y_end = None
            if j + 1 < num_rows:
                y_end = row_start_y_list[j + 1]

            curr_row = []
            if j == 0:
                # TODO: Add functionality to add left overs
                pass
            for hor_line in hor_line_list:
                hor_line_y = hor_line[0]["y"]
                if hor_line_y < y_start:
                    continue
                if y_end and hor_line_y >= y_end:
                    continue

                curr_row += hor_line

            row_list.append(curr_row)

        # Use header info to segment row list to cells
        column_start_x_list = []
        for text_obj in header_line:
            x_coord = text_obj["x"]
            val = text_obj["text"]
            column_start_x_list.append({"x": x_coord, "col_name": val})

        tmp_list = []
        COL_X_RANGE = 5
        num_columns = len(column_start_x_list)
        for row in row_list:
            column_dict: dict[str, list[dict]] = {}

            for text_obj in row:
                obj_x = text_obj["x"]
                col_name = None

                # Add page to text_obj
                text_obj["page_num"] = page_num

                for j, col_obj in enumerate(column_start_x_list):
                    col_x = col_obj["x"]
                    col_start = col_x - COL_X_RANGE
                    col_end = None
                    if j + 1 < num_columns:
                        col_end = column_start_x_list[j + 1]["x"] - COL_X_RANGE

                    if col_start > obj_x:
                        continue
                    if col_end and col_end <= obj_x:
                        continue
                    col_name = col_obj["col_name"]

                if col_name:
                    column_entry = column_dict.get(col_name)
                    if not column_entry:
                        column_dict[col_name] = [text_obj]
                    else:
                        column_entry.append(text_obj)

            tmp_list.append(column_dict)
        row_list = tmp_list

        to_return_row_list += row_list

    return to_return_row_list, failed_page_list


VALID_OWNER_LIST = ["JT", "DC", "SP"]
DESC_START_LINE_LIST = [
    "FILING STATUS",
    "SUBHOLDING OF",
    "DESCRIPTION",
    "COMMENT",
    "LOCATION:",
]


def extract_info(in_cng_obj: dict):
    to_return_extract_info_list = []
    row_list: list[dict] = in_cng_obj["row_list"]
    for row_obj in row_list:
        owner_val = None
        owner_col: list | None = row_obj.get("OWNER")
        if owner_col:
            owner_val = owner_col[0]["text"]
            if owner_val not in VALID_OWNER_LIST:
                owner_val = None

        asset_name_val = None
        asset_desc_val = None
        ticker_val = None
        asset_type_val = None
        asset_desc_col: list | None = row_obj.get("ASSET")
        if asset_desc_col:
            combined_line = combine_group_to_string(asset_desc_col)
            desc_start_idx = -1
            for start_substr in DESC_START_LINE_LIST:
                tmp_idx = combined_line.find(start_substr)
                if desc_start_idx == -1 or (tmp_idx > -1 and tmp_idx < desc_start_idx):
                    desc_start_idx = tmp_idx

            if desc_start_idx == -1:
                asset_name_val = combined_line
            else:
                asset_name_val = combined_line[0:desc_start_idx].strip()
                asset_desc_val = combined_line[desc_start_idx:].strip()

            # Get ticker
            ticker = re.search(r"(?s:.*)\((.*?)\)", asset_name_val)
            if ticker:
                ticker_val = ticker.group(1)

            # Get asset type
            asset_type = re.search(r"(?s:.*)\| (.*?) \|", asset_name_val)
            if asset_type:
                asset_type_val = asset_type.group(1)
                asset_type_val = asset_type_val.replace("|", "").strip()

        tx_type_val = None
        tx_type_col: list | None = row_obj.get("TRANSACTION")
        if tx_type_col:
            tx_type_val = tx_type_col[0]["text"]

        tx_date_val = None
        tx_date_col: list | None = row_obj.get("DATE")
        if tx_date_col:
            tx_date_val = tx_date_col[0]["text"]

        notif_date_val = None
        notif_date_col: list | None = row_obj.get("NOTIFICATION")
        if notif_date_col:
            notif_date_val = notif_date_col[0]["text"]

        amount_val = None
        amount_col: list | None = row_obj.get("AMOUNT")
        if amount_col:
            amount_val = amount_col[0]["text"]

        to_add = {
            "asset_name": asset_name_val,
            "ticker": ticker_val,
            "asset_type": asset_type_val,
            "tx_type": tx_type_val,
            "owner": owner_val,
            "tx_date": tx_date_val,
            "notif_date": notif_date_val,
            "amount": amount_val,
            "asset_desc": asset_desc_val,
        }
        to_return_extract_info_list.append(to_add)

    return to_return_extract_info_list


EXTRA_INFO_LINE_VAL = "extra_info"
LINE_SPLIT_VAL = "--new_line--"


# if "FILING ID" in content_lines[0] and "PERIODIC TRANS" in content_lines[1]:
#     return True


CROP_START_STR_LIST = [
    "GAINS > $200?",
    "GAINS > $200",
    "NOTIFICATION AMOUNT DATE",
    "NOTIFICATION DATE AMOUNT",
]


CROP_END_STR_LIST = [
    "* FOR THE COMPLETE LIST",
    "INITIAL PUBLIC OFFER",
    "ASSET CLASS DETA",
]

TABLE_HEADER_LIST = ["OWNER ASSET TRANSACTION", "ID OWNER ASSET TRANSACTION"]


if __name__ == "__main__":
    main()
