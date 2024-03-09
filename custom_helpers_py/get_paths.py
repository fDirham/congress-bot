from dotenv import load_dotenv
from os import environ

load_dotenv(override=True)


def get_out_folder_house() -> str:
    return environ.get("OUT_FOLDER_HOUSE")


def get_out_folder_senate() -> str:
    return environ.get("OUT_FOLDER_SENATE")
