
import re
import traceback
from math import sqrt
from copy import deepcopy


pattern_dict = r'\[("|\').+?("|\')\]'
pattern_index = r'\[[0-9]+[, 0-9]*\]'
pattern_split = r'\[((\*)|((-)?[0-9]*:(-)?[0-9]*))\]'
pattern_dot = r'\.\*?'
pattern_double_dot = r'\.\.((\*)|(\[\*\]))?'
pattern_normal_type = r'[\-\_0-9a-zA-Z\u4e00-\u9fa5]+(\(\))?'
pattern_controller_type = r'\[\?\(.+?\)\]'
pattern_filter_type = r'\sin\s|\snin\s|\ssubsetof\s|\sanyof\s|\snoneof\s|\ssize\s|\sempty|\s?[\!\=\>\<\~]+\s?'


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
        except (KeyError, IndexError, ValueError, RecursionError, UnExpectJsonPathError):
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
            elif expr.startswith(".[?"):
                expr = "..[?" + expr[3:]
                obj, expr = self.scan_parsing(obj, expr)
                result.extend(obj)
                self.start_parsing(obj, expr, result)
            elif expr.startswith(".["):
                expr = "..[" + expr[2:]
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
            elif x == '*' or x == '[*]' or value is None:
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
                    elif g == 'length()':
                        f = func_dict[g]
                        result.append(f(item))
                    elif all([
                        all([isinstance(i, (int, float)) for i in item]),
                        g in ('min()', 'max()', 'avg()', 'stddev()', 'sum()')
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
            return value if compare == '=~' else eval(value)

    def normalize(self, value, index=0, replaced_dict=None):   # todo
        replaced_dict = replaced_dict if replaced_dict else {}
        expr = f"(@((\.[_0-9a-zA-Z\u4e00-\u9fa5]+)|(\[(\"|').+?(\"|')\]))+({pattern_filter_type})?((true|false|null|\d+\.?\d*|\/.*?/i|'.*?'|\[.*?\]|$((\.[_0-9a-zA-Z\u4e00-\u9fa5]+)|(\[(\"|').+?(\"|')\]))+))?)|((true|false|null|\d+\.?\d*|\/.*?/i|'.*?'|\[.*?\]|$((\.[_0-9a-zA-Z\u4e00-\u9fa5]+)|(\[(\"|').+?(\"|')\]))+)({pattern_filter_type})@((\.[_0-9a-zA-Z\u4e00-\u9fa5]+)|(\[(\"|').+?(\"|')\])))"
        m = re.search(expr, value)
        if m:
            span = m.span()
            s = m.group()
            new_s = ''
            spt = re.split(pattern_filter_type, s)
            if spt and len(spt) == 2:
                left, right = spt
                compare = s[len(left):-len(right) if len(right) else len(s)].strip()        # todo
                compare = compare.replace('nin', 'not in')
                if left.startswith('@'):
                    if right in ('true', 'false', 'null'):
                        right = right.replace('true', 'True').replace('false', 'False').replace('null', 'None')
                    s_ = re.sub(r"\.([_0-9a-zA-Z\u4e00-\u9fa5]+)", r"['\1']", left)
                    if compare in ('empty', 'size'):
                        right = 0 if compare == 'empty' else right
                        new_s = f"len(child{s_[1:]}) == {right}"
                    elif compare == "subsetof":
                        new_s = f"(set(child{s_[1:]}).issubset(set({right})) if isinstance(child{s_[1:]}, list) else False)"
                    elif compare == "anyof":
                        new_s = f"(set(child{s_[1:]}) & set({right}) if isinstance(child{s_[1:]}, list) else False)"
                    elif compare == "noneof":
                        new_s = f"(not set(child{s_[1:]}) & set({right}) if isinstance(child{s_[1:]}, list) else True)"
                    elif compare == "=~":
                        if not isinstance(right, str) or not right.startswith("/") or not right.endswith("/i"):
                            raise UnExpectJsonPathError('Ungrammatical JsonPath')
                        new_s = f"re.match('{right[1:-3]}', child{s_[1:]}, re.I)"
                    else:
                        new_s = f"child{s_[1:]} {compare} {right}"
                elif right.startswith('@'):
                    if left in ('true', 'false', 'null'):
                        left = left.replace('true', 'True').replace('false', 'False').replace('null', 'None')
                    s_ = re.sub(r"\.([_0-9a-zA-Z\u4e00-\u9fa5]+)", r"['\1']", right)
                    if compare in ('empty', 'size', '=~'):
                        raise Exception('不符合语法的JsonPath')
                    elif compare == "subsetof":
                        new_s = f"set({left}) < set(child{s_[1:]})"
                    elif compare == "anyof":
                        new_s = f"set({left}) & set(child{s_[1:]})"
                    elif compare == "noneof":
                        new_s = f"not set({left}) & set(child{s_[1:]})"
                    else:
                        new_s = f"{left} {compare} child{s_[1:]}"
            elif s.startswith(("!@", "@")):
                s_ = re.sub(r"\.([_0-9a-zA-Z\u4e00-\u9fa5]+)", r"['\1']", s)
                new_s = f"not child{s_[2:]}" if s.startswith("!@") else f"child{s_[1:]}"

            index += 1
            k = f"param_{index}"
            v = new_s if new_s else s
            value = value[:span[0]] + '{' + k +'}' + value[span[1]:]
            replaced_dict[k] = v
            return self.normalize(value, index, replaced_dict)
        else:
            value = value.replace("&&", "and").replace("||", "or")
            value = value.format(**replaced_dict) if replaced_dict else value
            return value

    def start_filtering(self, obj, expr):
        result = []
        expr = self.normalize(expr, index=0, replaced_dict=None)
        if not expr:
            return result

        if len(obj) == 1 and isinstance(obj[0], list):
            for child in obj[0]:
                try:
                    value = eval(expr)
                except Exception:
                    continue
                if value:
                    result.append(child)
        else:
            for item in obj:
                if isinstance(item, dict):
                    child = deepcopy(item)
                    try:
                        value = eval(expr)
                    except Exception:
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
