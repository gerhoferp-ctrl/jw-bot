#!/usr/bin/env python3
"""
# versione 1.1
Bot Telegram per le novità di https://www.jw.org/it/cosa-nuovo/

Controlla la pagina, trova gli elementi nuovi e manda un messaggio Telegram
per ognuno.

Variabile d'ambiente richiesta:
  TELEGRAM_TOKEN    il codice del bot ricevuto da @BotFather
Facoltativa:
  TELEGRAM_CHAT_ID  la chat a cui scrivere. Se manca, il bot usa la prima
                    persona che gli ha scritto /start e la ricorda in chat_id.txt
"""

import html
import json
import os
import re
import sys
import time
import urllib.parse
from pathlib import Path

import requests
from bs4 import BeautifulSoup

URL = "https://www.jw.org/it/cosa-nuovo/"
BASE = "https://www.jw.org"
STATE_FILE = Path(__file__).with_name("seen.json")
CHAT_FILE = Path(__file__).with_name("chat_id.txt")
DATE_RE = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")
HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept-Language": "it-IT,it;q=0.9",
}


def fetch_items():
    """Restituisce la lista degli elementi della pagina, dal più recente."""
    r = requests.get(URL, headers=HEADERS, timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    items, seen_links = [], set()
    for h3 in soup.find_all("h3"):
        a = h3.find("a", href=True)
        if not a:
            continue
        link = urllib.parse.urljoin(BASE, a["href"])
        if "/it/" not in link or link.rstrip("/") == URL.rstrip("/") or link in seen_links:
            continue
        title = a.get_text(" ", strip=True)
        if not title:
            continue

        # Risale al riquadro dell'elemento per trovare data, categoria e descrizione
        box = h3
        for _ in range(5):
            if box.parent is None:
                break
            box = box.parent
            if DATE_RE.search(box.get_text(" ", strip=True)):
                break
        text = box.get_text("\n", strip=True)
        m = DATE_RE.search(text)
        date = m.group(1) if m else ""

        category = ""
        cat_el = box.find(class_=re.compile(r"contextTtl|context|category", re.I))
        if cat_el:
            category = cat_el.get_text(" ", strip=True)
        else:
            # fallback: la riga in MAIUSCOLO prima del titolo
            for line in text.split("\n"):
                if line == title:
                    break
                if line.isupper() and len(line) > 2:
                    category = line

        desc = ""
        p = h3.find_next_sibling("p")
        if p:
            desc = p.get_text(" ", strip=True)

        seen_links.add(link)
        items.append({"link": link, "title": title, "date": date,
                      "category": category, "desc": desc})
    return items


def load_state():
    if STATE_FILE.exists():
        return set(json.loads(STATE_FILE.read_text(encoding="utf-8")))
    return None


def save_state(links):
    STATE_FILE.write_text(json.dumps(sorted(links), ensure_ascii=False, indent=1),
                          encoding="utf-8")


API = "https://api.telegram.org/bot{token}/{method}"


def tg(method, **params):
    token = os.environ["TELEGRAM_TOKEN"].strip()
    r = requests.post(API.format(token=token, method=method), data=params, timeout=30)
    data = r.json()
    if not data.get("ok"):
        raise RuntimeError(f"Telegram {method} fallito: {data}")
    return data["result"]


def get_chat_id():
    env = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if env:
        return env
    if CHAT_FILE.exists():
        return CHAT_FILE.read_text().strip()
    # Cerca chi ha scritto /start al bot
    for upd in reversed(tg("getUpdates")):
        msg = upd.get("message") or {}
        chat = msg.get("chat") or {}
        if chat.get("type") == "private":
            CHAT_FILE.write_text(str(chat["id"]))
            return str(chat["id"])
    print("Nessuna chat trovata: apri il tuo bot su Telegram, premi Avvia (/start) "
          "e rilancia il workflow.")
    sys.exit(1)


def send(chat_id, text):
    tg("sendMessage", chat_id=chat_id, text=text, parse_mode="HTML",
       disable_web_page_preview="true")


MESI = ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio",
        "agosto", "settembre", "ottobre", "novembre", "dicembre"]

EMOJI = [("NEWS", "🗞"), ("CANZON", "🎵"), ("MUSIC", "🎵"), ("VIDEO", "🎬"),
         ("BROADCAST", "🎬"), ("TORRE", "📖"), ("VIGILATE", "📖"), ("RIVIST", "📖"),
         ("GUIDA", "🗒"), ("ADUNANZA", "🗒"), ("LIBR", "📚"), ("OPUSCOL", "📚"),
         ("INDIC", "🔎"), ("DONAZION", "🌍")]


def esc(s):
    return html.escape(s, quote=False)


def data_it(d):
    try:
        y, m, g = d.split("-")
        return f"{int(g)} {MESI[int(m) - 1]} {y}"
    except Exception:
        return d


def emoji_for(category):
    up = category.upper()
    for key, em in EMOJI:
        if key in up:
            return em
    return "📢"


def get_image(link):
    """Immagine principale dell'articolo (og:image), se c'è."""
    try:
        r = requests.get(link, headers=HEADERS, timeout=30)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        for attr, name in (("property", "og:image"), ("name", "twitter:image")):
            tag = soup.find("meta", attrs={attr: name})
            if tag and tag.get("content") and "placeholder" not in tag["content"]:
                return urllib.parse.urljoin(BASE, tag["content"])
    except Exception as e:
        print(f"Immagine non trovata per {link}: {e}")
    return None


def format_caption(it):
    cat = it["category"].strip()
    lines = [f"{emoji_for(cat)} <b>{esc(it['title'])}</b>", ""]
    meta = []
    if cat:
        meta.append(f"🏷 {esc(cat.title())}")
    if it["date"]:
        meta.append(f"🗓 {data_it(it['date'])}")
    if meta:
        lines.append("  ·  ".join(meta))
    if it["desc"]:
        desc = it["desc"] if len(it["desc"]) <= 600 else it["desc"][:597] + "…"
        lines += ["", f"<i>{esc(desc)}</i>"]
    return "\n".join(lines)


def send_item(chat_id, it, intro=""):
    caption = (intro + format_caption(it))[:1024]
    button = json.dumps({"inline_keyboard": [[
        {"text": "📖 Leggi su JW.ORG", "url": it["link"]}]]})
    image = get_image(it["link"])
    if image:
        try:
            tg("sendPhoto", chat_id=chat_id, photo=image, caption=caption,
               parse_mode="HTML", reply_markup=button)
            return
        except Exception as e:
            print(f"Foto non inviata, mando solo testo: {e}")
    tg("sendMessage", chat_id=chat_id, text=caption, parse_mode="HTML",
       disable_web_page_preview="true", reply_markup=button)


def main():
    chat_id = get_chat_id()
    items = fetch_items()
    if not items:
        print("Nessun elemento trovato: forse la pagina è cambiata.")
        sys.exit(1)

    seen = load_state()
    if seen is None:
        # Primo avvio: memorizza tutto senza inviare, solo un messaggio di conferma
        send_item(chat_id, items[0],
                  intro="✅ <b>Bot JW.ORG attivo!</b> Ti avviserò per ogni novità.\n"
                        "Ecco l'ultima uscita:\n\n")
        save_state({i["link"] for i in items})
        print(f"Primo avvio: {len(items)} elementi memorizzati.")
        return

    new = [i for i in items if i["link"] not in seen]
    # Dal più vecchio al più recente, così in chat arrivano in ordine
    for it in reversed(new):
        send_item(chat_id, it)
        seen.add(it["link"])
        save_state(seen)          # salva subito: niente doppioni se un invio fallisce
        time.sleep(1)
    print(f"{len(new)} novità inviate.")


if __name__ == "__main__":
    main()
