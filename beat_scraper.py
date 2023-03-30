import datetime
import io
import os
import requests
import zipfile
import re
import json
from datetime import datetime as dt
from tqdm import tqdm

with open("config.json") as c:
    config = json.load(c)

BEATSABER_CUSTOM_LEVELS_DIRECTORY = config['beatsaber_custom_levels_directory']
BEATSAVER_API = config['beatsaver_api']


def to_date(string):
    string = string[:-1] if string[-1] == "Z" else string
    try:
        return dt.strptime(string, "%Y-%m-%dT%H:%M:%S.%f")
    except ValueError:
        pass
    try:
        return dt.strptime(string, "%Y-%m-%dT%H:%M:%S")
    except ValueError:
        pass
    return datetime.datetime.min


def sanitize(s):
    s = re.sub(r'[:*<>/\\|?"\t]', '', s)
    return s


def get_installed():
    installed = {}
    for f in os.scandir(BEATSABER_CUSTOM_LEVELS_DIRECTORY):
        if f.is_dir():
            level_name = f.name
            level_id = level_name.split(' ')[0]
            level_date = datetime.datetime.min
            if os.path.exists(f.path + '\\' "version.json"):
                with open(f.path + '\\' "version.json", 'r') as v:
                    version = json.load(v)
                    level_date = to_date(version['date'])
            installed[level_id] = dict({"id": level_id, "name": level_name, "date": level_date})
    return installed


def get_latest_curated_maps(next_page):
    r = requests.get(BEATSAVER_API + next_page)
    r = r.json()['docs']
    d = r[-1]['uploaded']
    r = [x for x in r if "curator" in x]
    return r, d


def is_skippable(map_id, map_date, installed):
    if map_id in installed:
        return installed[map_id]['date'] >= map_date
    return False


def get_map_data(level):
    level_id = str(level['id'])
    level_name = sanitize(str(level['name']))
    level_date = datetime.datetime.min
    download_url = ""
    for version in level['versions']:
        current_date = to_date(version['createdAt'])
        if current_date > level_date:
            level_date = current_date
            download_url = version['downloadURL']
    return level_id, level_name, level_date, download_url, len(level['versions'])


def download_and_extract(level_id, level_name, level_date, download_url):
    try:
        download = requests.get(download_url)
        level_zip = zipfile.ZipFile(io.BytesIO(download.content))
        path = BEATSABER_CUSTOM_LEVELS_DIRECTORY + '\\' + f"{level_id} ({level_name})"
        level_zip.extractall(path)
        with open(path + '\\' + 'version.json', 'w') as j:
            json.dump({"id": level_id, "name": level_name, "date": str(level_date)}, j)
        return True
    except zipfile.BadZipfile:
        return False


def run():
    next_page = ""
    installed = get_installed()
    count = config['download_count']
    pbar = tqdm(total=count, desc="downloading", postfix={"map": ""})
    i = count
    while i > 0:
        latest_curated, last_date = get_latest_curated_maps(next_page)
        for map in latest_curated:
            map_id, map_name, map_date, download_url, version_count = get_map_data(map)
            if not is_skippable(map_id, map_date, installed):
                pbar.set_postfix(map=f"{map_name}({version_count})")
                download_and_extract(map_id, map_name, map_date, download_url)
                i -= 1
                pbar.update(1)
        next_page = f"&before={last_date}"


run()
