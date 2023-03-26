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

directory = config['beatsaber_custom_levels_directory']
api = config['beatsaver_url']
curated_endpoint = config['curated_endpoint']
map_id_endpoint = config['id_endpoint']
map_hash_endpoint = config['hash_endpoint']


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
    for f in os.scandir(directory):
        if f.is_dir():
            map_name = f.name
            map_id = map_name.split(' ')[0]
            map_hash = ""
            map_date = datetime.datetime.min
            if os.path.exists(f.path + '\\' "version.json"):
                with open(f.path + '\\' "version.json", 'r') as v:
                    version = json.load(v)
                    map_id = version['id']
                    map_hash = version['hash']
                    map_date = to_date(version['date'])
            installed[map_id] = dict({"name": map_name, "hash": map_hash, "date": map_date})
    return installed


def get_latest_curated_maps(next_page):
    r = requests.get(api + curated_endpoint + next_page)
    r = r.json()['docs']
    d = r[-1]['uploaded']
    r = [x for x in r if "curator" in x]
    return r, d


def is_skippable(map_id, map_date, installed):
    if map_id in installed:
        return installed[map_id]['date'] >= map_date
    return False


def get_map_data(map):
    map_id = str(map['id'])
    map_name = sanitize(str(map['name']))
    map_hash = ""
    map_date = datetime.datetime.min
    download_url = ""
    for version in map['versions']:
        current_date = to_date(version['createdAt'])
        if current_date > map_date:
            map_date = current_date
            map_hash = str(version['hash'])
            download_url = version['downloadURL']
    return map_id, map_name, map_hash, map_date, download_url, len(map['versions'])


def download_and_extract(map_id, map_name, map_hash, map_date, download_url):
    try:
        download = requests.get(download_url)
        zip = zipfile.ZipFile(io.BytesIO(download.content))
        path = directory + '\\' + f"{map_id} ({map_name})"
        zip.extractall(path)
        with open(path + '\\' + 'version.json', 'w') as j:
            json.dump({"id": map_id, "hash": map_hash, "date": str(map_date)}, j)
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
            map_id, map_name, map_hash, map_date, download_url, version_count = get_map_data(map)
            if not is_skippable(map_id, map_date, installed):
                pbar.set_postfix(map=f"{map_name}({version_count})")
                download_and_extract(map_id, map_name, map_hash, map_date, download_url)
                i -= 1
                pbar.update(1)
        next_page = f"&before={last_date}"


run()
