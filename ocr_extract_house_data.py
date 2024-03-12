import cv2
import pytesseract
from os.path import join
import json
import re
from os import listdir
from os.path import join
from custom_helpers_py.utilities import get_percentage_string, remove_non_alphanumeric
from custom_helpers_py.img_helpers import convert_pil_to_opencv_img
from pdf2image import convert_from_path
from PIL import Image
from custom_helpers_py.get_paths import get_out_folder_house
import argparse


# Mention the installed location of Tesseract-OCR in your system
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


OWNER_PREFIX_LIST = ["JT", "DC", "SP"]

AMOUNT_RANGE_LIST = [
    "$1,001 - $15,000",
    "$15,001 - $50,000",
    "$50,001 - $100,000",
    "$100,001 - $250,000",
    "$250,001 - $500,000",
    "$500,001 - $1,000,000",
    "$1,000,001 - $5,000,000",
    "$5,000,001 - $25,000,000",
    "$25,000,001 - $50,000,000",
]


def analyze_line(row_content: str) -> dict:
    row_content = row_content.strip()

    to_return = {"original_content": row_content}

    # Handle extra info
    if EXTRA_INFO_LINE_VAL in row_content:
        extra_info_start_idx = row_content.find(EXTRA_INFO_LINE_VAL)
        extra_info_end_idx = extra_info_start_idx + len(EXTRA_INFO_LINE_VAL)
        extra_info = row_content[extra_info_end_idx:]
        row_content = row_content[:extra_info_start_idx]
        to_return["extra_info"] = extra_info.strip()
    else:
        to_return["extra_info"] = None

    # Get owner
    owner = "SELF"
    for owner_prefix in OWNER_PREFIX_LIST:
        to_test = owner_prefix + " "
        if row_content.startswith(to_test):
            owner = owner_prefix
            row_content = row_content.removeprefix(to_test)
            break
    to_return["owner"] = owner

    # Find ticker
    ticker = re.search(r"\((.*?)\)", row_content)
    if ticker:
        ticker_val = ticker.group(1)
        to_return["ticker"] = ticker_val
        row_content = row_content.replace("(" + ticker_val + ")", " ")
    else:
        to_return["ticker"] = None

    # Special transaction type case
    transaction_type = None
    S_PARTIAL_STR = "S (PARTIAL)"
    if S_PARTIAL_STR in row_content:
        transaction_type = S_PARTIAL_STR
        row_content = row_content.replace(S_PARTIAL_STR, "")

    # Find asset type
    asset_type = re.search(r"\[(.*?)\]", row_content)
    if asset_type:
        asset_type_val = asset_type.group(1)
        to_return["asset_type"] = asset_type_val
        row_content = row_content.replace("[" + asset_type_val + "]", " ")
    else:
        to_return["asset_type"] = None

    # Find dates
    date_list = re.findall(r"\b\d{1,2}/\d{1,2}/\d{4}\b", row_content)
    if len(date_list) == 2:
        to_return["transaction_date"] = date_list[0]
        to_return["notification_date"] = date_list[1]
        for date_str in date_list:
            row_content = row_content.replace(date_str, " ")
    else:
        to_return["transaction_date"] = None
        to_return["notification_date"] = None

    # Find amount
    amount = None
    for amount_range in AMOUNT_RANGE_LIST:
        if amount_range in row_content:
            amount = amount_range
            row_content = row_content.replace(amount, " ")
            break
    to_return["amount"] = amount

    # Reformat row_content
    row_content = re.sub(" +", " ", row_content)
    row_content = row_content.strip()

    # Get transaction type
    if not transaction_type:
        transaction_type = row_content[-1:]
        row_content = row_content[:-2]
    to_return["transaction_type"] = transaction_type

    to_return["asset_name"] = row_content
    return to_return


EXTRA_INFO_LINE_VAL = "extra_info"
LINE_SPLIT_VAL = "--new_line--"


def get_content_lines(content: str) -> list[dict]:
    # Try to crop out some lines
    CROP_START_STR_LIST = [
        "GAINS > $200?",
        "GAINS > $200",
        "NOTIFICATION AMOUNT DATE",
        "NOTIFICATION DATE AMOUNT",
    ]

    start_index = 0
    for start_str in CROP_START_STR_LIST:
        tmp = content.find(start_str)
        if tmp > 0:
            start_index = tmp + len(start_str)
            break

    CROP_END_STR_LIST = [
        "* FOR THE COMPLETE LIST",
        "INITIAL PUBLIC OFFER",
        "ASSET CLASS DETA",
    ]

    end_index = len(content)
    for end_str in CROP_END_STR_LIST:
        tmp = content.find(end_str)
        if tmp > 0 and tmp < end_index:
            end_index = tmp

    content = content[start_index:end_index]

    info_list = []
    extra_info_list = []
    ENDING_LINE_LIST = ["STATUS: NEW", "SUBHOLDING OF", "DESCRIPTION: ", "COMMENT"]
    TABLE_HEADER_LIST = ["OWNER ASSET TRANSACTION", "ID OWNER ASSET TRANSACTION"]

    for line in content.splitlines():
        line = line.strip()
        if not line:
            continue

        # TODO: Opportunity here to get more data
        is_ending_line = False
        for ending_line in ENDING_LINE_LIST:
            if ending_line in line:
                is_ending_line = True
                break

        is_header_line = False
        for header_str in TABLE_HEADER_LIST:
            if header_str in line:
                is_header_line = True
                break
        if is_header_line:
            continue

        if is_ending_line:
            extra_info_list.append(line)

        else:
            if len(extra_info_list):
                to_add = [EXTRA_INFO_LINE_VAL, *extra_info_list, LINE_SPLIT_VAL]
                info_list += to_add
                extra_info_list = []

            info_list.append(line)

    # Fix line splits
    info_list = " ".join(info_list).split(LINE_SPLIT_VAL)
    info_list = [analyze_line(line) for line in info_list if line.strip()]

    return info_list


def process_extract_obj_list(extract_obj_list: tuple[str, tuple]) -> str:
    # Sort text by y
    extract_obj_list = sorted(extract_obj_list, key=lambda obj: obj[1][1])

    # Find all lines in text
    """
    line_list items are tuples.
    First value are line y ranges
    Second value is obj_list, list of extract_obj items 
    """
    line_list: list[tuple[tuple, list]] = []

    for extract_obj in extract_obj_list:
        _, coords = extract_obj
        _, img_y = coords

        should_append = True
        for line_obj in line_list:
            line_range, obj_list = line_obj
            range_start, range_end = line_range

            if img_y >= range_start and img_y <= range_end:
                obj_list.append(extract_obj)
                should_append = False
                break

        if should_append:
            RANGE_DIFF = 5
            range_start = img_y
            range_end = range_start + RANGE_DIFF

            new_line_range: tuple[int, int] = (range_start, range_end)
            new_obj_list = [extract_obj]
            new_line_obj = (new_line_range, new_obj_list)
            line_list.append(new_line_obj)

    # Sort and combine line list second item
    flattened_line_list = []
    for line_obj in line_list:
        sorted_obj_list = sorted(line_obj[1], key=lambda obj: obj[1][0])
        to_add_list = [obj[0] for obj in sorted_obj_list]
        to_add = " ".join(to_add_list)
        flattened_line_list.append(to_add)

    return "\n".join(flattened_line_list)


def ocr_img(pil_img):
    # Read image from which text needs to be extracted
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
    rect_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (18, 18))

    # Applying dilation on the threshold image
    dilation = cv2.dilate(thresh1, rect_kernel, iterations=1)

    # Finding contours
    contours, _ = cv2.findContours(dilation, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)

    # Creating a copy of image
    im2 = img.copy()

    extract_obj_list: list[tuple[str, tuple[int, int]]] = []
    failed_ocr_list: list = []
    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)

        # Drawing a rectangle on copied image
        cv2.rectangle(im2, (x, y), (x + w, y + h), (0, 255, 0), 2)

        # Cropping the text block for giving input to OCR
        cropped = im2[y : y + h, x : x + w]

        # Apply OCR on the cropped image
        text: str = pytesseract.image_to_string(cropped, lang="eng")

        # Redo OCR with stricter psm
        is_small = cropped.shape[0] < 50 and cropped.shape[1] < 50
        if not text and is_small:
            text: str = pytesseract.image_to_string(
                cropped, lang="eng", config="--psm 10"
            )
            text = remove_non_alphanumeric(text)
            if len(text) > 2:
                text = ""

            if not text:
                failed_ocr_list.append((cropped, text, (x, y)))

        # Convert text to uppercase
        text = text.upper()
        text = text.replace("\n", " ")
        text = re.sub(" +", " ", text).strip()

        # Common errors to fix
        COMMON_ERROR_DICT = {"SS": "S"}

        COMMON_ERROR_SUBSTRING_DICT = {
            "CIASS": "CLASS",
            "SUUBHOLDING": "SUBHOLDING",
            "PUBLIICC": "PUBLIC",
            "PUBLIICC": "PUBLIC",
            "FITINC": "FILING",
            "FIIINC": "FILING",
            "FIUINC": "FILING",
            "FILINC": "FILING",
            "ST|": "ST]",
        }

        for item in COMMON_ERROR_DICT.items():
            if text == item[0]:
                text = item[1]

        for item in COMMON_ERROR_SUBSTRING_DICT.items():
            if item[0] in text:
                text = text.replace(item[0], item[1])

        if text:
            extract_obj_list.append((text, (x, y)))

    return im2, extract_obj_list, failed_ocr_list


def should_analyze_content(content: str) -> str:
    content_lines = content.splitlines()
    if "FILING ID" in content_lines[0] and "PERIODIC TRANS" in content_lines[1]:
        return True
    return False


def analyze_pdf(pdf_file_path):
    image_list = convert_from_path(pdf_file_path)

    master_failed_ocr_list = []
    processed_image_list = []
    master_content_list = []

    is_dont_analyze = False
    for i, img_obj in enumerate(image_list):
        img, extract_obj_list, failed_ocr_list = ocr_img(img_obj)
        raw_content = process_extract_obj_list(extract_obj_list)

        if i == 0 and not should_analyze_content(raw_content):
            is_dont_analyze = True
            break

        processed_image_list.append(img)
        master_failed_ocr_list += failed_ocr_list
        master_content_list.append(raw_content)

    master_content = "\n".join(master_content_list)

    if is_dont_analyze:
        content_lines = [{"failed": True, "reason": "Not formatted"}]
    else:
        content_lines = get_content_lines(master_content)

    return (content_lines, master_content, processed_image_list, master_failed_ocr_list)


def main():
    # Get arguments
    parser = argparse.ArgumentParser()

    parser.add_argument("-s", "--start-index", type=int)
    parser.add_argument("-e", "--end-index", type=int)
    parser.add_argument("--start-year", type=int)
    args, _ = parser.parse_known_args()

    start_index = args.start_index or 0
    end_index = args.end_index or -1
    start_year = args.start_year or 0

    IN_FOLDER_PATH = join(get_out_folder_house(), "documents")
    file_names = listdir(IN_FOLDER_PATH)
    if end_index == -1:
        end_index = len(file_names)

    OUT_FOLDER_PATH = get_out_folder_house()
    RAW_CONTENT_FOLDER_PATH = join(OUT_FOLDER_PATH, "raw_content")
    INFO_EXTRACT_FOLDER_PATH = join(OUT_FOLDER_PATH, "info_extract")

    file_names.sort()
    for i, file_name in enumerate(file_names):
        if i < start_index or i >= end_index:
            continue

        if start_year:
            file_year = int(file_name[0:4])
            if file_year < start_year:
                continue

        print("Processing", i, file_name)
        file_path = join(IN_FOLDER_PATH, file_name)

        content_lines, raw_content, processed_image_list, failed_ocr_list = analyze_pdf(
            file_path
        )

        # Save extract
        info_extract_file_path = join(
            INFO_EXTRACT_FOLDER_PATH, file_name.replace("pdf", "json")
        )
        with open(info_extract_file_path, "w", encoding="utf-8") as outfile:
            outfile.write(json.dumps(content_lines, indent=4))

        # Save raw content
        raw_content_file_path = join(
            RAW_CONTENT_FOLDER_PATH, file_name.replace("pdf", "txt")
        )
        with open(raw_content_file_path, "w", encoding="utf-8") as outfile:
            outfile.write(raw_content)

        print("Done", i, file_name)

        pct = get_percentage_string(i + 1, start_index, end_index)
        print(pct)


if __name__ == "__main__":
    main()
