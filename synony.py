import lyricsgenius as genius
import threading
import queue
import requests
import random
import bs4
import sys
import os

URL_DEFINITION = "https://www.linternaute.fr/dictionnaire/fr/definition/{0}/"
URL_SYNONYM = "http://www.synonymo.fr/synonyme/{0}"
HEADERS = {
    "user-agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:61.0) "\
                  + "Gecko/20100101 Firefox/61.0"
}

STOPWORDS = "un une le la les de des je tu il nous vous ils elle elles on"

PROBABILITY_FETCH = 1

def get_definition(word):
    r = requests.get(URL_DEFINITION.format(word), headers=HEADERS)
    if r.status_code != 200:
        print("Error with the request: status code {0}".format(r.status_code))
        return
    soup = bs4.BeautifulSoup(r.text, "lxml")
    divs = soup.select(".dico_definition")[0].findChildren(recursive=False)
    for i in range(0, len(divs), 2):
        if "nom" in divs[i].select("em")[0].contents[0][3:]:
            for div in divs[i + 1].select(".grid_line.gutter"):
                children = div.findChildren(recursive=False)
                if len(children) >= 2:
                    left, right = children[:2]
                    if "sens" in left.contents[0].lower():
                        string = ""
                        for content in right.contents:
                            if type(content) == type(""):
                                string += content
                            elif content.name != "div":
                                string += content.string
                        tmp = string.replace("\n", "").replace(".", "")
                        index = len(tmp) - 1
                        while ord(tmp[index]) == 32:
                            index -= 1
                        return tmp[0].lower() + tmp[1:index + 1]

def get_synonym(word):
    try:
        r = requests.get(URL_SYNONYM.format(word), headers=HEADERS)
    except requests.exceptions.ConnectionError:
        # print("Connection error")
        return
    if r.status_code != 200:
        # print("Error with the request: status code {0}".format(r.status_code))
        return
    soup = bs4.BeautifulSoup(r.text.encode(r.encoding), "lxml")
    words = soup.select("#main-container .word")
    if len(words) > 0:
        return random.choice(words).string

def charging_bar(pos, max, end):
    size = 78
    string = ""
    index = int(float(size) * float(pos) / float(max))
    for i in range(index):
        string += "="
    if index < size:
        string += ">"
    while len(string) < size:
        string += " "
    print("\r[" + string + "]", end=end)
    sys.stdout.flush()

def remove_brackets_lines(text):
    new_text = ""
    for line in text.split("\n"):
        if "[" not in line:
            new_text += line + "\n"
    return new_text[:-1]

def split(string):
    arr, sep = [""], []
    for c in string:
        if c in ",;:.?! ":
            sep.append(c)
            arr.append("")
        else:
            arr[-1] += c
    return arr, sep

def join(arr, sep):
    string = ""
    for i in range(len(arr)):
        string += arr[i]
        if i < len(sep):
            string += sep[i]
    return string

def transform(text):
    out = ""
    arr, sep = split(remove_brackets_lines(text))
    n_threads = 100

    print("Processing lyrics...")

    q_in = queue.Queue()
    q_out = queue.Queue()
    q_progress = queue.Queue()
    threads = []

    def worker(arr, q_in, q_out, q_progress):
        while True:
            index = q_in.get()
            if index is None:
                break
            word = get_synonym(arr[index].lower())
            q_out.put({index: word})
            q_progress.put(True)
            q_in.task_done()

    def progress(length, q):
        index = 0
        while True:
            foo = q.get()
            if foo is None:
                break
            index += 1
            charging_bar(index, length, "")

    for i in range(n_threads):
        thread = threading.Thread(target=worker,
            args=(arr, q_in, q_out, q_progress))
        thread.start()
        threads.append(thread)

    progress_thread = threading.Thread(target=progress,
        args=(len(arr), q_progress))
    progress_thread.start()

    for i in range(len(arr)):
        if len(arr[i]) > 0 and random.random() < PROBABILITY_FETCH\
            and arr[i].lower() not in STOPWORDS:
            q_in.put(i)

    q_in.join()

    for i in range(n_threads):
        q_in.put(None)
    q_progress.put(None)
    for tread in threads:
        thread.join()

    while not q_out.empty():
        index, response = list(q_out.get().items())[0]
        if response is not None:
            arr[index] = response

    os.system("clear")
    return join(arr, sep)


def retrieve_lyrics(query):
    api = genius.Genius(open("genius.token", "r").readline().replace("\n", ""))
    song = api.search_song(query, verbose=False)
    if song is not None:
        return song.lyrics, song.title, song.artist


def main():
    song_results = retrieve_lyrics(input("Song title> "))
    if song_results is not None:
        lyrics, title, artist = song_results
        print("Found {0} by {1}.".format(title, artist))
        print(transform(lyrics))
    else:
        print("Song not found.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
