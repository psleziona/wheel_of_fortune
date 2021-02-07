import requests
from bs4 import BeautifulSoup
import time

url = 'https://pl.wikiquote.org/wiki/Przysłowia_polskie'

res = requests.get(url)

soup = BeautifulSoup(res.text, 'html.parser')


sentences = soup.find_all(lambda tag:tag.parent.name == 'ul' and  not tag.has_attr('id') and not tag.has_attr('class'))
with open('game_passwords.txt', 'w') as file:
    for sentence in sentences:
        sen = sentence.contents[0]
        if sen.startswith('Źródło') or sen.startswith('Zobacz też'):
            continue
        file.write(sen + '\n')
