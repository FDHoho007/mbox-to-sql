#!/bin/python
from email.header import decode_header
import re, sys, datetime

def decode_mime_words(s):
    return u''.join(
        word.decode(encoding or 'utf8') if isinstance(word, bytes) else word
        for word, encoding in decode_header(s))

def parse_mbox(mbox_file_handle):
    mbox_archive = []
    header_block = True
    mbox_message = {}
    last_header = None
    for line in mbox_file_handle:
        if header_block:
            if line.strip() == "":
                if last_header is not None:
                    header_block = False
                    last_header = None
            elif line.startswith(" "):
                if last_header is not None:
                    mbox_message[last_header] += (line[1:] if mbox_message[last_header] == "" else line).replace("\n", "")
            elif ": " in line:
                header = line.split(": ")
                last_header = header[0]
                header_content = header[1]
                i = 2
                while i < len(header):
                    header_content += ": " + header[i]
                    i += 1
                mbox_message[last_header] = header_content.replace("\n", "")
            elif line.replace("\n", "").endswith(":"):
                last_header = line.replace("\n", "")[:-1]
                mbox_message[last_header] = ""
        else:
            if line.startswith("--=========="):
                if line.strip().endswith("--"):
                    m = re.fullmatch(r"(.+) <(.+)>", mbox_message["From"])
                    mbox_message["From"] = {
                        "name": decode_mime_words(m.group(1)) if m else None,
                        "address": m.group(2) if m else mbox_message["From"]
                    }
                    if mbox_message["From"]["name"] is not None and mbox_message["From"]["name"].startswith("\"") and mbox_message["From"]["name"].endswith("\"") and len(mbox_message["From"]["name"]) > 1:
                        mbox_message["From"]["name"] = mbox_message["From"]["name"][1:-1]
                    if "Date" in mbox_message:
                        mbox_message["Timestamp"] = int(datetime.datetime.strptime(mbox_message["Date"], "%a, %d %b %Y %X %z").timestamp())
                    mbox_archive.append(mbox_message)
                    mbox_message = {}
                    header_block = True
    return mbox_archive

if not len(sys.argv) == 2:
    print("Please provide only the path to one mbox file to analyze.")
if not sys.argv[1].endswith(".mbox"):
    print("Only .mbox files are allowed.")
name = sys.argv[1][:-5]
input = open(name + ".mbox", "r")
output = open(name + ".sql", "w")

output.write("START TRANSACTION;\n")
output.write("CREATE TABLE IF NOT EXISTS `" + name + "` (`MessageId` VARCHAR(255) NOT NULL PRIMARY KEY, `FromName` TEXT, `FromAddress` TEXT NOT NULL, `ToName` TEXT, `ToAddress` TEXT NOT NULL, `InReplyTo` VARCHAR(255), `Subject` TEXT NOT NULL, `Date` DATETIME);\n")
output.write("INSERT INTO `" + name + "` VALUES ")

first = True
header_block = True
mbox_message = {}
last_header = None
for line in input:
    if header_block:
        if line.strip() == "":
            if last_header is not None:
                header_block = False
                last_header = None
        elif line.startswith(" "):
            if last_header is not None:
                mbox_message[last_header] += (line[1:] if mbox_message[last_header] == "" else line).replace("\n", "")
        elif ": " in line:
            header = line.split(": ")
            last_header = header[0]
            header_content = header[1]
            i = 2
            while i < len(header):
                header_content += ": " + header[i]
                i += 1
            mbox_message[last_header] = header_content.replace("\n", "")
        elif line.replace("\n", "").endswith(":"):
            last_header = line.replace("\n", "")[:-1]
            mbox_message[last_header] = ""
    else:
        if line.startswith("--=========="):
            if line.strip().endswith("--"):
                if "Message-ID" in mbox_message:
                    m = re.fullmatch(r"(.+) <(.+)>", mbox_message["From"])
                    messageId = mbox_message["Message-ID"][1:-1] if mbox_message["Message-ID"].startswith("<") and mbox_message["Message-ID"].endswith(">") else mbox_message["Message-ID"]
                    fromName = decode_mime_words(m.group(1)) if m else None
                    fromAddress = m.group(2) if m else mbox_message["From"]
                    if fromName is not None and fromName.startswith("\"") and fromName.endswith("\"") and len(fromName) > 1:
                        fromName = fromName[1:-1]
                    m = re.fullmatch(r"(.+) <(.+)>", mbox_message["To"])
                    toName = decode_mime_words(m.group(1)) if m else None
                    toAddress = m.group(2) if m else mbox_message["To"]
                    if toName is not None and toName.startswith("\"") and toName.endswith("\"") and len(toName) > 1:
                        toName = toName[1:-1]
                    inReplyTo = (mbox_message["In-Reply-To"][1:-1] if mbox_message["In-Reply-To"].startswith("<") and mbox_message["In-Reply-To"].endswith(">") else mbox_message["In-Reply-To"]) if "In-Reply-To" in mbox_message else None
                    subject = mbox_message["Subject"]
                    #date = int(datetime.datetime.strptime(mbox_message["Date"], "%a, %d %b %Y %X %z").timestamp()) if "Date" in mbox_message else None
                    date = datetime.datetime.strptime(mbox_message["Date"], "%a, %d %b %Y %X %z").strftime("%Y-%m-%d %X") if "Date" in mbox_message else None
                    
                    sqlQuery = "(" if first else ",\n("
                    sqlQuery += "'" + messageId.replace("'", "\\'") + "', "
                    sqlQuery += "NULL, " if fromName is None else "'" + fromName.replace("'", "\\'") + "', "
                    sqlQuery += "'" + fromAddress.replace("'", "\\'") + "', "
                    sqlQuery += "NULL, " if toName is None else "'" + toName.replace("'", "\\'") + "', "
                    sqlQuery += "'" + toAddress.replace("'", "\\'") + "', "
                    sqlQuery += "NULL, " if inReplyTo is None else "'" + inReplyTo.replace("'", "\\'") + "', "
                    sqlQuery += "'" + subject.replace("'", "\\'") + "', "
                    sqlQuery += "NULL" if date is None else "'" + date.replace("'", "\\'") + "'"
                    sqlQuery += ")"
                    output.write(sqlQuery)
                else:
                    print("Skipping message without Message id.")

                mbox_message = {}
                header_block = True
                first = False

output.write(";\nCOMMIT;")