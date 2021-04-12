import pymongo

class DbMongoSaver:
    bd_name = "Data_Mining"
    collection_name = "youla_cars"

    def __init__(self):
        self.db_client = pymongo.MongoClient("mongodb://localhost:27017")
        self.db = self.db_client[self.bd_name]
        self.db_collection = self.db[self.collection_name]

    def save_data(self, data):
        self.db_collection.insert_one(data)


