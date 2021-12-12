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
pattern_filter_type = r'in|nin|subsetof|anyof|noneof|size|empty|[\!\=\>\<\~]+'


def math_avg(L):
    return sum(L) / len(L)


def math_stddev(L):
    a = math_avg(L)
    return sqrt(sum([(i - a) * (i - a) for i in L]) / (len(L) - 1))


func_dict = {'min()': min, 'max()': max, 'avg()': math_avg, 'stddev()': math_stddev, 'length()': len, 'sum()': sum}


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
        except KeyError:
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

    def controller_parsing(self, obj, expr):

        def parse_value(value):
            if value.startswith('@'):
                return self.controller_walk(obj, x[1:])
            elif value.startswith('$'):
                res = []
                self.start_parsing(self.obj, value, res)
                return res
            else:
                return value

        result = []
        compare = re.match(pattern_controller_type, expr)
        if compare:
            g = compare.group()
            s = g[3:-2]
            spt = re.split(pattern_filter_type, s)
            if spt and len(spt) == 2:
                left, right = spt
                left = left.strip()
                right = right.strip()
                c = re.search(pattern_filter_type, s).group()
                c = c.replace('nin', 'not in').replace('anyof', '&')
                if left.startswith('@'):
                    right = parse_value(right)
                    right = '0' if c == 'empty' else right
                    c = c.replace('subsetof', '<')
                    if isinstance(right, list) and len(right) == 1:
                        right = right[0]
                        right = eval(right)
                        res = self.controller_walk(obj, left[1:], c, right)
                        result.extend(res)
                    elif isinstance(right, str):
                        right = eval(right)
                        res = self.controller_walk(obj, left[1:], c, right)
                        result.extend(res)
                elif right.startswith('@'):
                    left = parse_value(left)
                    left = '0' if c == 'empty' else left
                    c = c.replace('<', '>').replace('>', '<').replace('subsetof', '>')
                    if isinstance(left, list) and len(left) == 1:
                        left = left[0]
                        left = eval(left)
                        res = self.controller_walk(obj, right[1:], c, left)
                        result.extend(res)
                    elif isinstance(left, str):
                        left = eval(left)
                        res = self.controller_walk(obj, right[1:], c, left)
                        result.extend(res)
            else:
                x = spt[0]
                res = parse_value(x)
                result.extend(res)

            expr = expr[len(g):]
        return result, expr

    def controller_walk(self, obj, expr, compare=None, value=None):
        result = []
        if expr:
            dit = re.match(pattern_dict, expr)
            dot = re.match(pattern_dot, expr)
            if dit:
                g = dit.group()
                x = g[2:-2]
                res = self.controller_filter(obj, x, compare, value)
                result.extend(res)
                expr = expr[len(g):]
            elif dot:
                x = expr[1:]
                res = self.controller_filter(obj, x, compare, value)
                result.extend(res)
                expr = expr[len(expr):]

            s = deepcopy(result)
            self.controller_walk(s, expr)

        return result

    def controller_filter(self, obj, x, compare=None, value=None):
        result = []
        for item in obj:
            if not isinstance(item, list):
                continue
            for child in item:
                if not all([isinstance(child, dict),
                            x in child]):
                    continue
                if all([compare is not None,
                        value is not None]):
                    if compare == '=~' and isinstance(child[x], str):
                        if not value.startswith("/"):
                            continue
                        if value.endswith("/i"):
                            if re.match(value[1:-3], child[x], re.I):
                                result.append(child)
                        else:
                            if re.match(value[1:], child[x]):
                                result.append(child)
                    elif compare in ('>', '<', '<=', '>=', '&', 'noneof'):
                        if type(child[x]) != type(value):
                            continue

                        a = child[x]
                        b = value
                        c = '&' if compare == 'noneof' else compare
                        if isinstance(a, list):
                            a = set(a)
                            b = set(b)

                        e = eval("a {} b".format(c))
                        if compare == 'noneof':
                            if isinstance(child[x], list) and not e:
                                result.append(child)
                        elif e:
                            result.append(child)

                    elif compare in ('size', 'empty'):
                        if isinstance(child[x], (list, str)) and len(child[x]) == value:
                            result.append(child)
                    elif eval("child[x] {} value".format(compare)):
                        result.append(child)
                else:
                    result.append(child)

        return result
