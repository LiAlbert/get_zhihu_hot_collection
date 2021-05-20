import requests
import json
from brotli import decompress as br_decode
from time import sleep
from bs4 import BeautifulSoup
import re
import sqlite3

def pare_header_file(file_path):
    header = {}
    with open(file_path) as f:
        for line in f.readlines():
            l = line.strip().split(": ")
            if(len(l)==2):
                header[l[0]] =l[1]
    return header


zhi_main_page_link = "https://www.zhihu.com"

def clear_number(number_str):
    match = re.search(r"[\d,\,]+", number_str)
    if match:
        return int(match.group().replace(',',''))
    else:
        return 0

class Collection():
    create_table_sql = "create table ZhihuHotCollections (_id INTEGER primary key autoincrement, title TEXT, link TEXT unique, creatorName TEXT, creatorLink TEXT, creatorPicLink TEXT, followersCount INTEGER, collectedItemCount INTEGER, sampleItemType TEXT, sampleItemTitle TEXT, sampleItemContentExcerpt Text, sampleItemLink Text, sampleItemVoteupCount INTEGER, sampleItemCommentCount INTEGER)"
    insert_sql = "insert into ZhihuHotCollections(%s) values(" + "".join(["?,"] * (len(create_table_sql.split(","))-2)) + "?)"
    def init(self):
        self.title = ""
        self.link = ""
        self.creatorName = ""
        self.creatorLink = ""
        self.creatorPicLink = ""
        self.followersCount = 0
        self.collectedItemCount = 0
        self.sampleItemType = ""
        self.sampleItemTitle = ""
        self.sampleItemContentExcerpt = ""
        self.sampleItemLink = ""
        self.sampleItemVoteupCount = 0
        self.sampleItemCommentCount = 0

    def __init__(self,data):
        self.init()
        if data.__class__.__name__ == "Tag":
            global zhi_main_page_link
            try:
                title_tag = data.select_one("a.CollectionListCard-title")
                if title_tag:
                    self.title = title_tag.text
                    self.link = zhi_main_page_link + title_tag["href"]
                
                self.creatorName = data.select_one(
                    "span.CollectionListCard-creatorName").text
                self.creatorPicLink = data.select_one(
                    "img.UserLink-avatar")["src"]
                followersCountText = data.select_one(
                    ".CollectionListCard-followersCount").text
                
                self.followersCount = clear_number(
                    followersCountText)

                collectedItemCountText = data.select_one(
                    ".CollectionListCard-entry").text
                self.collectedItemCount = clear_number(collectedItemCountText)
                
                title_tag = data.select_one(".CollectionListCard-contentTitle")
                if title_tag:
                    self.sampleItemTitle = title_tag.text
                    self.sampleItemLink = title_tag["href"]
                self.sampleItemContentExcerpt = data.select_one(
                    ".CollectionListCard-contentExcerpt").text
                
                self.sampleItemType = data.select_one(
                    ".CollectionListCard-contentTypeTag").text
                contentCountTags = data.select(".CollectionListCard-contentCountTag")
                if contentCountTags and len(contentCountTags) == 2:
                    self.sampleItemVoteupCount = clear_number(contentCountTags[0].text)
                    self.sampleItemCommentCount = clear_number(
                        contentCountTags[1].text)

                self.creatorLink = "https:" + data.select_one(".UserLink-link")["href"]
            except Exception as e:
                print(e)
            print("clean collection finish!")

        elif data.__class__.__name__ == "dict":
            try:
                self.title = data["title"]
                self.link = data["url"].replace(
                    "api/v4/collections", "collection")
                self.followersCount = data["follower_count"]
                self.collectedItemCount = data["total_count"]
                self.creatorName = data["creator"]["name"]
                creator_token = data["creator"].get("url_token")
                if creator_token and len(creator_token):
                    self.creatorLink = "https://www.zhihu.com/people/"+ creator_token
                self.creatorPicLink = data["creator"]["avatar_url"]

                sampleItem = data["favitems"][0]["content"]
                self.sampleItemCommentCount = sampleItem["comment_count"]
                self.sampleItemVoteupCount = sampleItem["voteup_count"]
                self.sampleItemContentExcerpt = sampleItem["excerpt"]
                if sampleItem["type"] == "answer":
                    self.sampleItemType = "回答"
                    self.sampleItemTitle = sampleItem["question"]["title"]
                    self.sampleItemLink = sampleItem["url"].replace(
                        "api/v4/answers", "answer")
                elif sampleItem["type"] == "article":
                    self.sampleItemType = "文章"
                    self.sampleItemTitle = sampleItem["title"]
                    self.sampleItemLink = sampleItem["url"]

            except Exception as e:
                print(e)
            print("clean collection finish!")

        else:
            print()
            print("wrong paramater, the data paramater should be a Beautifuldata Tag or a json dict!")
    
    def dumpToSqlite(self,sqlite_cur):
        check_table_exist_sql = "select count(*) from sqlite_master where tbl_name='ZhihuHotCollections' and type='table'"
        sqlite_cur.execute(check_table_exist_sql)
        table_exist = sqlite_cur.fetchone()[0]
        if not table_exist:
            sqlite_cur.execute(self.create_table_sql)
        
        try:
            sqlite_cur.execute(self.insert_sql % (",".join(list(self.__dict__.keys()))), tuple(self.__dict__.values()))
        except Exception as e:
            print(self.insert_sql % (",".join(list(self.__dict__.keys()))))
            print(e)



header = pare_header_file("header.txt")
header2 = pare_header_file("header2.txt")

url = "https://www.zhihu.com/collection/hot"
res = requests.get(url, headers=header)
print(res.headers["content-encoding"])
# html = br_decode(res.content).decode(res.encoding)
html = res.content.decode(res.encoding)
soup = BeautifulSoup(html, features="lxml")
collections = soup.select(".CollectionListCard")
sqlite_conn = sqlite3.connect("test.sqlite")
sqlite_cur = sqlite_conn.cursor()

for collection in collections: 
    collection_obj = Collection(collection)
    collection_obj.dumpToSqlite(sqlite_cur)



with open("zhihu_hot_collenction.html","wb") as f:
    f.write(html.encode('utf-8'))
offset = 10
url_next = "https://www.zhihu.com/api/v4/favlists/discover?include=data%5B%2A%5D.updated_time%2Ctotal_count%2Ccreator%2Cfollower_count%2Cis_following%3Bdata%5B%2A%5D.favitems%5B%2A%5D.content.question%2Cexcerpt%2Cvoteup_count%2Ccomment_count&limit=10&offset="
while True:
    url = url_next + str(offset)
    res = requests.get(url,headers=header)
    file_name = "zhihu_top"+str(offset)+"-"+str(offset+10)+"_collection.json"
    collections = res.json()
    with open(file_name,"wb") as f:
        f.write(res.content)
    if collections["paging"]["is_end"]:
        break
    else:
        for collection in collections["data"]:
            collection_obj = Collection(collection)
            collection_obj.dumpToSqlite(sqlite_cur)

    sleep(0.5)
    offset+=10

sqlite_conn.commit()
