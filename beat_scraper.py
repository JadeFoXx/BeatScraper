import io
import os
import requests
import zipfile
import re
import json

with open("config.json") as f:
    config = json.load(f)

directory = config['beatsaber_custom_levels_directory']
api = config['beatsaver_url']
count = config['download_count']
next_page = ""

installed = [f.name for f in os.scandir(directory) if f.is_dir()]


def sanitize(s):
    s = re.sub(r'[:*<>/\\|?"]', '', s)
    return s


def get_latest():
    r = requests.get(api + next_page)
    r = r.json()['docs']
    d = r[-1]['uploaded']
    r = [x for x in r if x['uploader']['curator']]
    return r, d


def download_and_extract(level):
    id = str(level['id'])
    name = sanitize(str(level['name']))
    print(f"downloading {name}")
    download = requests.get(level['versions'][0]['downloadURL'])
    zip = zipfile.ZipFile(io.BytesIO(download.content))
    print(f"extracting {name}")
    zip.extractall(directory + '\\' + f"{id} ({name})")


def is_duplicate(level):
    id = level['id']
    return any(id in i_level for i_level in installed)


while count > 0:
    latest_curated, last_date = get_latest()
    for level in latest_curated:
        if not is_duplicate(level):
            download_and_extract(level)
            count = count - 1
            if count <= 0:
                break
            print(f"{count} songs remaining")
    next_page = f"&before={last_date}"
