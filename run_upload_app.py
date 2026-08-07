#!/usr/bin/env python

from uploader import UploaderApp, UploadConfig
import os
import logging
import json 
import argparse
from pathlib import Path
parser = argparse.ArgumentParser()
parser.add_argument("-c", "--config", type=str, dest = "CONFIG", required=True,
                    help="path to the JSON configuration file")
args = parser.parse_args()

config_path = args.CONFIG
if config_path is None or not os.path.isfile(config_path):
    raise ValueError(f"Invalid configuration file path: {config_path}")

uploader_json_dict = json.load(open(config_path, "r"))
uploader_config = UploadConfig(source_dir=Path(uploader_json_dict["source_dir"]),
                               trash_dir=Path(uploader_json_dict["trash_dir"]),
                               destination_url=uploader_json_dict["destination_url"],
                               semaphore_ext=uploader_json_dict.get("semaphore_ext", None))

print(f"Uploader configuration: {uploader_config}")
__user = uploader_json_dict.get("username", None)
__password = uploader_json_dict.get("password", None)
if __user is None or __password is None:
    raise ValueError("Username and password must be provided in the configuration file.")

uploader = UploaderApp(config=uploader_config, 
                        user=__user, 
                        password=__password,
                        logfile = "uploader.log",
                        printlevel=logging.INFO,
                        loglevel=logging.INFO)