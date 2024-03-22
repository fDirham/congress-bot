from os.path import join
import pandas as pd
from custom_helpers_py.get_paths import get_out_folder_analysis
import argparse


def main():
    # Get arguments
    parser = argparse.ArgumentParser()

    parser.add_argument("-i", "--in-substring", type=str, required=True)
    parser.add_argument("-o", "--out-file-path", type=str, required=False)
    args, _ = parser.parse_known_args()

    in_substring: str = args.in_substring
    out_file_path: str = args.out_file_path

    TRANSACTIONS_MASTER_DF_FILE_PATH = join(get_out_folder_analysis(), "master_df.csv")

    master_df = pd.read_csv(TRANSACTIONS_MASTER_DF_FILE_PATH)

    mask = master_df["politician_name"].str.contains(in_substring.upper())
    master_df = master_df[mask]

    if out_file_path:
        master_df.to_csv(out_file_path, encoding="utf-8", index=False)

    print(master_df.head())


if __name__ == "__main__":
    main()
