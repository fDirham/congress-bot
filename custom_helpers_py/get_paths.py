from dotenv import load_dotenv
from os.path import join
from os import environ

load_dotenv(override=True)


def get_out_folder() -> str:
    return environ.get("OUT_FOLDER")


def get_out_folder_house() -> str:
    return join(get_out_folder(), "house")


def get_out_folder_senate() -> str:
    return join(get_out_folder(), "senate")


def get_out_folder_analysis() -> str:
    return join(get_out_folder(), "analysis")
