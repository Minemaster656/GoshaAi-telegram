import uuid
from enum import Enum

import pymongo
from pymongo import MongoClient

import Data
import env

client = MongoClient(env.MONGO_URL)
db = client[Data.DB_NAME]
col_history = db.get_collection("history_chunks")
col_messages = db.get_collection("messages")
class Scemes(Enum):
    HISTORY_CHUNK = 1
    MESSAGE = 2

def schema(document: dict, scheme: Scemes) -> dict:
    fields = {}
    if scheme == Scemes.HISTORY_CHUNK:
        fields = {
            "UUID": None, #UUID
            "messages": [],
            "last_update": 0,
            "target_id": 0
        }
    if scheme == Scemes.MESSAGE:
        fields = {
            "UUID": None, #UUID
            "message": "",
            "user_id": 0,
            "group_id": 0,
            "assistant": False,
            "author_name": "",
            "timestamp": 0 #time.time()
        }


    fields_check = {}
    if not document:
        document = fields
    for k in fields.keys():
        fields_check[k] = False
    for k in document.keys():
        if k in fields.keys():
            fields_check[k] = True
    for k in fields_check:
        if not fields_check[k]:
            document[k] = fields[k]
            fields_check[k] = True
    if "UUID" in document.keys():
        if document["UUID"] is None:
            document["UUID"] = str(uuid.uuid4())
    return document

def getTelegramUserByID(id_telegram: int, query: dict={}) -> dict:
    dbQuery = {"id_telegram": id_telegram}
    dbQuery.update(query)
    doc = db["users"].find_one(dbQuery)
    return {}
# def getGroupsWhereCanWrite(id_telegram: int, query_: dict={}):
#     query = {"$or": [
#         {"writers": id_telegram},
#         {"admins": id_telegram},
#         {"owner": id_telegram}
#         ]
#     }
#     query.update(query_)
#     return db["groups"].find(query)
# def getArrayOfGroupsByUUIDs(uuids: list) -> list:
#     docs = []
#     for uuid in uuids:
#         docs.append(schema(db["groups"].find_one({"UUID": uuid}), Scemes.GROUP))
#     return docs
# def groupDocToUniqueUsers(doc: dict) -> list:
#     users = {}
#     for user in doc["subscribers"]:
#         users[user] = True
#     for user in doc["writers"]:
#         users[user] = True
#     for user in doc["admins"]:
#         users[user] = True
#     users[doc["owner"]] = True
#     return list(users.keys())

