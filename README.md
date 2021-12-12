# Python JsonPath
A Python toolkit for parsing JSON document

Inspired by: https://github.com/json-path/JsonPath

## Quick Start
install it using the pip command
```
pip install pyjsonpath
```
Then:
```
>>> from pyjsonpath import JsonPath
>>> obj = {"name": "jsonpath"}
>>> JsonPath(obj, "$.name").load()
['jsonpath']
>>>
```

## JsonPath Syntax
- General Operators

|operators|description|
|---|---|
|$|	The root element to query. This starts all path expressions.|
|@|	The current node being processed by a filter predicate.|
|*|	Wildcard. Available anywhere a name or numeric are required.|
|..| Deep scan. Available anywhere a name is required.|
|.<name>|Dot-notated child|
|['\<name\>' (, '\<name>\')]|Bracket-notated child or children|
|[\<number\> (, \<number\>)]|Array index or indexes|
|[start:end]|Array slice operator|
|[?(\<expression\>)]|Filter expression. Expression must evaluate to a boolean value.|

- Filter Operators

|operators|description|
|---|---|
|==	|left is equal to right (note that 1 is not equal to '1')|
|!=	|left is not equal to right|
|<	|left is less than right|
|<=	|left is less or equal to right|
|>	|left is greater than right|
|>=	|left is greater than or equal to right|
|=~	|left matches regular expression [?(@.name =~ /foo.*?/i)]|
|in	|left exists in right [?(@.size in ['S', 'M'])]|
|nin|left does not exists in right|
|subsetof|left is a subset of right [?(@.sizes subsetof ['S', 'M', 'L'])]|
|anyof|left has an intersection with right [?(@.sizes anyof ['M', 'L'])]|
|noneof|left has no intersection with right [?(@.sizes noneof ['M', 'L'])]|
|size|size of left (array or string) should match right|
|empty|left (array or string) should be empty|

- Functions

|operators|description|
|---|---|
|min()|Provides the min value of an array of numbers|
|max()|Provides the max value of an array of numbers|
|avg()|Provides the average value of an array of numbers|
|stddev()|Provides the standard deviation value of an array of numbers|
|length()|Provides the length of an array|
|sum()|Provides the sum value of an array of numbers|
|keys()|Provides the property keys (An alternative for terminal tilde ~)|
