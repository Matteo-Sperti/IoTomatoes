import MyExceptions
from pymongo import MongoClient

ciao=MongoClient("mongodb+srv://admin:admin@cluster0.lzvxrr9.mongodb.net/?retryWrites=true&w=majority")
print(ciao.list_database_names())