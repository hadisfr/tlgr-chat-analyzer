#!/usr/bin/env python3

import csv
import glob
import re
from itertools import chain
from os import sep
from sys import argv, stderr
from typing import Any, Dict, Iterable
from html import unescape

from tqdm import tqdm


def parse_message(raw_message: str) -> Dict[str, Any]:
    id_type_pattern = re.compile(r"<div class=\"message default clearfix( joined)?\" id=\"([^\"]+?)\">")
    date_pattern = re.compile(r"<div class=\"pull_right date details\" title=\"([^\"]+?)\">")
    text_pattern = re.compile(r"(?s)<div class=\"text\">(.+?)</div>")
    from_pattern = re.compile(r"(?s)<div class=\"from_name\">(.+?)</div>")
    is_media_pattern = re.compile(r"<div class=\"media_wrap")
    media_title_pattern = re.compile(r"(?s)<div class=\"title bold\">(.+?)</div>")
    media_description_pattern = re.compile(r"(?s)<div class=\"description\">(.+?)</div>")
    meida_status_pattern = re.compile(r"(?s)<div class=\"status details\">(.+?)</div>")
    is_reply_pattern = re.compile(r"<div class=\"reply_to")
    reply_to_pattern = re.compile(r"(?s)<div class=\"reply_to details\">\s*"
                                  r"In reply to "
                                  r"<a href=\"#go_to_([^\"]+?)\" onclick=\"return GoToMessage\([^)]+?\)\">"
                                  r"this message</a>\s*"
                                  r"</div>")
    is_forwarded_pattern = re.compile(r"<div class=\"forwarded")
    forwarded_pattern = re.compile(r"(?s)<div class=\"forwarded body\">\s*"
                                   r"<div class=\"from_name\">\s*"
                                   r"(.+?)<span class=\"date details\" title=\"([^\"]+?)\">.+?</span>\s*"
                                   r"</div>")
    sign_pattern = re.compile(r"(?s)<div class=\"signature details\">(.+?)</div>")
    via_pattern = re.compile(r"\s+via\s+@(.*)")

    def get_field(raw_message: str, pattern: re.Pattern, group_index=0) -> str:
        matches = pattern.findall(raw_message)
        # assert len(matches) in {0, 1}, "more than one pattern match found for\t%s in\n%s" % (pattern, raw_message)
        if not matches:
            return None
        res = matches[0]
        if not isinstance(res, tuple):
            res = (res,)
        res = res[group_index]
        return res.strip()
    
    message = {
        "Id": get_field(raw_message, id_type_pattern, 1),
        "Is Joined": bool(get_field(raw_message, id_type_pattern, 0)),
        "Date": get_field(raw_message, date_pattern),
        "From": get_field(raw_message, from_pattern, 0),
        "Signed By": get_field(raw_message, sign_pattern, 0),
        "Text": clean_text(get_field(raw_message, text_pattern)),
        "Is Reply": bool(get_field(raw_message, is_reply_pattern)),
        "Reply To": get_field(raw_message, reply_to_pattern),
        "Has Media": bool(get_field(raw_message, is_media_pattern)),
        "Media Title": get_field(raw_message, media_title_pattern),
        "Media Description": get_field(raw_message, media_description_pattern),
        "Media Status": get_field(raw_message, meida_status_pattern),
        "Is Forwarded": bool(get_field(raw_message, is_forwarded_pattern)),
        "Forwarded From": get_field(raw_message, forwarded_pattern, 0),
        "Forwarded Original Date": get_field(raw_message, forwarded_pattern, 1),
    }
    if message["From"]:
        message["Via"] = get_field(message["From"], via_pattern)
        message["From"] = via_pattern.sub("", message["From"])
    else:
        message["Via"] = None

    if not message["Text"] and not message["Has Media"]:
        print("Empty message %s\tChance animated 🎲🎯🏀 emojies?" % message["Id"])

    return message


def clean_text(text: str) -> str:
    if not text:
        return text
    text = re.sub(r"<a[^>]+?>", "", text)
    text = text.replace("</a>", "")
    text = re.sub(r"<span[^>]*?>", "", text)
    text = text.replace("</span>", "")
    text = text.replace("<strong>", "")
    text = text.replace("</strong>", "")
    text = text.replace("<em>", "")
    text = text.replace("</em>", "")
    text = text.replace("<u>", "")
    text = text.replace("</u>", "")
    text = text.replace("<code>", "")
    text = text.replace("</code>", "")
    text = text.replace("<pre>", "")
    text = text.replace("</pre>", "")
    text = text.replace("<br>", "\n")
    text = unescape(text)
    text = text.strip()
    return text


def read_messages(file_addr: str) -> Iterable[Dict[str, Any]]:
    msg_pattern = re.compile(r"(?s)     <div class=\"message default.*?\n     </div>")

    with open(file_addr) as f:
        messages = list(msg_pattern.findall(f.read()))
    messages = map(parse_message, messages)
    
    last_from = None
    last_forwarded_from = None
    last_forwarded_date = None
    for message in messages:
        if message["Is Joined"]:
            message["From"] = last_from
        else:
            last_from = message["From"]
        del message["Is Joined"]

        if message["Is Forwarded"]:
            if message["Forwarded From"]:
                last_forwarded_from = message["Forwarded From"]
            else:
                message["Forwarded From"] = last_forwarded_from
            if message["Forwarded Original Date"]:
                last_forwarded_date = message["Forwarded Original Date"]
            else:
                message["Forwarded Original Date"] = last_forwarded_date
        else:
            last_forwarded_from = None
            last_forwarded_date = None

        yield message


def find_message_files(chats_addr: str) -> Iterable[str]:
    file_name_pattern = re.compile(r"messages([0-9]*).html")

    def get_file_number(file_addr: str) -> int:
        file_name = file_addr.split(sep)[-1]
        file_num = file_name_pattern.findall(file_name)[0]
        file_num = int(file_num) if file_num else 1
        return file_num

    files = glob.iglob(sep.join([chats_addr, "messages*.html"]))
    files = sorted(files, key=get_file_number)
    return files


def write_message(messages: Iterable[Dict[str, Any]], addr: str) -> None:
    first_message = next(messages)
    with open(addr, "w") as f:
        writer = csv.DictWriter(f, list(first_message.keys()))
        writer.writeheader()
        writer.writerow(first_message)
        writer.writerows(tqdm(messages, desc="Parsed", unit=" Messages", initial=1))


def parse_chats(chats_addr: str, output_addr: str) -> None:
    files_addr = find_message_files(chats_addr)
    messages = chain(*map(read_messages, files_addr))
    write_message(messages, output_addr)


def main():
    if len(argv) != 3:
        print("usage:\t%s <ChatExport Dir Path> <Output CSV Path>" % argv[0], file=stderr)
        exit(2)

    parse_chats(argv[1], argv[2])


if __name__ == '__main__':
    main()
