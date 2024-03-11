from pypdf import PdfReader
import json
import re
from os import listdir
from os.path import join
from pdfminer.high_level import extract_text


OWNER_PREFIX_LIST = ["JT", "DC", "SP"]
HEADER_STR = (
    "ID OwnerAsset Transaction TypeDate Notification DateAmount Cap . Gains > $200?"
)
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

NULL_VAL = None


def analyze_row(row_content: str) -> dict:
    is_malformed = HEADER_STR in row_content

    row_content = row_content.replace(HEADER_STR, " ")
    row_content = re.sub(" +", " ", row_content)
    row_content = row_content.strip()

    to_return = {"original_content": row_content, "is_malformed": is_malformed}

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
        to_return["ticker"] = NULL_VAL

    # Find asset type
    asset_type = re.search(r"\[(.*?)\]", row_content)
    if asset_type:
        asset_type_val = asset_type.group(1)
        to_return["asset_type"] = asset_type_val
        row_content = row_content.replace("[" + asset_type_val + "]", " ")
    else:
        to_return["asset_type"] = NULL_VAL

    # Find dates
    date_list = re.findall(r"\b\d{1,2}/\d{1,2}/\d{4}\b", row_content)
    if len(date_list) == 2:
        to_return["transaction_date"] = date_list[0]
        to_return["notification_date"] = date_list[1]
        for date_str in date_list:
            row_content = row_content.replace(date_str, " ")
    else:
        to_return["transaction_date"] = NULL_VAL
        to_return["notification_date"] = NULL_VAL

    # Find amount
    amount = NULL_VAL
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
    to_return["transaction_type"] = row_content[-1:]
    row_content = row_content[:-2]

    to_return["asset_name"] = row_content
    return to_return


def analyze_pdf(pdf_file_path) -> tuple[list[dict], str]:
    reader = PdfReader(pdf_file_path, strict=True)
    content_list = []
    for page in reader.pages:
        page_text = page.extract_text()
        content_list.append(page_text)

    content = "\n".join(content_list)
    raw_content = content

    pdf_miner_content = extract_text(pdf_file_path)
    raw_content += "\n MINER \n" + pdf_miner_content
    raw_content = raw_content.replace("\0", "_")

    analyzed_data = []
    try:
        # Strip useless content
        START_SUBSTRING = "$200?"
        start_idx = content.find(START_SUBSTRING) + len(START_SUBSTRING)
        if start_idx < 0:
            raise Exception("Can't find start")

        END_SUBSTRING = "* For the complete"
        end_idx = content.find(END_SUBSTRING)
        if end_idx < 0:
            raise Exception("Can't find end")

        content = content[start_idx:end_idx].strip()

        # Replace null values with special value
        NUL_VAL = "[NUL]"
        content = content.replace("\0", NUL_VAL)

        # Split per row
        LINE_SPLIT_VAL = "[LINE_SPLIT]"
        lines = []
        for line in content.splitlines():
            if NUL_VAL in line:
                # TODO: Opportunity here
                if lines[-1] != LINE_SPLIT_VAL:
                    lines.append(LINE_SPLIT_VAL)
            else:
                lines.append(line)
        content = " ".join(lines)

        content = content.split(LINE_SPLIT_VAL)

        analyzed_data = [analyze_row(row) for row in content if row]
    except Exception as error:
        analyzed_data = [{"error": str(error)}]

    return (analyzed_data, raw_content)


def main():
    BASE_FOLDER_PATH = "./tmp/test_pdf/"
    file_names = listdir(BASE_FOLDER_PATH)

    RES_FOLDER_PATH = "./tmp/extract_out/"
    RAW_FOLDER_PATH = join(RES_FOLDER_PATH, "raw_content")
    for file_name in file_names:
        file_path = join(BASE_FOLDER_PATH, file_name)

        analyzed_data, raw_content = analyze_pdf(file_path)
        to_write = json.dumps(analyzed_data, indent=4)

        out_file_path = join(RES_FOLDER_PATH, file_name.replace("pdf", "json"))
        raw_file_path = join(RAW_FOLDER_PATH, file_name.replace("pdf", "txt"))

        with open(out_file_path, "w", encoding="utf-8") as outfile:
            outfile.write(to_write)

        with open(raw_file_path, "w", encoding="utf-8") as outfile:
            outfile.write(raw_content)


if __name__ == "__main__":
    main()
