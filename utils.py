"""
MIT License

Copyright (c) 2022 Omkaar

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
from datetime import datetime, timedelta
import aiohttp
import re
import time
import json

proxy = 'http://127.0.0.1:10809' #此处填写代理地址

NEW_SESSION_URL = "https://{}/new_session?callback=jQuery331023608747682107778_{}&urlApiWs={}&partner=1&childMod={}&player=website-desktop&uid_ext_session={}&frontaddr={}&constraint=ETAT<>'AV'&soft_constraint={}&question_filter={}"
ANSWER_URL = "https://{}/answer_api?callback=jQuery331023608747682107778_{}&urlApiWs={}&childMod={}&session={}&signature={}&step={}&answer={}&frontaddr={}&question_filter={}"
BACK_URL = "{}/cancel_answer?callback=jQuery331023608747682107778_{}&childMod={}&session={}&signature={}&step={}&answer=-1&question_filter={}"
WIN_URL = "{}/list?callback=jQuery331023608747682107778_{}&childMod={}&session={}&signature={}&step={}"


HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
    "Accept-Encoding": "gzip, deflate",
    "Accept-Language": "en-US,en;q=0.9",
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) snap Chromium/81.0.4044.92 Chrome/81.0.4044.92 Safari/537.36",
    "x-requested-with": "XMLHttpRequest",
}

def ans_to_id(ans):
    """Convert an input answer string into an Answer ID for Akinator"""

    ans = str(ans).lower()
    if ans == "yes" or ans == "y" or ans == "0":
        return "0"
    elif ans == "no" or ans == "n" or ans == "1":
        return "1"
    elif ans == "i" or ans == "idk" or ans == "i dont know" or ans == "i don't know" or ans == "2":
        return "2"
    elif ans == "probably" or ans == "p" or ans == "3":
        return "3"
    elif ans == "probably not" or ans == "pn" or ans == "4":
        return "4"
    else:
        raise Exception("""
        You put "{}", which is an invalid answer.
        The answer must be one of these:
            - "yes" OR "y" OR "0" for YES
            - "no" OR "n" OR "1" for NO
            - "i" OR "idk" OR "i dont know" OR "i don't know" OR "2" for I DON'T KNOW
            - "probably" OR "p" OR "3" for PROBABLY
            - "probably not" OR "pn" OR "4" for PROBABLY NOT
        """.format(ans))


def get_lang_and_theme(lang=None):
    """Returns the language code and theme based on what is input"""

    if lang is None:
        return {"lang": "en", "theme": "c"}

    lang = str(lang).lower()
    if lang == "en" or lang == "english":
        return {"lang": "en", "theme": "c"}
    elif lang == "en_animals" or lang == "english_animals":
        return {"lang": "en", "theme": "a"}
    elif lang == "en_objects" or lang == "english_objects":
        return {"lang": "en", "theme": "o"}
    elif lang == "ar" or lang == "arabic":
        return {"lang": "ar", "theme": "c"}
    elif lang == "cn" or lang == "chinese":
        return {"lang": "cn", "theme": "c"}
    elif lang == "de" or lang == "german":
        return {"lang": "de", "theme": "c"}
    elif lang == "de_animals" or lang == "german_animals":
        return {"lang": "de", "theme": "a"}
    elif lang == "es" or lang == "spanish":
        return {"lang": "es", "theme": "c"}
    elif lang == "es_animals" or lang == "spanish_animals":
        return {"lang": "es", "theme": "a"}
    elif lang == "fr" or lang == "french":
        return {"lang": "fr", "theme": "c"}
    elif lang == "fr_animals" or lang == "french_animals":
        return {"lang": "fr", "theme": "a"}
    elif lang == "fr_objects" or lang == "french_objects":
        return {"lang": "fr", "theme": "o"}
    elif lang == "il" or lang == "hebrew":
        return {"lang": "il", "theme": "c"}
    elif lang == "it" or lang == "italian":
        return {"lang": "it", "theme": "c"}
    elif lang == "it_animals" or lang == "italian_animals":
        return {"lang": "it", "theme": "a"}
    elif lang == "jp" or lang == "japanese":
        return {"lang": "jp", "theme": "c"}
    elif lang == "jp_animals" or lang == "japanese_animals":
        return {"lang": "jp", "theme": "a"}
    elif lang == "kr" or lang == "korean":
        return {"lang": "kr", "theme": "c"}
    elif lang == "nl" or lang == "dutch":
        return {"lang": "nl", "theme": "c"}
    elif lang == "pl" or lang == "polish":
        return {"lang": "pl", "theme": "c"}
    elif lang == "pt" or lang == "portuguese":
        return {"lang": "pt", "theme": "c"}
    elif lang == "ru" or lang == "russian":
        return {"lang": "ru", "theme": "c"}
    elif lang == "tr" or lang == "turkish":
        return {"lang": "tr", "theme": "c"}
    elif lang == "id" or lang == "indonesian":
        return {"lang": "id", "theme": "c"}
    else:
        raise Exception("You put \"{}\", which is an invalid language.".format(lang))


def raise_connection_error(response):
    """Raise the proper error if the API failed to connect"""

    if response == "KO - SERVER DOWN":
        raise Exception("Akinator's servers are down in this region. Try again later or use a different language")
    elif response == "KO - TECHNICAL ERROR":
        raise Exception("Akinator's servers have had a technical error. Try again later or use a different language")
    elif response == "KO - TIMEOUT":
        raise Exception("Your Akinator session has timed out")
    elif response == "KO - ELEM LIST IS EMPTY" or response == "WARN - NO QUESTION":
        raise Exception("\"Akinator.step\" reached 79. No more questions")
    else:
        raise Exception("An unknown error has occured. Server response: {}".format(response))

class Akinator():
    """
    A class that represents an Akinator game [ASYNC VERSION].
    The first thing you want to do after calling an instance of this class is to call "start_game()".
    """
    def __init__(self):
        self.uri = None
        self.server = None
        self.session = None
        self.signature = None
        self.uid = None
        self.frontaddr = None
        self.child_mode = None
        self.question_filter = None
        self.timestamp = None

        self.question = None
        self.progression = None
        self.step = None

        self.first_guess = None
        self.guesses = None

        self.client_session = None

    def _update(self, resp, start=False):
        """Update class variables"""

        if start is True:
            self.session = int(resp["parameters"]["identification"]["session"])
            self.signature = int(resp["parameters"]["identification"]["signature"])
            self.question = str(resp["parameters"]["step_information"]["question"])
            self.progression = float(resp["parameters"]["step_information"]["progression"])
            self.step = int(resp["parameters"]["step_information"]["step"])
            data = {
                'session':self.session,
                'cilent_session':self.client_session,
                'signature':self.signature,
                'question':self.question,
                'progression':self.progression,
                'step':self.step
            }
        else:
            self.question = str(resp["parameters"]["question"])
            self.progression = float(resp["parameters"]["progression"])
            self.step = int(resp["parameters"]["step"])
            data = {
                'question':self.question,
                'progression':self.progression,
                'step':self.step
            }
        return data

    async def _get_session_info(self):
        """Get uid and frontaddr from akinator.com/game"""

        info_regex = re.compile("var uid_ext_session = '(.*)'\\;\\n.*var frontaddr = '(.*)'\\;")

        async with self.client_session.get(url="https://en.akinator.com/game", proxy=proxy) as w:
            match = info_regex.search(await w.text())

        self.uid, self.frontaddr = match.groups()[0], match.groups()[1]

    async def _auto_get_region(self, lang, theme):
        """Automatically get the uri and server from akinator.com for the specified language and theme"""

        server_regex = re.compile(
            "[{\"translated_theme_name\":\"[\s\S]*\",\"urlWs\":\"https:\\\/\\\/srv[0-9]+\.akinator\.com:[0-9]+\\\/ws\",\"subject_id\":\"[0-9]+\"}]")
        uri = lang + ".akinator.com"

        bad_list = ["https://srv12.akinator.com:9398/ws"]
        while True:
            u = "https://" + uri
            async with self.client_session.get(url=u, proxy=proxy) as w:
                match = server_regex.search(await w.text())

            parsed = json.loads(match.group().split("'arrUrlThemesToPlay', ")[-1])

            if theme == "c":
                server = next((i for i in parsed if i["subject_id"] == "1"), None)["urlWs"]
            elif theme == "a":
                server = next((i for i in parsed if i["subject_id"] == "14"), None)["urlWs"]
            elif theme == "o":
                server = next((i for i in parsed if i["subject_id"] == "2"), None)["urlWs"]

            if server not in bad_list:
                return {"uri": uri, "server": server}

    async def start_game(self, language=None, child_mode=False, client_session=None):
        self.timestamp = time.time()

        if client_session:
            self.client_session = client_session
        else:
            self.client_session = aiohttp.ClientSession()

        region_info = await self._auto_get_region(get_lang_and_theme(language)["lang"], get_lang_and_theme(language)["theme"])
        self.uri, self.server = region_info["uri"], region_info["server"]

        self.child_mode = child_mode
        soft_constraint = "ETAT%3D%27EN%27" if self.child_mode else ""
        self.question_filter = "cat%3D1" if self.child_mode else ""
        await self._get_session_info()

        async with self.client_session.get(NEW_SESSION_URL.format(self.uri, self.timestamp, self.server, str(self.child_mode).lower(), self.uid, self.frontaddr, soft_constraint, self.question_filter), headers=HEADERS, proxy=proxy) as w:
            r = await w.text()
            try:
                resp = json.loads(",".join(r.split("(")[1::])[:-1])
            except:
                raise Exception('网络错误，这可能是由于使用频率过高导致的')

        if resp["completion"] == "OK":
            data = self._update(resp, True)
            return data
        else:
            return raise_connection_error(resp["completion"])

    async def answer(self, ans, aki):
        ans = ans_to_id(ans)
        session = aki['session']
        signature = aki['signature']
        step = aki['step']
        async with self.client_session.get(ANSWER_URL.format(self.uri, self.timestamp, self.server, str(self.child_mode).lower(), session, signature, step, ans, self.frontaddr, self.question_filter), headers=HEADERS, proxy=proxy) as w:
            r = await w.text()
            try:
                resp = json.loads(",".join(r.split("(")[1::])[:-1])
            except:
                raise Exception('网络错误，这可能是由于使用频率过高导致的')


        if resp["completion"] == "OK":
            data = self._update(resp)
            return data
        else:
            return raise_connection_error(resp["completion"])

    async def back(self, aki):
        session = aki['session']
        signature = aki['signature']
        step = aki['step']
        if step == 0:
            raise Exception("You were on the first question and couldn't go back any further")

        async with self.client_session.get(BACK_URL.format(self.server, self.timestamp, str(self.child_mode).lower(), session, signature, self.step, self.question_filter), headers=HEADERS, proxy=proxy) as w:
            r = await w.text()
            try:
                resp = json.loads(",".join(r.split("(")[1::])[:-1])
            except:
                raise Exception('网络错误，这可能是由于使用频率过高导致的')

        if resp["completion"] == "OK":
            data = self._update(resp)
            return data
        else:
            return raise_connection_error(resp["completion"])

    async def win(self,aki):
        session = aki['session']
        signature = aki['signature']
        step = aki['step']
        async with self.client_session.get(WIN_URL.format(self.server, self.timestamp, str(self.child_mode).lower(), session, signature, step), headers=HEADERS, proxy=proxy) as w:
            r = await w.text()
            try:
                resp = json.loads(",".join(r.split("(")[1::])[:-1])
            except:
                raise Exception('网络错误，这可能是由于使用频率过高导致的')

        if resp["completion"] == "OK":
            first_guess = resp["parameters"]["elements"][0]["element"]
            self.guesses = [g["element"] for g in resp["parameters"]["elements"]]
            return first_guess
        else:
            return raise_connection_error(resp["completion"])

class Switch:
    def __init__(self):
        self.on = {}
        self.count = {}
        self.timeout = {}
        self.aki = {}

    def get_on_off_status(self, gid):
        return self.on[gid] if self.on.get(gid) is not None else False

    def turn_on(self, gid, uid, r):
        self.on[gid] = uid
        self.timeout[gid] = datetime.now()+timedelta(seconds=60)
        self.count[gid] = 0
        self.aki[gid] = r

    def turn_off(self, gid):
        self.on.pop(gid)
        self.count.pop(gid)
        self.timeout.pop(gid)
        self.aki.pop(gid)

    def count_plus(self, gid, r):
        self.count[gid] += 1
        self.aki[gid]['question'] = r['question']
        self.aki[gid]['progression'] = r['progression']
        self.aki[gid]['step']= r['step']