# -*- coding: utf-8 -*-
import re
import traceback
from math import sqrt
from copy import deepcopy

pattern_dict = r'\[("|\').+?("|\')\]'
pattern_index = r'\[[0-9]+[, 0-9]*\]'
pattern_split = r'\[((\*)|((-)?[0-9]*:(-)?[0-9]*))\]'
pattern_dot = r'\.(\*)?'
pattern_double_dot = r'\.\.((\*)|(\[\*\]))?'
pattern_normal_type = r'[\-\_0-9a-zA-Z\u4e00-\u9fa5]+(\(\))?'
pattern_controller_type = r'\[\?\(.+?\)\]'
pattern_filter_type = r'\s(in|nin|subsetof|anyof|noneof|size|empty|[\!\=\>\<\~])\s?'


def math_avg(L):
    return sum(L) / len(L)

def math_stddev(L):
    a = math_avg(L)
    return sqrt(sum([(i - a) * (i - a) for i in L]) / (len(L) - 1))

func_dict = {'min()': min, 'max()': max, 'avg()': math_avg, 'stddev()': math_stddev, 'length()': len, 'sum()': sum}

class UnExpectJsonPathError(Exception):
    pass

class JsonPath(object):

    def __init__(self, obj, expr):
        self.obj = obj
        self.expr = expr

    def load(self):
        if not self.expr.startswith('$'):
            raise ValueError("'expr' is not a parsable JsonPath format")

        result = []
        try:
            self.start_parsing(self.obj, self.expr, result)
        except (KeyError, UnExpectJsonPathError):
            fmt = traceback.format_exc()
            print(fmt)
        return result

    def start_parsing(self, obj, expr, result):
        if expr:
            result.clear()
            if expr.startswith('$'):
                obj, expr = self.match_parsing(self.obj, expr)
                result.extend(obj)
                self.start_parsing(obj, expr, result)
            elif expr.startswith('[?('):
                obj, expr = self.controller_parsing(obj, expr)
                result.extend(obj)
                self.start_parsing(obj, expr, result)
            elif expr.startswith('['):
                obj, expr = self.index_parsing(obj, expr)
                result.extend(obj)
                self.start_parsing(obj, expr, result)
            elif expr.startswith(".."):
                obj, expr = self.scan_parsing(obj, expr)
                result.extend(obj)
                self.start_parsing(obj, expr, result)
            elif expr.startswith("."):
                obj, expr = self.dot_parsing(obj, expr)
                result.extend(obj)
                self.start_parsing(obj, expr, result)
            else:
                obj, expr = self.normal_parsing(obj, expr)
                result.extend(obj)
                self.start_parsing(obj, expr, result)

    def match_parsing(self, obj, expr):
        expr = expr[1:]
        result = [obj]
        return result, expr

    def index_parsing(self, obj, expr):
        result = []
        dit = re.match(pattern_dict, expr)
        idx = re.match(pattern_index, expr)
        spt = re.match(pattern_split, expr)
        if dit:
            g = dit.group()
            key = g[2:-2]
            for item in obj:
                if isinstance(item, dict) and key in item:
                    value = item[key]
                    result.append(value)
            expr = expr[len(g):]
        elif idx:
            g = idx.group()
            index_list = eval(g)
            for item in obj:
                if isinstance(item, list):
                    for index in index_list:
                        value = item[int(index)]
                        result.append(value)
            expr = expr[len(g):]
        elif spt:
            g = spt.group()
            if g == '[*]':
                for item in obj:
                    if isinstance(item, list):
                        result.extend(item)
                    elif isinstance(item, dict):
                        result.extend(list(item.values()))
            else:
                s = g[1:-1]
                start, end = s.split(':')
                start = start.strip()
                end = end.strip()
                for item in obj:
                    if isinstance(item, list):
                        if not start:
                            start = 0
                        if not end:
                            end = len(item)
                        start, end = int(start), int(end)
                        result.extend(item[start:end])
            expr = expr[len(g):]
        return result, expr

    def scan_parsing(self, obj, expr):
        result = []

        def scan(value, x=''):
            if isinstance(value, list):
                result.append(value)
                for item in value:
                    scan(item, x)
            elif isinstance(value, dict):
                result.append(value)
                for item in value.values():
                    scan(item, x)
            elif x == '*' or x == '[*]':
                result.append(value)

        g = re.match(pattern_double_dot, expr)
        if g:
            g = g.group()
            x = g[2:]
            if not x:
                scan(obj[0])
            elif x == '*' or x == '[*]':
                if isinstance(obj[0], dict):
                    for item in obj[0].values():
                        scan(item, x)
                elif isinstance(obj[0], list):
                    for item in obj[0]:
                        scan(item, x)

            expr = expr[len(g):]
        return result, expr

    def dot_parsing(self, obj, expr):
        result = []
        g = re.match(pattern_dot, expr)
        if g:
            g = g.group()
            key = g[1:]
            if not key:
                result = deepcopy(obj)
            else:
                for item in obj:
                    if isinstance(item, list):
                        result.extend(item)
                    elif isinstance(item, dict):
                        result.extend(list(item.values()))
            expr = expr[len(g):]
        return result, expr

    def normal_parsing(self, obj, expr):
        result = []
        g = re.match(pattern_normal_type, expr)
        if g:
            g = g.group()
            for item in obj:
                if isinstance(item, dict) and g in item:
                    result.append(item[g])
                elif isinstance(item, list):
                    if re.search(r"^[0-9]+$", g):
                        result.append(obj[int(g)])
                    elif all([
                        all([isinstance(i, (int, float)) for i in item]),
                        g in ('min()', 'max()', 'avg()', 'stddev()', 'length()', 'sum()')
                    ]):
                        f = func_dict[g]
                        result.append(f(item))
                    elif isinstance(item, dict) and g == 'keys()':
                        value = list(item.keys())
                        result.extend(value)
            expr = expr[len(g):]
        return result, expr

    def parse_value(self, value, compare):
        if value.startswith('$'):
            res = []
            self.start_parsing(self.obj, value, res)
            return res
        else:
            print('value', value)
            return value if compare == '=~' else eval(value)

    def normalize(self, old, new):
        old = old.strip()
        if not old:
            return new
        if old.startswith("&&"):
            new += f"and "
            old = old[3:]
        elif old.startswith("||"):
            new += f"or "
            old = old[3:]

        expr = "(@((\.[_0-9a-zA-Z\u4e00-\u9fa5]+)|(\[(\"|').+?(\"|')\]))\s?(in|nin|subsetof|anyof|noneof|size|empty|[\!\=\>\<\~])?(\s(true|false|null|\d+\.?\d*|\/.*?/i|'.*?'))?)|((true|false|null|\d+\.?\d*|\/.*?/i|'.*?')\s(in|nin|subsetof|anyof|noneof|[\!\=\>\<])\s@((\.[_0-9a-zA-Z\u4e00-\u9fa5]+)|(\[(\"|').+?(\"|')\])))"
        m = re.match(expr, old)
        if m:
            s = m.group()
            spt = re.split(pattern_filter_type, s)
            if spt and len(spt) == 3:
                left, compare, right = spt
                compare = compare.replace('nin', 'not in')
                if left.startswith('@'):
                    if right in ('True', 'False', 'null'):
                        right = right.replace('true', 'True').replace('false', 'False').replace('null', 'None')
                    # right = self.parse_value(right, compare)
                    s_ = re.sub(r"\.([_0-9a-zA-Z\u4e00-\u9fa5]+)", r"['\1']", left)
                    if compare in ('empty', 'size'):
                        right = 0 if compare == 'empty' else right
                        new += f"len(child{s_[1:]}) == {right} "
                    elif compare == "subsetof":
                        new += f"set(child{s_[1:]}) < set({right}) "
                    elif compare == "anyof":
                        new += f"set(child{s_[1:]}) & set({right}) "
                    elif compare == "noneof":
                        new += f"not set(child{s_[1:]}) & set({right}) "
                    elif compare == "=~":
                        if not isinstance(right, str) or not right.startswith("/") or not right.endswith("/i"):
                            raise UnExpectJsonPathError('Ungrammatical JsonPath')
                        new += f"re.match('{right[1:-3]}', child{s_[1:]}, re.I) "
                    else:
                        new += f"child{s_[1:]} {compare} {right} "
                elif right.startswith('@'):
                    if left in ('True', 'False', 'null'):
                        left = left.replace('true', 'True').replace('false', 'False').replace('null', 'None')
                    # left = self.parse_value(left, compare)
                    s_ = re.sub(r"\.([_0-9a-zA-Z\u4e00-\u9fa5]+)", r"['\1']", right)
                    if compare in ('empty', 'size', '=~'):
                        raise Exception('不符合语法的JsonPath')
                    elif compare == "subsetof":
                        new += f"set({left}) < set(child{s_[1:]}) "
                    elif compare == "anyof":
                        new += f"set({left}) & set(child{s_[1:]}) "
                    elif compare == "noneof":
                        new += f"not set({left}) & set(child{s_[1:]}) "
                    else:
                        new += f"{left} {compare} child{s_[1:]} "
            elif s.startswith(("!@", "@")):
                s_ = re.sub(r"\.([_0-9a-zA-Z\u4e00-\u9fa5]+)", r"['\1']", s)
                new += f"not child{s_[2:]} " if s.startswith("!@") else f"child{s_[1:]} "

            return self.normalize(old[len(s):], new)

        raise UnExpectJsonPathError('Ungrammatical JsonPath')

    def start_filtering(self, obj, expr):
        result = []
        expr = self.normalize(expr, '')
        if not expr:
            return result

        for item in obj:
            if not isinstance(item, list):
                continue

            for child in item:
                try:
                    value = eval(expr)
                except NameError:
                    continue

                if value:
                    result.append(child)

        return result

    def controller_parsing(self, obj, expr):
        result = []
        compare = re.match(pattern_controller_type, expr)
        if compare:
            g = compare.group()
            s = g[3:-2]
            res = self.start_filtering(obj, s)
            result.extend(res)
            expr = expr[len(g):]

        return result, expr
    