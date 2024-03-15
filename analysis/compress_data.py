import pandas as pd
from os import listdir
from os.path import join
from custom_helpers_py.get_paths import get_out_folder_house, get_out_folder_senate
from custom_helpers_py.utilities import get_percentage_string
from typing import Any
import argparse


def compress_house():
    house_folder_path = join(get_out_folder_house(), "info_extract")
    house_df_list: list[pd.DataFrame] = []
    house_file_name_list = listdir(house_folder_path)
    last_idx = len(house_file_name_list)

    for i, house_file_name in enumerate(house_file_name_list):
        file_path = join(house_folder_path, house_file_name)
        df = pd.read_json(file_path)
        if "Skipped" in df.columns or "failed" in df.columns:
            continue

        file_name_list = house_file_name.removesuffix(".json").split("_")
        year, district, politician_last_name, politician_first_name, doc_id = (
            file_name_list
        )

        df["politician_first_name"] = politician_first_name
        df["politician_last_name"] = politician_last_name
        df["district"] = district
        df["year"] = year
        df["office"] = "H"
        df["doc_id"] = doc_id

        house_df_list.append(df)
        print(get_percentage_string(i + 1, 0, last_idx))

    master_house_df = pd.concat(house_df_list)
    master_house_df = master_house_df.rename(
        columns={
            "extra_info": "comments",
        }
    )

    # Get action
    def get_action_type(row) -> str:
        action_type = row["action_type"]
        if isinstance(action_type, str) and len(action_type) >= 1:
            return action_type[0]
        return None

    def get_action_type_extra(row) -> str:
        action_type = row["action_type"]
        if isinstance(action_type, str) and len(action_type) > 1:
            return action_type[1:].strip()
        return None

    master_house_df["action_type_extra"] = master_house_df.apply(
        get_action_type_extra, axis=1
    )
    master_house_df["action_type"] = master_house_df.apply(get_action_type, axis=1)

    master_house_df = master_house_df.drop(
        columns=[
            "original_content",
        ]
    )

    # Get final columns
    master_house_df = master_house_df[
        [
            "transaction_date",
            "politician_first_name",
            "politician_last_name",
            "office",
            "district",
            "asset_name",
            "asset_type",
            "ticker",
            "owner",
            "action_type",
            "action_type_extra",
            "amount",
            "comments",
            "doc_id",
        ]
    ]

    # Get malformed df
    ACCEPTABLE_TYPE = ["P", "S", "E"]

    def is_malformed_house_df(row) -> bool:
        if (
            not row["action_type"]
            or row["action_type"] not in ACCEPTABLE_TYPE
            or not row["amount"]
        ):
            return True
        return False

    is_malformed = master_house_df.apply(is_malformed_house_df, axis=1)
    malformed_house_df = master_house_df[is_malformed]
    master_house_df = master_house_df[~is_malformed]

    # Save
    OUT_FOLDER = join(get_out_folder_house(), "compressed")
    MALFORMED_FILE_PATH = join(OUT_FOLDER, "malformed_house.csv")
    MASTER_HOUSE_FILE_PATH = join(OUT_FOLDER, "master_house.csv")
    malformed_house_df.to_csv(
        MALFORMED_FILE_PATH, encoding="utf-8", index=False, header=True
    )
    master_house_df.to_csv(
        MASTER_HOUSE_FILE_PATH, encoding="utf-8", index=False, header=True
    )


def compress_senate():
    senate_folder_path = join(get_out_folder_senate(), "documents")
    senate_df_list: list[pd.DataFrame] = []
    senate_file_name_list = listdir(senate_folder_path)
    last_idx = len(senate_file_name_list)

    for i, senate_file_name in enumerate(senate_file_name_list):
        if not senate_file_name.endswith(".json") or "image-list" in senate_file_name:
            continue

        file_path = join(senate_folder_path, senate_file_name)
        df = pd.read_json(file_path)
        if "Skipped" in df.columns or "failed" in df.columns:
            continue

        file_name_list = senate_file_name.removesuffix(".json").split("_")
        year, politician_last_name, politician_first_name, doc_id = file_name_list

        df["politician_first_name"] = politician_first_name
        df["politician_last_name"] = politician_last_name
        df["district"] = ""
        df["office"] = "S"
        df["year"] = year
        df["doc_id"] = doc_id

        senate_df_list.append(df)
        print(get_percentage_string(i + 1, 0, last_idx))

    master_senate_df = pd.concat(senate_df_list)
    master_senate_df = master_senate_df.rename(
        columns={
            "transactionDate": "transaction_date",
            "assetName": "asset_name",
            "assetType": "asset_type",
            "actionType": "action_type",
            "comment": "comments",
        }
    )

    # Get action type extra
    def get_action_type_extra(row) -> str:
        action_type = row["action_type"]
        at_wc = len(action_type.split(" "))
        if isinstance(action_type, str) and at_wc > 1:
            extra_info = " ".join(action_type.split(" ")[1:])
            extra_info = extra_info.strip().upper()
            if "FULL" in extra_info:
                return None

            return extra_info
        return None

    master_senate_df["action_type_extra"] = master_senate_df.apply(
        get_action_type_extra, axis=1
    )

    # Standardize action type
    def get_action_type(row) -> str:
        action_type = row["action_type"]
        if isinstance(action_type, str) and len(action_type) >= 1:
            return action_type[0]
        return None

    master_senate_df["action_type"] = master_senate_df.apply(get_action_type, axis=1)

    # Standardize owner
    def get_owner(in_owner: str) -> str:
        if in_owner == "Self":
            return "SELF"
        if in_owner == "Spouse":
            return "SP"
        if in_owner == "Joint":
            return "JT"
        if in_owner == "Child":
            return "DC"
        return None

    master_senate_df["owner"] = master_senate_df["owner"].apply(get_owner)

    # Standardize asset type
    def get_asset_type(in_asset_type: str) -> str:
        if in_asset_type == "--":
            return None
        if in_asset_type == "Corporate Bond":
            return "CS"
        if in_asset_type == "Stock":
            return "ST"
        return in_asset_type

    master_senate_df["asset_type"] = master_senate_df["asset_type"].apply(
        get_asset_type
    )

    # Get final columns
    master_senate_df = master_senate_df[
        [
            "transaction_date",
            "politician_first_name",
            "politician_last_name",
            "office",
            "district",
            "asset_name",
            "asset_type",
            "ticker",
            "owner",
            "action_type",
            "action_type_extra",
            "amount",
            "comments",
            "doc_id",
        ]
    ]

    # Save
    OUT_FOLDER = join(get_out_folder_senate(), "compressed")
    MASTER_SENATE_FILE_PATH = join(OUT_FOLDER, "master_senate.csv")
    master_senate_df.to_csv(
        MASTER_SENATE_FILE_PATH, encoding="utf-8", index=False, header=True
    )


def main():
    # Get arguments
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "-b", "--both", type=bool, action=argparse.BooleanOptionalAction, default=False
    )
    parser.add_argument(
        "--house", type=bool, action=argparse.BooleanOptionalAction, default=False
    )
    parser.add_argument(
        "--senate",
        type=bool,
        action=argparse.BooleanOptionalAction,
        default=False,
    )
    args, _ = parser.parse_known_args()

    is_both = args.both
    is_house = args.house
    is_senate = args.senate

    if not is_senate and not is_house:
        is_both = True

    if is_both or is_house:
        compress_house()
    if is_both or is_senate:
        compress_senate()


if __name__ == "__main__":
    main()
