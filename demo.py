# -*- coding: utf-8 -*-

# obj = {
#     "store": {
#         "book": [
#             {
#                 "category": "reference",
#                 "author": "Nigel Rees",
#                 "title": "Sayings of the Century",
#                 "price": 8.95
#             },
#             {
#                 "category": "fiction",
#                 "author": "Evelyn Waugh",
#                 "title": "Sword of Honour",
#                 "price": 12.99
#             },
#             {
#                 "category": "fiction",
#                 "author": "Herman Melville",
#                 "title": "Moby Dick",
#                 "isbn": "0-553-21311-3",
#                 "price": 8.99
#             },
#             {
#                 "category": "fiction",
#                 "author": "J. R. R. Tolkien",
#                 "title": "The Lord of the Rings",
#                 "isbn": "0-395-19395-8",
#                 "price": 22.99
#             }
#         ],
#         "bicycle": {
#             "color": "red",
#             "price": 19.95
#         }
#     },
#     "expensive": 10
# }
# expr = "$..[?(@.category in ['reference'])]"

obj = {"key": [1, 2, 3, 0], "key1": [{"size": "S"}, {"size": "M"}, {"size": "L"}]}
expr = "$.key1[?(@.size in ['S', 'M'])]"

from pyjsonpath import JsonPath
result = JsonPath(obj, expr).load()
print(len(result), result)
