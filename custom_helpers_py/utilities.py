from os import listdir, remove
from os.path import join, isfile
import re


def get_percentage_string(curr_idx, start_idx, last_idx):
    normalized_idx = curr_idx - start_idx
    normalized_last_idx = last_idx - start_idx
    done_fraction = normalized_idx / normalized_last_idx
    done_pct: float = done_fraction * 100
    done_pct_string = "{:10.2f}%".format(done_pct)
    return done_pct_string


def delete_folder_contents(folder_path):
    file_list = listdir(folder_path)
    for file in file_list:
        file_path = join(folder_path, file)
        if isfile(file_path):
            remove(file_path)


def remove_non_alphanumeric(in_str: str, replace_with: str = None) -> str:
    replace_with = replace_with or ""
    return re.sub("[^0-9a-zA-Z]+", replace_with, in_str)
