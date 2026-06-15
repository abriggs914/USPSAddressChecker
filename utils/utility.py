import math
import ctypes
from typing import Literal, Any

import pandas as pd
from locale import currency, setlocale, LC_ALL
from math import e, ceil, sin, cos, radians
from random import random, choice, sample
from operator import itemgetter
from plyer import notification
from decimal import Decimal
from fractions import Fraction
import datetime
import shutil
import sys
import os

from screeninfo import get_monitors

#######################################################################################################################
#######################################################################################################################
#######################################################################################################################

VERSION = \
    """	
    General Utility Functions
    Version..............1.86
    Date...........2026-02-19
    Author(s)....Avery Briggs
    """


def VERSION_DETAILS():
    return VERSION.lower().split("version")[0].strip()


def VERSION_NUMBER():
    return float(".".join(VERSION.lower().split("version")[-1].split("date")[0].split(".")[-2:]).strip())


def VERSION_DATE():
    return datetime.datetime.strptime(VERSION.lower().split("date")[-1].split("author")[0].split(".")[-1].strip(),
                                      "%Y-%m-%dictionary")


def VERSION_AUTHORS():
    return [w.removeprefix(".").strip().title() for w in VERSION.lower().split("author(s)")[-1].split("..") if
            w.strip()]


#######################################################################################################################
#######################################################################################################################
#######################################################################################################################


def func_def():
    pass


class Foo:
    def __init__(self):
        pass

    def f1(self):
        pass

    def f2(self, f):
        pass


FOO_OBJ = Foo()


def isfunc(f):
    return isinstance(f, type(func_def))


def isclassmethod(m):
    return isinstance(m, type(FOO_OBJ.f1))


def lenstr(x):
    return len(str(x))


def minmax(a, b=None):
    if b is None:
        if isinstance(a, list) or isinstance(a, tuple):
            p, q = None, None
            for i, val in enumerate(a):
                if p is None or q is None:
                    p = val
                    q = val
                else:
                    if val < p:
                        p = val
                    if val > q:
                        q = val
            return p, q
        else:
            raise ValueError(f"Parameter 'a' must be a list or tuple when parameter 'b' is None. Got '{a}'")

    if a <= b:
        return a, b
    return b, a


def maxmin(a, b=None):
    if b is None:
        if isinstance(a, list) or isinstance(a, tuple):
            p, q = None, None
            for i, val in enumerate(a):
                if p is None or q is None:
                    p = val
                    q = val
                else:
                    if val < p:
                        p = val
                    if val > q:
                        q = val
            return q, p
        else:
            raise ValueError(f"Parameter 'a' must be a list or tuple when parameter 'b' is None. Got '{a}'")

    if a < b:
        return b, a
    return a, b


def avg(lst):
    try:
        if isinstance(lst, map):
            return avg(list(lst))
        return sum(lst) / max(1, len(lst))
    except TypeError:
        # print(f"TypeError1")
        res = 0
        c = 0
        i, el, vel = None, None, None
        try:
            for i, el in enumerate(lst):
                vel = float(el)
                if math.isnan(vel) or math.isinf(vel):
                    continue
                c += 1
                res += float(vel)
            return res / (1 if c == 0 else c)
        except TypeError as te:
            print(f"TypeError2\n{te=}\n{res=}\n{c=}\n{i=}\n{el=}\n{vel=}")
            return None


def median(lst):
    if not isinstance(lst, list) and not isinstance(lst, str):
        raise TypeError("Cannot find median of \"{}\" of type: \"{}\".".format(lst, type(lst)))
    if not lst:
        return None

    lt = lst.copy()
    lt.sort()
    l = len(lt)
    if l == 1:
        return lt
    else:
        h = l // 2
        o = (l % 2) == 1
        f = [] if o else lt[h - 1: h]
        return f + lt[h: h + 1]


def mode(lst):
    if not isinstance(lst, list) and not isinstance(lst, str):
        raise TypeError("Cannot find game_mode of \"{}\" of type: \"{}\".".format(lst, type(lst)))
    d = {}
    mv = float("-inf")
    for el in lst:
        if el in d:
            v = d[el] + 1
        else:
            v = 1

        d[el] = v
        if v > mv:
            mv = v

    print("mv", mv, "dictionary", d)
    return [k for k, v in d.items() if v == mv]


def pad_centre(text, l, pad_str=" "):
    """Just use str.center"""
    if l > 0:
        h = (l - len(text)) // 2
        odd = (((2 * h) + len(text)) == l)
        text = text.rjust(h + len(text), pad_str)
        h += 1 if not odd else 0
        text = text.ljust(h + len(text), pad_str)
        return text
    else:
        return ""


def text_size(txt):
    spl = txt.split("\n")
    return len(spl), max([len(line) for line in spl])


# Function returns a formatted string containing the contents of a dict object.
# Special lines and line count for values that are lists.
# Supports dictionaries with special value types.
# Lists are printed line by line, but the counting index is constant for all elements. - Useful for ties.
# Dicts are represented by a table which will dynamically generate a header and appropriately format cell values.
# Strings, floats, ints, bools are simply converted to their string representations.
# dictionary					-	dict object.
# n					-	Name of the dict, printed above the contents.
# number			-	Decide whether to number the content lines.
# l					-	Minimum number of chars in the content line.
# 						Spaces between keys and values are populated by marker.
# sep				-	Additional separation between keys and values.
# marker			-	Char that separates the key and value of a content line.
# sort_header		-	Will alphabetically sort the header line if any value is a
#						dictionary. Only one level of nesting supported.
# min_encapsulation	-	If a table is necessary because of a value that is a
#						dictionary, then opt to keep all column widths as small as
#						possible. This will most likely produce varying widths.
# table_title		-	If a table is created, then display the title in the first
#						column directly above the row names.
def dict_print(d, n="Untitled", number=False, l=15, sep=5, marker=".", sort_header=False, min_encapsulation=True,
               table_title="", TAB="    ", SEPARATOR="  -  ", TABLE_DIVIDER="|"):
    if not d or not n or type(d) != dict:
        return "None"
    m = "\n{}--  ".format(TAB[:len(TAB) // 2]) + str(n).title() + "  --\n\n"
    fill = 0

    # max_key = max([len(str(k)) + ((2 * len(k) + 2 + len(k) - 1) if type(k) == (list or tuple) else 0) for k in dictionary.keys()])
    # max_val = max([max([len(str(v_elem)) for v_elem in v]) if type(v) == (list or tuple) else len(str(v)) if type(v) != dict else 0 for v in dictionary.values()])
    # fill += sum([len(v) for v in dictionary.values() if type(v) == (list or tuple)])
    # l = max(l, (max_key + max_val)) + sep
    # has_dict = [(k, v) for k, v in dictionary.items() if type(v) == dict]
    # has_list = any([1 if type(v) in [list, tuple] else 0 for v in dictionary.values()])

    max_key = float("-inf")
    max_val = float("-inf")
    fill = float("-inf")
    l = float("-inf")
    has_dict = False
    has_list = False

    for k, v in d.items():
        max_key = max((len(str(k)) + ((2 * len(k) + 2 + len(k) - 1) if type(k) == (list or tuple) else 0)), max_key)
        max_val = max((max([len(str(v_elem)) for v_elem in v] if v else [0]) if (
                (type(v) == list) or (type(v) == tuple)) else len(
            str(v)) if type(v) != dict else 0), max_val)

    l = max(len(table_title), max(l, (max_key + max_val))) + sep
    has_dict = [(k, v) for k, v in d.items() if type(v) == dict or (type(v) == list and v and type(v[0]) == dict)]
    has_list = any([1 if type(v) in [list, tuple] else 0 for v in d.values()])

    header = []
    max_cell = 0
    max_cell_widths = []

    # print("has_dict: {hd}".format(hd=has_dict))
    if has_list:
        number = True
    for k1, v in has_dict:
        for k2 in v:
            key = str(k2)
            # print("key: {k}".format(k=key))
            if key not in header:
                if type(v) == dict:
                    # print("\t\tNew key: {k}".format(k=key))
                    header.append(key)
                    max_cell = max(max_cell, max(len(key), max([lenstr(value) for value in v.values()])))
                # print("max_cell: {mc}".format(mc=max_cell))
                elif type(k2) == dict:
                    strkeys = list(map(str, list(k2.keys())))
                    strvals = list(map(str, list(k2.values())))
                    header += [strkey for strkey in strkeys if strkey not in header]
                    max_cell = max(max_cell, max(list(map(len, strkeys))), max(list(map(len, strvals))))
                else:
                    for lst in v:
                        a = max(list(map(lenstr, list(map(str, lst.keys())))))
                        b = max(list(map(lenstr, list(map(str, lst.values())))))
                        # print("a: {a}, b: {b}, values: {v}".format(a=a, b=b, v=lst.values()))
                        max_cell = max(max_cell, max(a, b))

    max_cell += 2

    # print("max_cell: {mc}".format(mc=max_cell))
    if sort_header:
        header.sort(key=lambda x: x.rjust(max_cell))

    if min_encapsulation:
        for h in header:
            max_col_width = len(h) + 2
            # print("h: {h}, type(h): {th}".format(h=h, th=type(h)))
            for k, d_val in has_dict:
                d_val = {str(d_val_k): str(d_val_v) for d_val_k, d_val_v in d_val.items()} if type(
                    d_val) == dict else d_val
                # print("d_val: {dv},\thidv: {hidv},\tetdvlist: {etdvl}".format(dv=d_val, hidv=(h in d_val), etdvl=(type(d_val) == list)))
                # print("k: {k}\nt(k): {tk}\ndictionary: {dictionary}\nt(dictionary): {td}".format(k=k, tk=type(k), dictionary=d_val, td=type(d_val)))
                if h in d_val:
                    max_col_width = max(max_col_width, lenstr(d_val[h]) + 2)
                elif type(d_val) == list:
                    max_col_width = max(max_col_width, max([max(
                        max(list(map(lenstr, [ek for ek in elem.keys() if ek == h]))),
                        max(list(map(lenstr, [ev for ek, ev in elem.items() if ek == h]))) + 2) for elem in d_val]))
            max_cell_widths.append(max_col_width)

    # print("max_cell_widths: {mcw}".format(mcw=max_cell_widths))
    table_header = TABLE_DIVIDER + TABLE_DIVIDER.join(
        map(lambda x: pad_centre(str(x), max_cell), header)) + TABLE_DIVIDER
    empty_line = TABLE_DIVIDER + TABLE_DIVIDER.join(
        [pad_centre(" ", max_cell) for i in range(len(header))]) + TABLE_DIVIDER

    if min_encapsulation:
        table_header = TABLE_DIVIDER + TABLE_DIVIDER.join(
            [pad_centre(str(h), max_cell_widths[i]) for i, h in enumerate(header)]) + TABLE_DIVIDER
        empty_line = TABLE_DIVIDER + TABLE_DIVIDER.join(
            [pad_centre(" ", max_cell_widths[i]) for i in range(len(header))]) + TABLE_DIVIDER
    else:
        max_cell_widths = [max_cell for i in range(len(header))]

    # print("Header: {h}\nTable Header: {th}".format(h=header, th=table_header))
    fill = "".join([" " for i in range(len(str(fill + len(d))))])
    table_width = l + len(fill) + len(SEPARATOR) + len(TAB) + len(table_header) - (4 * len(TABLE_DIVIDER))
    table_tab = "".join([marker for i in range(len(TAB))])
    if has_dict:
        table_header_title = pad_centre(table_title, l + len(SEPARATOR) - 1)
        m += TAB
        m += "" if not number else fill + SEPARATOR
        m += table_header_title + table_header.rjust(
            table_width - len(table_header_title) - len(fill) - len(SEPARATOR)) + "\n"
    i = 0
    # print("FINAL L: {l}\nFill: {n}<{f}>".format(l=l, n=len(fill), f=fill))
    for k, v in d.items():
        if type(v) not in [list, tuple]:
            v = [v]
        for j, v_elem in enumerate(v):
            ml = str(k).strip()
            orig_ml = ml
            num = str(i + 1)
            if number:
                ml = fill + SEPARATOR + ml
                if j == 0:
                    ml = num.ljust(len(fill)) + ml[len(fill):]
            v_val = v_elem
            if has_dict and type(v_elem) == dict:
                v_val = ""
            ml += str(v_val).rjust(l - len(orig_ml), marker)
            if has_dict:
                ml += table_tab
                if type(v_elem) == dict:
                    keys = {str(k).strip(): v for k, v in v_elem.items()}
                    vals = [keys[key] if key in keys else "" for key in header]
                    ml += TABLE_DIVIDER + TABLE_DIVIDER.join(
                        pad_centre(str(cell), max_cell_widths[i]) for i, cell in enumerate(vals)) + TABLE_DIVIDER
                else:
                    ml += empty_line
            ml += "\n"
            m += TAB + ml
            i += 1
    return m


def money(v, int_only=False):
    # return "$ %.2f" % v
    setlocale(LC_ALL, "")
    m = currency(v, grouping=True)
    i = m.index("$") + 1
    if int_only:
        return (m[:i] + " " + m[i:]).split(".")[0]
    return m[:i] + " " + m[i:]


def money_value(m):
    return float("".join(m.removeprefix("$").strip().split(",")))


def is_money(value):
    if isnumber(value):
        value = f"$ {value}"
    if isinstance(value, str):
        value = value.replace(',', '').replace(' ', '').replace('.', '', 1).replace('-', '', 1)
        return value.startswith('$') and value.count('$') == 1 and value[1:].isdigit()
    return False


def percent(v):
    return ("%.2f" % (v * 100)) + " %"


def compute_min_edit_distance(a, b, show=False):
    len_a = len(a)
    len_b = len(b)
    x = max(len_a, len_b)
    s = b if x == len_a else a
    m, instructions = min_edit_distance(a, b, show_table=show)
    # print(instructions)
    return m


def min_edit_distance(a, b, show_table=False):
    a = a.upper()
    b = b.upper()
    n = len(a) + 2
    m = len(b) + 2
    table = [[0 for j in range(n)] for i in range(m)]
    for i in range(2, max(n, m)):
        if i < n:
            table[0][i] = a[i - 2]
            table[1][i] = i - 1
        if i < m:
            table[i][0] = b[i - 2]
            table[i][1] = i - 1

    for i in range(2, m):
        for j in range(2, n):
            x = table[i][j - 1]
            y = table[i - 1][j - 1]
            z = table[i - 1][j]
            mini = min(x, min(y, z))
            u = table[0][j]
            v = table[i][0]
            if u == v:
                table[i][j] = table[i - 1][j - 1]
            else:
                # System.out.println("x: " + x + ", y: " + y + ", z: " + z + ", min(x, min(y, z): " + mini);
                table[i][j] = mini + 1

    if show_table:
        show(table)
        print("Minimum edit Distance to convert \"" + a + "\" to \"" + b + "\": " + str(table[m - 1][n - 1]))
    return table[m - 1][n - 1], table


def show(arr):
    res = "{"
    for i in range(len(arr)):
        res += "{"
        if i > 0:
            res += " "
        for j in range(len(arr[i])):
            if j < len(arr[i]) - 1:
                if i == 0 or j == 0:
                    res += str(arr[i][j]) + ", "
                else:
                    res += str(arr[i][j]) + ", "
            else:
                if i == 0 or j == 0:
                    res += str(arr[i][j])
                else:
                    res += str(arr[i][j])
        if i < len(arr) - 1:
            res += "},\n"
        else:
            res += "}"
    res += "}\n"
    print(res)


def intersection(a, b):
    res = []
    l = a if len(a) >= len(b) else b
    m = b if len(a) >= len(b) else a
    for i in l:
        if i in m:
            res.append(i)
    return res


def disjoint(a, b):
    overlap = intersection(a, b)
    res = []
    for el in a + b:
        if el not in overlap:
            res.append(el)
    return res


def isfloat(value):
    try:
        float(value)
        return True
    except ValueError:
        return False


def isnumber(value):
    # if isinstance(value, int) or isinstance(value, float):
    #     return True
    # if isinstance(value, str):
    #     if value.count("-") < 2 and value.count(".") < 2:
    #         if value.replace("-", "").replace(".", "").isnumeric():
    #             return True
    # return False
    if isinstance(value, (int, float, complex, Decimal, Fraction)) or pd.api.types.is_numeric_dtype(value):
        return True
    xs = str(value)
    if xs.count(".") < 2 and xs.count("-") < 2:
        return xs.replace(".", "").removeprefix("-").isnumeric()
    return False


def pyth(a=None, b=None, c=None):
    if all([a is None, b is None, c is None]):
        return None
    if c is None:
        if a is not None and b is not None:
            return {"a": a, "b": b, "c": (a ** 2 + b ** 2) ** 0.5}
    elif a is None:
        if b is not None and c is not None:
            return {"a": (c ** 2 - b ** 2) ** 0.5, "b": b, "c": c}
    elif b is None:
        if a is not None and c is not None:
            return {"a": a, "b": (c ** 2 - a ** 2) ** 0.5, "c": c}
    return {"a": a, "b": b, "c": c}


def sigmoid(x):
    return 1 / (1 + (e ** -x))


def random_in_range(a, b):
    return ((max(a, b) - min(a, b)) * random()) + min(a, b)


def max_idx(lst):
    max_val = None, float("-inf")
    for i, el in enumerate(lst):
        if el > max_val[1]:
            max_val = i, el
    return max_val


def min_idx(lst):
    min_val = None, float("inf")
    for i, el in enumerate(lst):
        if el < min_val:
            min_val = i, el
    return min_val


# Usage:
# (val, weight) where weight is a float or integer.
# float weights must sum to 1 or less, indicatiing a percentage of 100.
# A whole integer will be considered as a ratio value.
# l1 = [(1, 0.7), (2, 0.3)]  # '1' 70% of the time, '2' 30% of the time
# l2 = [(0, 0.05), (1, 0.05), (2, 0.05), (3, 0.1), (4, 0.2), (5, 0.05), (6, 10), (7, 2), (8, 3)]
# 5% of the time: '0', '1', '2', '5', '3' 10% of the time, '4' 20% of the time, and 10 individual counts of 6, 2 and 7 and 3 counts of 8.
# l3 = [("Avery", 5), ("Jordan", 15), ("Briggs", 2)]
# List of 5 counts of 'Avery', 15 counts of 'Jordan', and 2 counts of 'Briggs'
# weighted_choice(l1)
# Returns a radnom choice from a generated weighted list.
def weighted_choice(weighted_lst):
    item_scalar = 10
    lst_len = 1000
    res = []
    whole = []
    fract = []
    fract_sum = 0
    sum_count = 0
    for el in weighted_lst:
        if isinstance(el, list) or isinstance(el, tuple):
            if len(el) == 2:
                val, weight = el
                if str(weight).startswith("0."):
                    fract.append(el)
                    fract_sum += weight
                    sum_count += weight * lst_len
                else:
                    whole.append(el)
    # print("Whole:", whole)
    # print("Fract:", fract)
    if fract_sum > 1:
        print("Fract:", fract)
        raise ValueError("Fractional weights sum to 1 or less.")

    remaining = lst_len - sum_count
    remaining = remaining if remaining != 0 else 1
    sum_whole = sum([weight for val, weight in whole])
    sum_whole = sum_whole if sum_whole != 0 else 1
    p = sum_whole / remaining

    for val, weight in fract:
        # print("item_scalar:", item_scalar, "p:", p, "weight:", weight, "lst_len:", lst_len)
        s = ceil(item_scalar * p * weight * lst_len)
        # print("\ts:", s)
        res += [val for i in range(s)]

    for val, weight in whole:
        # print("{} x {}".format(weight, val))
        res += [val for i in range(ceil(weight))]

    # print("\tres", res)
    if res:
        # print("Choice from:\n\t{}".format(res))
        return choice(res)
    if isinstance(weighted_lst, list) or isinstance(weighted_lst, tuple):
        # print("Choice from:\n\t{}".format(weighted_lst))
        return choice(weighted_lst)
    return None


# TODO - Broken test:
#	weighted_choice([(1, 9), 2])


def lbs_kg(lbs):
    """
	lbs_kg(args) -> int() or float()
	Convert N pounds to Kilograms.
	1 Lbs = 0.453592 Kg
	:param lbs: int or float value in pounds.
	:return: float value in kilograms.
	"""
    if not isinstance(lbs, int) or isinstance(lbs, float):
        raise ValueError("Cannot convert \"{}\" of type: \"{}\" to kilograms.".format(lbs, type(lbs)))
    return 0.453592 * lbs


def kg_lbs(kg):
    """
	kg_lbs(args) -> int() or float()
	Convert N Kilograms to pounds.
	1 Lbs = 0.453592 Kg
	:param kg: int or float value in kilograms.
	:return: float value in pounds.
	"""
    if not isinstance(kg, int) or isinstance(kg, float):
        raise ValueError("Cannot convert \"{}\" of type: \"{}\" to pounds.".format(kg, type(kg)))
    if kg == 0:
        return 0.0
    return 1 / lbs_kg(kg)


def miles_km(miles):
    """
	miles_km(args) -> int() or float()
	Convert N Miles to Kilometers.
	1 Mi = 1.60934 Km
	:param miles: int or float value in miles.
	:return: float value in kilometers.
	"""
    if not isinstance(miles, int) or isinstance(miles, float):
        raise ValueError("Cannot convert \"{}\" of type: \"{}\" to miles.".format(miles, type(miles)))
    return 1.60934 * miles


def km_miles(km):
    """
	km_miles(args) -> int() or float()
	Convert N Kilometers to Miles.
	1 Mi = 1.60934 Km.
	:param km: int or float value in kilometers.
	:return: float value in miles.
	"""
    if not isinstance(km, int) or isinstance(km, float):
        raise ValueError("Cannot convert \"{}\" of type: \"{}\" to kilometers.".format(km, type(km)))
    if km == 0:
        return 0.0
    return 1 / miles_km(km)


def flatten(lst):
    """
	flatten(args) -> list()
	Flatten a multi-dimensional list into a single dimension.
	Non-list objects are returned in a list.
	:param lst: list object with one or more dimensions.
	:return: list object with one dimension.
	"""
    if not isinstance(lst, list):
        return [lst]
    if not lst:
        return lst
    return [*flatten(lst[0]), *flatten(lst[1:])]


def clamp(s, v, l):
    """Clamp a number between small and large values."""
    return max(s, min(v, l))


def rotate_on_origin(px, py, theta):
    """Rotate a 2D point about the origin, a given amount of degrees. Counterclockwise"""
    t = radians(theta)
    x = (px * cos(t)) - (py * sin(t))
    y = (px * sin(t)) + (py * cos(t))
    return x, y


def rotate_point(cx, cy, px, py, theta):
    """Rotate a 2D point around any central point, a given amount of degrees. Counterclockwise"""
    xd = 0 - cx
    yd = 0 - cy
    rx, ry = rotate_on_origin(px + xd, py + yd, theta)
    return rx - xd, ry - yd


def bar(a, b, c=10):
    """String representation of a progress bar."""
    if not isinstance(c, int) or c < 1:
        c = 10
    return "{} |".format(percent(a / b)) + "".join(["#" if i < int((c * a) / b) else " " for i in range(c)]) + "|"


def lstindex(lst, target):
    """Iterate a list and return the index of a target value. Avoids IndexError, but iterates the whole list."""
    if lenstr(target) == 1:
        for i, val in enumerate(lst):
            if val == target:
                return i

    if (not hasattr(target, "__iter__")) or isinstance(target, str):
        target = [target]

    for i, val in enumerate(lst):
        for j, tar in enumerate(target):
            if tar != lst[i + j]:
                break
            if j == len(target) - 1:
                return i

    return -1


def cos_x(degrees, amplitude=1, period=1, phase_shift=0, vertical_shift=0):
    return (amplitude * (cos(period * (degrees + phase_shift)))) + vertical_shift


def sin_x(degrees, amplitude=1, period=1, phase_shift=0, vertical_shift=0):
    return (amplitude * (sin(period * (degrees + phase_shift)))) + vertical_shift


def get_terminal_columns():
    return shutil.get_terminal_size().columns


def is_imported(module_name):
    return module_name in sys.modules


def distance(start, end):
    return ((start[0] - end[0]) ** 2 + (start[1] - end[1]) ** 2) ** 0.5


def dot_product(a, b):
    return (a[0] * b[0]) + (b[0] * b[1])


def reduce(lst, p, how="left"):
    if not isinstance(how, str):
        how = str(how)
    how = how.lower()
    if how not in ["left", "center", "right", "distributed"]:
        how = "distributed"

    l = len(lst)
    n_items = round(l * p)
    if n_items <= 0:
        return []

    if how == "left":
        return lst[:n_items]
    elif how == "center":
        a = (l - n_items) // 2
        b = (l + n_items) // 2
        if l % 2 == 1:
            b += 1
        return lst[a:b]
    elif how == "right":
        return lst[l - n_items:]
    else:
        return lst[0: l: l // n_items]


def spread(lst, desired_len, filler=None, how: Literal["average", "exact"]="average"):
    """Take a list and a desired length, return a list of those elements spread over the desired length.
    Use how='average' to increment by the average increase between the first and last elements.
     WARNING when using how='average' the input list should be sorted first, AND new elements may be created.
     Use how='exact' to ensure that elements are only duplicated. No new elements will be created.
     Use filler to populate non-number lists."""

    assert isinstance(desired_len, int) and desired_len >= 0, f"Error param 'desired_len' must be a non-negative integer."
    assert hasattr(lst, "__iter__"), f"Error param 'lst' must be an iterable."
    assert how in ("average", "exact")

    t_lst = list(lst)
    # t_lst.sort()
    ll = len(t_lst)
    is_num = all([isnumber(v) for v in t_lst])

    # print(f"input= {t_lst}")

    if desired_len == ll:
        return lst
    elif desired_len < ll:
        return reduce(lst, ll, how="distribute")
    else:

        if how == "average":
            # print(f"A")
            ub = t_lst[-1]
            lb = t_lst[0]
            if desired_len == 1:
                return t_lst[ll // 2]
            else:
                s = (ub - lb) / (desired_len - 1)

            i = 0
            x = ((desired_len - 1) - 1)
            result = [lst[0]]
            # print(f"{x=}")
            while i < x:
                if filler is None:
                    if is_num:
                        result.append(lb + ((i + 1) * s))
                    else:
                        result.append(filler)
                else:
                    result.append(filler)

                i += 1

            result.append(lst[-1])
        else:
            # print(f"B")
            mf = desired_len // ll
            o = desired_len - (mf * ll)
            result = []
            if mf > 1:
                # print(f"C")
                for i, val in enumerate(t_lst):
                    for j in range(mf):
                        result.append(val)
            else:
                # print(f"D")
                result = list(t_lst)

            if o < mf:
                # print(f"E")
                m = desired_len // 2
                v = result[m]
                # print(f"{result=}")
                for i in range(mf - o):
                    result.insert(m + i, v)
            else:
                # print(f"F")
                idxs = list(range(len(result)))
                idxs = sample(idxs, k=desired_len - (mf * ll))
                # print(f"{result=}")
                # print(f"{idxs=}")
                for i in idxs:
                    result.insert(i, result[i])

        return result


class Line:
    def __init__(self, x1, y1, x2, y2):
        self.x1 = x1
        self.y1 = y1
        self.x2 = x2
        self.y2 = y2
        self.is_init = False
        self.tupl = None
        self.p1 = None
        self.p2 = None
        self.m = None
        self.b = None
        self.abc = None
        self.init(x1, y1, x2, y2)

    def init(self, x1, y1, x2, y2):
        self.tupl = ((x1, y1), (x2, y2))
        self.p1 = x1, y1
        self.p2 = x2, y2
        div = x2 - x1
        if div != 0:
            self.m = (y2 - y1) / div
        else:
            self.m = "undefined"
        if self.m != "undefined":
            self.b = y1 - (x1 * self.m)
        else:
            self.b = "undefined"
        self.abc = (y2 - y1, x1 - x2, ((y2 - y1) * x1) + ((x1 - x2) * y1))
        self.is_init = True

    def collide_point(self, x, y, is_segment=True):
        if self.m == "undefined" or self.b == "undefined":
            return self.x1 == x and self.x2 == x
        if not is_segment:
            return y == (self.m * x) + self.b
        return y == (self.m * x) + self.b and (self.x1 <= x <= self.x2 or self.x2 <= x <= self.x1) and (
                self.y1 <= y <= self.y2 or self.y2 <= y <= self.y1)

    def collide_line(self, line):
        assert isinstance(line, Line)
        a1, b1, c1 = self.abc
        a2, b2, c2 = line.abc
        det = a1 * b2 - a2 * b1
        if det == 0:
            # Lines are parallel
            return None
        else:
            x = (b2 * c1 - b1 * c2) / det
            y = (a1 * c2 - a2 * c1) / det
            sx1, sy1 = self.p1
            sx2, sy2 = self.p2
            sx1, sx2 = minmax(sx1, sx2)
            sy1, sy2 = minmax(sy1, sy2)
            lx1, ly1 = line.p1
            lx2, ly2 = line.p2
            lx1, lx2 = minmax(lx1, lx2)
            ly1, ly2 = minmax(ly1, ly2)
        #         if self.collide_point(x, y) and line.collide_point(x,
        #                                                            y) and self.x1 <= x <= self.x2 and self.y1 <= y <= self.y2 and line.x1 <= x <= line.x2 and line.y1 <= y <= line.y2:

        if self.collide_point(x, y) and line.collide_point(x,
                                                           y) and sx1 <= x <= sx2 and sy1 <= y <= sy2 and lx1 <= x <= lx2 and ly1 <= y <= ly2:
            return x, y
        else:
            return None

    def __eq__(self, other):
        return isinstance(other, Line) and (all([
            self.x1 == other.x1,
            self.y1 == other.y1,
            self.x2 == other.x2,
            self.y2 == other.y2
        ]) or all([
            self.x1 == other.x2,
            self.y1 == other.y2,
            self.x2 == other.x1,
            self.y2 == other.y1
        ]))

    # comparison object "other" must be a tuple of:
    #   (x, y, none_result) -> None comparisons return none_result
    #   (x, y) -> None comparisons throw TypeErrors
    def __lt__(self, other):
        if isinstance(other, tuple) or isinstance(other, list):
            if len(other) == 2:
                if all([isinstance(x, int) or isinstance(x, float) for x in other]):
                    ox, oy = other
                    return oy < self.y_at_x(ox)
            elif len(other) == 3:
                if all([isinstance(x, int) or isinstance(x, float) for x in other[:2]]):
                    if isinstance(other[2], bool) or (isinstance(other[2], int) and other[2] in [0, 1]):
                        ox, oy, none_result = other
                        v = self.y_at_x(ox)
                        # return (oy < v) if v is not None else bool(none_result)
                        return (oy < v) if v is not None else (ox < self.x_at_y(oy))
        raise TypeError(
            "Cannot compare \"{}\" of type with Line.\nRequires tuple / list: (x, y)".format(other, type(other)))

    # comparison object "other" must be a tuple of:
    #   (x, y, none_result) -> None comparisons return none_result
    #   (x, y) -> None comparisons throw TypeErrors
    def __le__(self, other):
        if isinstance(other, tuple) or isinstance(other, list):
            if len(other) == 2:
                if all([isinstance(x, int) or isinstance(x, float) for x in other]):
                    ox, oy = other
                    return oy <= self.y_at_x(ox)
            elif len(other) == 3:
                if all([isinstance(x, int) or isinstance(x, float) for x in other[:2]]):
                    if isinstance(other[2], bool) or (isinstance(other[2], int) and other[2] in [0, 1]):
                        ox, oy, none_result = other
                        v = self.y_at_x(ox)
                        # return (oy <= v) if v is not None else bool(none_result)
                        return (oy <= v) if v is not None else (ox <= self.x_at_y(oy))
        raise TypeError(
            "Cannot compare \"{}\" of type with Line.\nRequires tuple / list: (x, y)".format(other, type(other)))

    # comparison object "other" must be a tuple of:
    #   (x, y, none_result) -> None comparisons return none_result
    #   (x, y) -> None comparisons throw TypeErrors
    def __gt__(self, other):
        if isinstance(other, tuple) or isinstance(other, list):
            if len(other) == 2:
                if all([isinstance(x, int) or isinstance(x, float) for x in other]):
                    ox, oy = other
                    return oy > self.y_at_x(ox)
            elif len(other) == 3:
                if all([isinstance(x, int) or isinstance(x, float) for x in other[:2]]):
                    if isinstance(other[2], bool) or (isinstance(other[2], int) and other[2] in [0, 1]):
                        ox, oy, none_result = other
                        v = self.y_at_x(ox)
                        # return (oy > v) if v is not None else bool(none_result)
                        return (oy > v) if v is not None else (ox > self.x_at_y(oy))
        raise TypeError(
            "Cannot compare \"{}\" of type with Line.\nRequires tuple / list: (x, y)".format(other, type(other)))

    # comparison object "other" must be a tuple of:
    #   (x, y, none_result) -> None comparisons return none_result
    #   (x, y) -> None comparisons throw TypeErrors
    def __ge__(self, other):
        if isinstance(other, tuple) or isinstance(other, list):
            if len(other) == 2:
                if all([isinstance(x, int) or isinstance(x, float) for x in other]):
                    ox, oy = other
                    return oy >= self.y_at_x(ox)
            elif len(other) == 3:
                if all([isinstance(x, int) or isinstance(x, float) for x in other[:2]]):
                    if isinstance(other[2], bool) or (isinstance(other[2], int) and other[2] in [0, 1]):
                        ox, oy, none_result = other
                        v = self.y_at_x(ox)
                        # return (oy >= v) if v is not None else bool(none_result)
                        return (oy >= v) if v is not None else (ox >= self.x_at_y(oy))
        raise TypeError(
            "Cannot compare \"{}\" of type with Line.\nRequires tuple / list: (x, y)".format(other, type(other)))

    def y_at_x(self, x):
        if self.m == "undefined":
            # return None
            return None
        if self.m == 0:
            return self.y1
        return (self.m * x) + self.b

    def x_at_y(self, y):
        if self.m == "undefined":
            return self.x1
        if self.m == 0:
            return None
        return (y - self.b) / self.m

    def translate(self, x, y):
        self.x1 += x
        self.x2 += x
        self.y1 += y
        self.y2 += y
        self.init(self.x1, self.y1, self.x2, self.y2)

    def translated(self, x, y):
        r = Line(self.x1, self.y1, self.x2, self.y2)
        r.translate(x, y)
        return r

    def __iter__(self):
        lst = [self.p1, self.p2]
        for val in lst:
            yield val

    def __repr__(self):
        if self.m == "undefined":
            return "x = {}".format(self.x1)
        if self.m == 0:
            return "y = {}".format(self.b)
        return "y = {}x + {}".format("%.2f" % self.m, self.b)


class LineSeg(Line):

    def __init__(self, x1, y1, x2, y2):
        super().__init__(x1, y1, x2, y2)
        self.length = distance(self.p1, self.p2)

    def collide_point(self, x, y):
        return super().collide_point(x, y)


# class Rect:
#     def __init__(self, x, y=None, w=None, h=None):
#         self.x = x
#         self.y = y
#         self.width_canvas = w
#         self.height_canvas = h
#         if any([y is None, w is None, h is None]):
#             if is_imported("pygame"):
#                 if isinstance(x, pygame.Rect):
#                     x = x.left
#                     y = x.y
#                     w = x.width_canvas
#                     y = x.height_canvas
#                 else:
#                     raise ValueError("Cannot create a Rect object with <{}>.\nExpected a pygame.Rect object.".format(x))
#             else:
#                 ValueError("Cannot create a rect object with <{}>.\npygame module is not imported.".format(x))
#         self.is_init = False
#         self.tupl = None
#         self.top = None
#         self.left = None
#         self.bottom = None
#         self.right = None
#         self.center = None
#         self.top_left = None
#         self.top_right = None
#         self.bottom_left = None
#         self.bottom_right = None
#         self.top_line = None
#         self.left_line = None
#         self.right_line = None
#         self.bottom_line = None
#         self.center_top = None
#         self.center_left = None
#         self.center_right = None
#         self.center_bottom = None
#         self.area = None
#         self.perimetre = None
#         self.init(x, y, w, h)
#
#     def init(self, x, y, w, h):
#         self.x = x
#         self.y = y
#         self.width_canvas = w
#         self.height_canvas = h
#         self.tupl = (x, y, w, h)
#         self.top = y
#         self.left = x
#         self.bottom = y + h
#         self.right = x + w
#         self.center = x + (w / 2), y + (h / 2)
#         self.top_left = x, y
#         self.top_right = x + w, y
#         self.bottom_left = x, y + h
#         self.bottom_right = x + w, y + h
#         self.center_top = self.center[0], y
#         self.center_left = x, self.center[1]
#         self.center_right = x + w, self.center[1]
#         self.center_bottom = self.center[0], y + h
#         self.area = w * h
#         self.perimetre = 2 * (w + h)
#         self.top_line = Line(*self.top_left, *self.top_right)
#         self.left_line = Line(*self.top_left, *self.bottom_left)
#         self.right_line = Line(*self.top_right, *self.bottom_right)
#         self.bottom_line = Line(*self.bottom_left, *self.bottom_right)
#         self.is_init = True
#
#     def __iter__(self):
#         lst = [self.x, self. y, self.width_canvas, self.height_canvas]
#         for val in lst:
#             yield val
#
#     def collide_rect(self, rect, strictly_inside=True):
#         if strictly_inside:
#             return all([
#                 self.left < rect.left,
#                 self.right > rect.right,
#                 self.top < rect.top,
#                 self.bottom > rect.bottom
#             ])
#         else:
#             return any([
#                 self.collide_point(*rect.top_left),
#                 self.collide_point(*rect.top_right),
#                 self.collide_point(*rect.bottom_left),
#                 self.collide_point(*rect.bottom_right)
#             ])
#
#     def collide_line(self, line):
#         assert isinstance(line, Line)
#         if self.collide_point(*line.p1) or self.collide_point(*line.p1):
#             return True
#         else:
#             top = Line(self.left, self.top, self.right, self.top)
#             bottom = Line(self.left, self.bottom, self.right, self.bottom)
#             left = Line(self.left, self.top, self.left, self.bottom)
#             right = Line(self.right, self.top, self.right, self.bottom)
#             return any([
#                 line.collide_line(top),
#                 line.collide_line(bottom),
#                 line.collide_line(left),
#                 line.collide_line(right)
#             ])
#
#     def collide_point(self, x, y):
#         return all([
#             self.x <= x <= self.right,
#             self.y <= y <= self.bottom
#         ])
#
#     def translate(self, x, y):
#         if not self.is_init:
#             self.init(self.x, self.y, self.width_canvas, self.height_canvas)
#         self.x += x
#         self.y += y
#         self.init(self.x, self.y, self.width_canvas, self.height_canvas)
#
#     def translated(self, x, y):
#         r = Rect(self.x, self.y, self.width_canvas, self.height_canvas)
#         r.translate(x, y)
#         return r
#
#     def scale(self, w_factor, h_factor):
#         self.init(self.x, self.y, self.width_canvas * w_factor, self.height_canvas * h_factor)
#
#     def scaled(self, w_factor, h_factor):
#         r = Rect(self.x, self.y, self.width_canvas, self.height_canvas)
#         r.scale(w_factor, h_factor)
#         return r
#
#     def move(self, rect):
#         self.init(rect.x, rect.y, rect.width_canvas, rect.height_canvas)
#
#     def resize(self, rect):
#         self.init(rect.x, rect.y, rect.width_canvas, rect.height_canvas)
#
#     def __repr__(self):
#         return "<rect(" + ", ".join(list(map(str, [self.x, self.y, self.width_canvas, self.height_canvas]))) + ")>"


#            x2,y2              x1,y1 ---- x2,y2
#  x1,y1  /    |                  |          |
#    |       x3,y3              x4,y4 ---- x3,y3
#  x4,y4  /

class Rect2:
    def __init__(self, x, y=None, w=None, h=None, a=0):
        self.x = None
        self.y = None
        self.w = None
        self.h = None
        self.width = None
        self.height = None
        self.angle = None

        self.x1, self.y1 = None, None
        self.x2, self.y2 = None, None
        self.x3, self.y3 = None, None
        self.x4, self.y4 = None, None
        self.p1 = None
        self.p2 = None
        self.p3 = None
        self.p4 = None
        self.l1 = None
        self.l2 = None
        self.l3 = None
        self.l4 = None
        self.a = a % 360
        self.angle = a % 360
        self.tupl = None
        self.max_encapsulating_rect = None
        self.min_encapsulating_rect = None
        self.top = None
        self.left = None
        self.bottom = None
        self.right = None
        self.center = None
        self.top_left = None
        self.top_right = None
        self.bottom_left = None
        self.bottom_right = None
        self.center_top = None
        self.center_left = None
        self.center_right = None
        self.center_bottom = None
        self.area = None
        self.perimeter = None
        self.top_line = None
        self.right_line = None
        self.bottom_line = None
        self.left_line = None

        self.diagonal_p1_p3 = None
        self.diagonal_p3_p1 = None
        self.diagonal_p2_p4 = None
        self.diagonal_p4_p2 = None

        self.init(x, y, w, h, a)

    def init(self, x, y, w, h, a):
        if w < 0:
            raise ValueError("width_canvas value: \"{}\" must not be less than 0.".format(w))
        if h < 0:
            raise ValueError("height_canvas value: \"{}\" must not be less than 0.".format(h))
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.a = a
        self.width = w
        self.height = h
        self.angle = a

        self.x1, self.y1 = x, y
        self.x2, self.y2 = rotate_point(x, y, x + w, y, a)
        self.x3, self.y3 = rotate_point(x, y, x + w, y + h, a)
        self.x4, self.y4 = rotate_point(x, y, x, y + h, a)
        self.p1 = self.x1, self.y1
        self.p2 = self.x2, self.y2
        self.p3 = self.x3, self.y3
        self.p4 = self.x4, self.y4
        self.l1 = Line(self.x1, self.y1, self.x2, self.y2)
        self.l2 = Line(self.x2, self.y2, self.x3, self.y3)
        self.l3 = Line(self.x3, self.y3, self.x4, self.y4)
        self.l4 = Line(self.x4, self.y4, self.x1, self.y1)
        self.top_line = self.l1
        self.right_line = self.l2
        self.bottom_line = self.l3
        self.left_line = self.l4

        # self.tupl = (self.p1, self.p2, self.p3, self.p4)
        self.tupl = (self.x, self.y, self.w, self.h)
        if a == 0:
            self.max_encapsulating_rect = self
            self.min_encapsulating_rect = self
        else:
            xs = [self.x1, self.x2, self.x3, self.x4]
            ys = [self.y1, self.y2, self.y3, self.y4]
            xs.sort()
            ys.sort()
            self.max_encapsulating_rect = Rect2(xs[0], ys[0], xs[3] - xs[0], ys[3] - ys[0], 0)
            self.min_encapsulating_rect = Rect2(xs[1], ys[1], xs[2] - xs[1], ys[2] - ys[1], 0)

        # Using max_encapsulating_rect for calculations
        self.top = self.max_encapsulating_rect.y
        self.left = self.max_encapsulating_rect.x
        self.bottom = self.max_encapsulating_rect.y + self.max_encapsulating_rect.height
        self.right = self.max_encapsulating_rect.x + self.max_encapsulating_rect.width
        self.center = self.left + (self.max_encapsulating_rect.width / 2), self.top + (
                self.max_encapsulating_rect.height / 2)
        self.top_left = self.left, self.top
        self.top_right = self.right, self.top
        self.bottom_left = self.left, self.bottom
        self.bottom_right = self.bottom, self.right
        self.center_top = self.center[0], self.top
        self.center_left = self.left, self.center[1]
        self.center_right = self.right, self.center[1]
        self.center_bottom = self.center[0], self.bottom

        self.diagonal_p1_p3 = Line(*self.p1, *self.p3)
        self.diagonal_p3_p1 = Line(*self.p3, *self.p2)
        self.diagonal_p2_p4 = Line(*self.p2, *self.p4)
        self.diagonal_p4_p2 = Line(*self.p4, *self.p2)

        # Calculations done on the main rect object
        self.area = w * h
        self.perimeter = 2 * (w + h)

    def __iter__(self):
        lst = [self.x, self.y, self.width, self.height, self.angle]
        for val in lst:
            yield val

    def collide_point(self, x, y, strictly_inside=False):
        if not all([
            any([
                isinstance(x, int),
                isinstance(x, float)
            ]),
            any([
                isinstance(y, int),
                isinstance(y, float)
            ])
        ]):
            raise TypeError(
                "Cannot determine if x=\"{}\" of type: \"{}\" y=\"{}\" of type: \"{}\" collides with Rect object. Requires int and / or float objects.".format(
                    x, type(x), y, type(y)))
        if strictly_inside:
            return all([
                (x, y, 1) < self.l1,
                (x, y, 1) > self.l2,
                (x, y, 1) > self.l3,
                (x, y, 1) < self.l4
            ])
        else:
            return all([
                (x, y, 1) <= self.l1,
                (x, y, 1) >= self.l2,
                (x, y, 1) >= self.l3,
                (x, y, 1) <= self.l4
            ])

    def collide_line(self, line, strictly_inside=False):
        if not isinstance(line, Line):
            raise TypeError(
                "Cannot determine if line=\"{}\" of type: \"{}\" collides with Rect object. Requires Line object.".format(
                    line, type(line)))
        if strictly_inside:
            return all([
                self.collide_point(*line.p1),
                self.collide_point(*line.p2)
            ])
        else:
            return any([
                self.collide_point(*line.p1),
                self.collide_point(*line.p2)
            ])

    def collide_rect(self, rect, strictly_inside=False):
        if not isinstance(rect, Rect2):
            raise TypeError(
                "Cannot determine if rect=\"{}\" of type: \"{}\" collides with Rect object. Requires Rect object.".format(
                    rect, type(rect)))
        if strictly_inside:
            return all([
                self.collide_point(*rect.p1),
                self.collide_point(*rect.p2),
                self.collide_point(*rect.p3),
                self.collide_point(*rect.p4)
            ])
        else:
            return any([
                self.collide_point(*rect.p1),
                self.collide_point(*rect.p2),
                self.collide_point(*rect.p3),
                self.collide_point(*rect.p4)
            ])

    def translate(self, x, y):
        self.init(self.x + x, self.y + y, self.width, self.height, self.angle)
        return self

    def translated(self, x, y):
        return Rect2(self.x + x, self.y + y, self.width, self.height, self.angle)

    def scale(self, w, h):
        w = abs(w)
        h = abs(h)
        self.init(self.x, self.y, self.width * w, self.height * h, self.angle)
        return self

    def scaled(self, x, y):
        r = Rect2(*self)
        r.scale(x, y)
        return r

    def rotate(self, a):
        self.init(self.x, self.y, self.width, self.height, self.angle + a)
        return self

    def rotated(self, a):
        r = Rect2(*self)
        r.rotate(a)
        return r

    #     if any([y is None, w is None, h is None]):
    #         if is_imported("pygame"):
    #             if isinstance(x, pygame.Rect):
    #                 x = x.left
    #                 y = x.y
    #                 w = x.width_canvas
    #                 y = x.height_canvas
    #             else:
    #                 raise ValueError("Cannot create a Rect object with <{}>.\nExpected a pygame.Rect object.".format(x))
    #         else:
    #             ValueError("Cannot create a rect object with <{}>.\npygame module is not imported.".format(x))
    #     self.is_init = False
    #     self.tupl = None
    #     self.top = None
    #     self.left = None
    #     self.bottom = None
    #     self.right = None
    #     self.center = None
    #     self.top_left = None
    #     self.top_right = None
    #     self.bottom_left = None
    #     self.bottom_right = None
    #     self.top_line = None
    #     self.left_line = None
    #     self.right_line = None
    #     self.bottom_line = None
    #     self.center_top = None
    #     self.center_left = None
    #     self.center_right = None
    #     self.center_bottom = None
    #     self.area = None
    #     self.perimetre = None
    #     self.init(x, y, w, h)
    #
    # def init(self, x, y, w, h):
    #     self.x = x
    #     self.y = y
    #     self.width_canvas = w
    #     self.height_canvas = h
    #     self.tupl = (x, y, w, h)
    #     self.top = y
    #     self.left = x
    #     self.bottom = y + h
    #     self.right = x + w
    #     self.center = x + (w / 2), y + (h / 2)
    #     self.top_left = x, y
    #     self.top_right = x + w, y
    #     self.bottom_left = x, y + h
    #     self.bottom_right = x + w, y + h
    #     self.center_top = self.center[0], y
    #     self.center_left = x, self.center[1]
    #     self.center_right = x + w, self.center[1]
    #     self.center_bottom = self.center[0], y + h
    #     self.area = w * h
    #     self.perimetre = 2 * (w + h)
    #     self.top_line = Line(*self.top_left, *self.top_right)
    #     self.left_line = Line(*self.top_left, *self.bottom_left)
    #     self.right_line = Line(*self.top_right, *self.bottom_right)
    #     self.bottom_line = Line(*self.bottom_left, *self.bottom_right)
    #     self.is_init = True
    #
    # def __iter__(self):
    #     lst = [self.x, self. y, self.width_canvas, self.height_canvas]
    #     for val in lst:
    #         yield val
    #
    # def collide_rect(self, rect, strictly_inside=True):
    #     if strictly_inside:
    #         return all([
    #             self.left < rect.left,
    #             self.right > rect.right,
    #             self.top < rect.top,
    #             self.bottom > rect.bottom
    #         ])
    #     else:
    #         return any([
    #             self.collide_point(*rect.top_left),
    #             self.collide_point(*rect.top_right),
    #             self.collide_point(*rect.bottom_left),
    #             self.collide_point(*rect.bottom_right)
    #         ])
    #
    # def collide_line(self, line):
    #     assert isinstance(line, Line)
    #     if self.collide_point(*line.p1) or self.collide_point(*line.p1):
    #         return True
    #     else:
    #         top = Line(self.left, self.top, self.right, self.top)
    #         bottom = Line(self.left, self.bottom, self.right, self.bottom)
    #         left = Line(self.left, self.top, self.left, self.bottom)
    #         right = Line(self.right, self.top, self.right, self.bottom)
    #         return any([
    #             line.collide_line(top),
    #             line.collide_line(bottom),
    #             line.collide_line(left),
    #             line.collide_line(right)
    #         ])
    #
    # def collide_point(self, x, y):
    #     return all([
    #         self.x <= x <= self.right,
    #         self.y <= y <= self.bottom
    #     ])
    #
    # def translate(self, x, y):
    #     if not self.is_init:
    #         self.init(self.x, self.y, self.width_canvas, self.height_canvas)
    #     self.x += x
    #     self.y += y
    #     self.init(self.x, self.y, self.width_canvas, self.height_canvas)
    #
    # def translated(self, x, y):
    #     r = Rect(self.x, self.y, self.width_canvas, self.height_canvas)
    #     r.translate(x, y)
    #     return r
    #
    # def scale(self, w_factor, h_factor):
    #     self.init(self.x, self.y, self.width_canvas * w_factor, self.height_canvas * h_factor)
    #
    # def scaled(self, w_factor, h_factor):
    #     r = Rect(self.x, self.y, self.width_canvas, self.height_canvas)
    #     r.scale(w_factor, h_factor)
    #     return r
    #
    # def move(self, rect):
    #     self.init(rect.x, rect.y, rect.width_canvas, rect.height_canvas)
    #
    # def resize(self, rect):
    #     self.init(rect.x, rect.y, rect.width_canvas, rect.height_canvas)

    def sq_rect(self):
        return self.x, self.y, self.w, self.h

    def tkinter_rect(self):
        return Rect2(*self.top_left, *self.bottom_right)

    def __repr__(self):
        # return "<rect(p1:({}), p2:({}), p3:({}), p4:({}))>".format(self.p1, self.p2, self.p3, self.p4)
        x, y, w, h, a = self
        return f"<rect: {x=}, {y=}, {w=}, {h=}, {a=}>"


# Appends a counter '(1)' to a given file path to avoid overwriting.
def next_available_file_name(path):
    counter = 0
    path.replace("\\", "/")
    og_path = path
    while os.path.exists(path):
        counter += 1
        spl = og_path.split(".")
        path = ".".join(spl[:-1]) + " ({}).".format(counter) + spl[-1]
    path.replace("/", "\\")
    return path


def alert_colour(x, n):
    assert isnumber(x), "Parameter \"x\": ({}) needs to be a number".format(x)
    assert isnumber(n), "Parameter \"n\": ({}) needs to be a number".format(n)
    assert x <= n, "Parameter \"x\": ({}) needs to be less than or equal to parameter \"n\": ({})".format(x, n)
    assert 0 < n, "Parameter \"n\": ({}) must be non-zero and positive".format(n)
    t_diff = 255
    x = abs(x / n) * t_diff
    return x, 255 - x, 0


def notify(message, title="", app_icon=None, timeout=5):
    if app_icon is not None:
        notification.notify(
            title=title,
            message=message,
            app_icon=(app_icon),
            timeout=timeout  # seconds
        )
    else:
        notification.notify(
            title=title,
            message=message,
            timeout=timeout  # seconds
        )


def print_by_line(value, do_print=True):
    lines = "[" + "\n".join(list(map(str, list(value)))) + "]"
    if not do_print:
        return lines
    print(lines)


def rect2_to_tkinter(rect):
    """Rect2 (left, top, w, h) -> (left, top, right, bottom)"""
    if (isinstance(rect, tuple) or isinstance(rect, list)) and len(rect) in (4, 5):
        rect = Rect2(*rect)
    assert isinstance(rect, Rect2), f"Error value is not a valid Rect2 object. got: <{type(rect)}, v: <{rect}>>"
    assert rect.a == 0, "This Rect2 object is at a non-zero angle."
    return [rect.x, rect.y, rect.w + rect.x, rect.h + rect.y]


def tkinter_to_rect2(rect):
    """Tlinter (left, top, right, bottom) -> Rect2 (left, top, w, h)"""
    assert isinstance(rect, list) or isinstance(rect,
                                                tuple), f"Error value is not a valid list or tuple representing a tkinter rect., got <{type(rect)}>, v=<{rect}>"
    assert len(rect) == 4, "This list is too long"
    x1, y1, x2, y2 = rect
    return Rect2(x1, y1, x2 - x1, y2 - y1)


def kb_as_percent(kb, gb=2):
    return ("%.3f" % (((100 * kb / (1024 ** 2)) / gb))) + " %"


def calc_bounds(center, width, height=None):
    """Given a center (x, y) and width_canvas and heights, calculate the counding box that keeps these dimensions centered."""
    assert (isinstance(center, list) or isinstance(center, tuple)) and len(center) == 2 and all([isnumber(x) for x in
                                                                                                 center]), f"Error param 'center' must be a tuple or list representing center coordinates (x, y). Got: {center}"
    assert isnumber(width), f"Error param 'width_canvas' must be a number. Got: {width}"
    if height is not None:
        assert isnumber(height), f"Error param 'height_canvas' if not omitted, must be a number. Got: {height}"
    w = width / 2
    h = w if height is None else (height / 2)
    return (
        center[0] - w,
        center[1] - h,
        center[0] + w,
        center[1] + h
    )


def left_join(a_, b_):
    assert isinstance(a_, set), "Error, param 'a_' must be a set."
    assert isinstance(b_, set), "Error, param 'a_' must be a set."
    return a_.symmetric_difference(b_).union(a_).symmetric_difference(b_).union(a_)


NATO_phonetic_alphabet = {
    "a": "Alpha",
    "b": "Bravo",
    "c": "Charlie",
    "dictionary": "Delta",
    "e": "Echo",
    "f": "Foxtrot",
    "g": "Golf",
    "h": "Hotel",
    "i": "India",
    "j": "Juliett",
    "k": "Kilo",
    "l": "Lima",
    "m": "Mike",
    "n": "November",
    "o": "Oscar",
    "p": "Papa",
    "q": "Quebec",
    "r": "Romeo",
    "s": "Sierra",
    "t": "Tango",
    "u": "Uniform",
    "v": "Victor",
    "w": "Whiskey",
    "x": "Xray",
    "y": "Yankee",
    "z": "Zulu",
}


def translate_NATO_phonetic_alphabet(phrase, from_english=True, preserve_spaces=True):
    # print(f"{from_english=}, {preserve_spaces=}")
    result = ""
    if phrase:
        if from_english:
            for i, letter in enumerate(phrase):
                if letter.lower() in NATO_phonetic_alphabet:
                    result += NATO_phonetic_alphabet[letter.lower()]
                elif letter != " ":
                    # if result[-2:] != "  ":
                    #     result = result[:len(result) - 1]
                    result += letter
                elif preserve_spaces:
                    result += letter
                else:
                    result = result[:len(result) - 1]
                    # result += letter if letter != " " else ""
                result += " "
        else:
            reverse = {v: k for k, v in NATO_phonetic_alphabet.items()}
            result = phrase
            for k, v in reverse.items():
                result = result.replace(k, v)

            # print(f"{result=}")
            result = result.replace("   ", "&$&").replace(" ", "").replace("&$&", "   ")
            if not preserve_spaces:
                result = result.replace("   ", " ")

    return result.strip()


def grid_cells(
        t_width: int | float | str,
        n_cols: int | str,
        t_height: int | float | str = None,
        n_rows: int | str = None,
        x_pad: int | float | str = 0,
        y_pad: int | float | str = 0,
        x_0: int | float = 0,
        y_0: int | float = 0,
        r_type: list | dict = list,
        r_int: bool = False
) -> list | dict:
    """Calculate grid cell dimensions given W, H, n_rows, n_cols, x and y padding, x and y offset. Choose to return list or dictionary using r_type."""
    assert isnumber(t_width), f"Error param 't_width' needs to be a number. Got {t_width=}"
    assert isnumber(n_cols), f"Error param 'n_cols' needs to be a number. Got {n_cols=}"
    assert isnumber(x_pad), f"Error param 'x_pad' needs to be a number. Got {x_pad=}"
    assert isnumber(x_0), f"Error, param 'x_0' needs to be a number to offset the x position. Got {x_0}"
    assert isnumber(y_0), f"Error, param 'y_0' needs to be a number to offset the y position. Got {y_0}"
    t_width = float(t_width)
    n_cols = int(n_cols)
    x_pad = float(x_pad)
    x_0 = float(x_0)
    y_0 = float(y_0)
    assert t_width > 0, f"Error, this grid must have at least 1 pixel of space. Got {t_width=}"
    assert n_cols > 0, f"Error, this grid must have at least 1 column. Got {n_cols=}"
    assert x_pad > -1, f"Error, x padding cannot be negative. Got {x_pad=}"
    t_height = float(t_width if t_height is None else t_height)
    n_rows = int(n_cols if n_rows is None else n_rows)
    y_pad = float(x_pad if y_pad is None else y_pad)
    assert t_height > 0, f"Error, this grid must have at least 1 pixel of space. Got {t_height=}"
    assert n_rows > 0, f"Error, this grid must have at least 1 row. Got {n_rows=}"
    assert y_pad > -1, f"Error, y padding cannot be negative. Got {y_pad=}"
    # print(f"{t_width=}, {t_height=}, {n_rows=}, {n_cols=}, {x_pad=}, {y_pad=}, {r_type=}")

    tw = (t_width - ((n_cols + 1) * x_pad)) / (n_cols + 0)  # tile width_canvas
    th = (t_height - ((n_rows + 1) * y_pad)) / (n_rows + 0)  # tile height_canvas

    tiles = []
    if r_type == dict:
        tiles = {}

    # print(f"{tw=}, {t_width=}, {n_cols=}, {x_pad=}")
    # print(f"{th=}, {t_height=}, {n_rows=}, {y_pad=}")

    for r in range(n_rows):
        if r_type == list:
            row = []
        else:
            row = {}

        for c in range(n_cols):
            x1 = float(x_0 + (c * tw) + ((c + 1) * x_pad))  # + (x_pad / 1))
            y1 = float(y_0 + (r * th) + ((r + 1) * y_pad))  # + (y_pad / 1))
            x2 = float(x_0 + ((c + 1) * tw) + ((c + 1) * x_pad))  # + (x_pad / 1))
            y2 = float(y_0 + ((r + 1) * th) + ((r + 1) * y_pad))  # + (y_pad / 1))
            xd = float(x2 - x1)
            yd = float(y2 - y1)

            if r_int:
                x1 = round(x1)
                x2 = round(x2)
                y1 = round(y1)
                y2 = round(y2)
                xd = round(xd)
                yd = round(yd)

            if r_type == list:
                row.append([x1, y1, x2, y2])
            else:
                row[c] = {
                    "x_1": x1,
                    "y_1": y1,
                    "x_2": x2,
                    "y_2": y2,
                    "w": xd,
                    "h": yd
                }

        if r_type == list:
            tiles.append(row)
        else:
            tiles[r] = row

    return tiles


def clamp_rect(rect_bounds, out_bounds, maintain_inner_dims=False):
    """Calculate the 'clamped' rectangle within the outer bounds."""
    assert isinstance(rect_bounds, tuple) or isinstance(rect_bounds, list) or isinstance(rect_bounds,
                                                                                         Rect2), f"Error, param 'rect_bounds; needs to be a list or tuple of length 10, or an instance of a Rect2 object. Got{rect_bounds}"
    assert isinstance(out_bounds, tuple) or isinstance(out_bounds, list) or isinstance(out_bounds,
                                                                                       Rect2), f"Error, param 'out_bounds' needs to be a list or tuple of length 10, or an instance of a Rect2 object. Got {out_bounds}"

    if isinstance(rect_bounds, tuple) or isinstance(rect_bounds, list):
        assert len(rect_bounds) == 4, f"Error, list or tuple needs to be length 4. Got {rect_bounds}"
    else:
        # assuming rect was passed in format x, y, w, h, so the call tkinter_rect won't mess thing up.
        rect_bounds = list(rect_bounds.tkinter_rect())[:4]

    if isinstance(out_bounds, tuple) or isinstance(out_bounds, list):
        assert len(out_bounds) == 4, f"Error, list or tuple needs to be length 4. Got {out_bounds}"
    else:
        # assuming rect was passed in format x, y, w, h, so the call tkinter_rect won't mess thing up.
        out_bounds = list(out_bounds.tkinter_rect())[:4]

    rx1, ry1, rx2, ry2 = rect_bounds
    bx1, by1, bx2, by2 = out_bounds
    w = rx2 - rx1
    h = ry2 - ry1
    nx1 = clamp(bx1, rx1, bx2)
    ny1 = clamp(by1, ry1, by2)
    nx2 = clamp(bx1, rx2, bx2)
    ny2 = clamp(by1, ry2, by2)
    nw = nx2 - nx1
    nh = ny2 - ny1
    if not maintain_inner_dims:
        nx2 = clamp(bx1, nx1 + w, bx2)
        ny2 = clamp(by1, ny1 + h, by2)
    else:
        # print(f"A {nx1=}, {ny1=}, {nx2=}, {ny2=}, {bx1=}, {by1=}, {bx2=}, {by2=}, {w=}, {h=}, {nw=}, {nh=}")

        if nx1 >= bx1:
            if (nx2 - nx1) < w:
                nx1 = clamp(bx1, nx2 - w, bx2)
        else:
            nx1 = bx1
        if nx2 <= bx2:
            if nw < w:
                nx2 = clamp(bx1, nx1 + w, bx2)
        else:
            nx2 = bx2

        if ny1 >= by1:
            if (ny2 - ny1) < h:
                ny1 = clamp(by1, ny2 - h, by2)
        else:
            ny1 = by1
        if ny2 <= by2:
            if nh < h:
                ny2 = clamp(by1, ny1 + h, by2)
        else:
            ny2 = by2
        # print(f"B {nx1=}, {ny1=}, {nx2=}, {ny2=}, {bx1=}, {by1=}, {bx2=}, {by2=}, {w=}, {h=}, {nw=}, {nh=}")

    return [
        nx1,
        ny1,
        nx2,
        ny2
    ]


# NOTE - Copy this into the desired script you want to restart.
def restart_program():
    """Restarts the current program.
    Note: this function does not return. Any cleanup action (like
    saving data) must be done before calling this function.
    https://stackoverflow.com/questions/41655618/restart-program-tkinter
    https://www.daniweb.com/programming/software-development/code/260268/restart-your-python-program

    If you are using this in Idle, it won't work because the python process running in the shell is different from Idle gui's process.
    This will only restart the process running in the shell, not Idle itself.

    """
    python = sys.executable
    os.execl(python, python, *sys.argv)


def alpha_ize(number_in=0, capitalize=False):
    assert isinstance(number_in,
                      int) and 0 <= number_in <= 25, "Error, param 'number_in' must be an integer between 0 and 25."
    c = chr(number_in + 97)
    c = c if not capitalize else c.upper()
    return c


def alpha_seq(n_digits=1, prefix="", suffix="", numbers_instead=False, pad_0=False, shift_pad_0_on_number=True,
              capital_alpha=True, pad_char="0"):
    assert isinstance(prefix, str), f"Error, param 'prefix' must be an in stance of a string. Got '{prefix}'"
    assert isinstance(suffix, str), f"Error, param 'suffix' must be an in stance of a string. Got '{suffix}'"
    assert isinstance(n_digits,
                      int) and n_digits > 0, f"Error, param 'n_digits' must be a number and be greater than 0, Got '{n_digits}'"
    assert all([isinstance(param, bool) for param in [numbers_instead, pad_0, shift_pad_0_on_number,
                                                      capital_alpha]]), f"Error, 'params numbers_instead', 'pad_0', 'shift_pad_0_on_number', 'capital_alpha' must be boolean values.\nGot: {numbers_instead=}, {pad_0=}, {shift_pad_0_on_number=}, {capital_alpha=}"
    # print(f"A {n_digits=}, {prefix=}, {suffix=}, {numbers_instead=}, {pad_0=}, {shift_pad_0_on_number=}, {capital_alpha=}")
    pad_0 = pad_0 or ((not pad_0) and numbers_instead and shift_pad_0_on_number)
    pad_char = "0" if pad_0 and not pad_char else pad_char
    if pad_0 and ((not pad_char) or len(pad_char) > 1):
        raise ValueError(f"Error, pad_char must only be 1 character long. Got '{pad_char}'")
    # print(f"B {n_digits=}, {prefix=}, {suffix=}, {numbers_instead=}, {pad_0=}, {shift_pad_0_on_number=}, {capital_alpha=}")
    for i in range(1000):
        if numbers_instead:
            val = i
        else:
            c, i = divmod(i, 26)
            # print(f"\t{i=}, {divmod(i, 26)=}, {divmod(c, 26)=}")
            v, r = divmod(c, 26)

            if v > n_digits:
                raise StopIteration(f"Error, too many digits calculated '{v}'. Allowed digits={n_digits}")

            val = ""
            if c:
                val += alpha_ize(v + (c - 1))
            # for j in range(c, 0, -1):
            #     val += alphaize(j - 1)
            val += alpha_ize(i)
            if capital_alpha:
                val = val.upper()
        val = str(val)
        if len(val) > n_digits:
            raise StopIteration(f"Error, value '{val}' is too long. Allowed digits={n_digits}")
        elif len(val) < n_digits and pad_0:
            val = val.rjust(n_digits, pad_char)
        # else:
        # print(f"VAL='{val}'")
        yield f"{prefix}{val}{suffix}"


def excel_column_name(n: int, up_to: bool = True):
    if n < 0:
        return ""
    if n == 0:
        return "A"
    if not up_to:
        nd, nm = divmod(n, 26)
        return excel_column_name(nd - 1, up_to=False) + chr(ord("A") + (n % 26))
    else:
        return [excel_column_name(i, up_to=False) for i in range(n + 1)]


def sort_2_lists(list_1, list_2, reverse=False):
    # https://stackoverflow.com/questions/13668393/python-sorting-two-lists
    # l1 = [-7, 4, 0, -6, 14, 1, -4]
    # l2 = list(range(len(l1)))
    # sort_2_lists(l1, l2)
    # # [[-7, -6, -4, 0, 1, 4, 14], [0, 3, 6, 2, 5, 1, 4]]
    # sort_2_lists(l2, l1)
    # # [[0, 1, 2, 3, 4, 5, 6], [-7, 4, 0, -6, 14, 1, -4]]
    return [list(x) for x in zip(*sorted(zip(list_1, list_2), key=itemgetter(0), reverse=reverse))]


def margins(t_width, n_btns, btn_width):
    """Calculate margins given a total width_canvas, button_width and number of buttons.
    Usage:

        # Want to place 3 buttons of width_canvas 100, in a total width_canvas of 600
        m = margins(600, 3, 100)
    """
    assert (isinstance(t_width, int) or isinstance(t_width,
                                                   float)) and t_width > 0, "Error, param t_width must be a number greater than 0."
    assert (isinstance(n_btns, int) or isinstance(n_btns,
                                                  float)) and n_btns > 0, "Error, param n_btns must be a number greater than 0."
    assert (isinstance(btn_width, int) or isinstance(btn_width, float)) and (
            btn_width * n_btns) <= t_width, "Error, param btn_width must be a number greater than 0."
    mw = (t_width - (n_btns * btn_width)) / (n_btns + 1)
    return flatten([[
        i * (mw + btn_width),
        (i * btn_width) + ((i + 1) * mw)
    ] for i in range(n_btns + 1)])


def get_windows_user(EXTENDED_NAME_FORMAT: int = 3):
    """Get detailed information about the windows user.

    print("NameUnknown            : ", get_data(0))  -> ''
    print("NameFullyQualifiedDN   : ", get_data(1))  -> CN=Avery Briggs,OU=SBSUsers,OU=Users,OU=MyBusiness,DC=BWSDOMAIN,DC=local
    print("NameSamCompatible      : ", get_data(2))  -> BWSDOMAIN\abriggs
    print("NameDisplay            : ", get_data(3))  -> Avery Briggs
    print("NameUniqueId           : ", get_data(6))  -> {c74b0433-85cd-462d-903e-90f3a811f528}
    print("NameCanonical          : ", get_data(7))  -> BWSDOMAIN.local/MyBusiness/Users/SBSUsers/Avery Briggs
    print("NameUserPrincipal      : ", get_data(8))  -> ABriggs@BWSDOMAIN.local
    print("NameCanonicalEx        : ", get_data(9))  -> BWSDOMAIN.local/MyBusiness/Users/SBSUsers
                                                        Avery Briggs
    print("NameServicePrincipal   : ", get_data(10)) -> ''
    print("NameDnsDomain          : ", get_data(12)) -> BWSDOMAIN.LOCAL\abriggs

    Use "all" or -1 to return a dictionary of all of the values.
    Use an explicit key to return a single value, number or string (9, "NameCanonicalEx").

    https://stackoverflow.com/questions/21766954/how-to-get-windows-users-full-name-in-python
    """
    dct = {
        "NameUnknown": 0,
        "NameFullyQualifiedDN": 1,
        "NameSamCompatible": 2,
        "NameDisplay": 3,
        "NameUniqueId": 6,
        "NameCanonical": 7,
        "NameUserPrincipal": 8,
        "NameCanonicalEx": 9,
        "NameServicePrincipal": 10,
        "NameDnsDomain": 12
    }
    dct_vk = {v: k for k, v in dct.items()}

    GetUserNameEx = ctypes.windll.secur32.GetUserNameExW
    if EXTENDED_NAME_FORMAT in (-1, "all"):
        EXTENDED_NAME_FORMAT = dct
    else:
        if isinstance(EXTENDED_NAME_FORMAT, int):
            EXTENDED_NAME_FORMAT = {
                dct_vk[EXTENDED_NAME_FORMAT]: EXTENDED_NAME_FORMAT
            }
        elif isinstance(EXTENDED_NAME_FORMAT, str):
            EXTENDED_NAME_FORMAT = {
                EXTENDED_NAME_FORMAT: dct[EXTENDED_NAME_FORMAT]
            }
        else:
            raise ValueError(f"param 'EXTENDED_NAME_FORMAT' is an unrecognized value ({EXTENDED_NAME_FORMAT}).")

    results = {}

    for name, data in EXTENDED_NAME_FORMAT.items():
        size = ctypes.pointer(ctypes.c_ulong(0))
        GetUserNameEx(data, None, size)
        nameBuffer = ctypes.create_unicode_buffer(size.contents.value)
        GetUserNameEx(data, nameBuffer, size)
        results[name] = nameBuffer.value

    if len(EXTENDED_NAME_FORMAT) == 1:
        k = list(EXTENDED_NAME_FORMAT)[0]
        # print(f"{k=}, {results=}")
        return results[k]

    return results


def get_largest_monitors():
    return sorted(get_monitors(), key=lambda m: (-m.width_mm, m.width_mm * m.height_mm))


def number_suffix(n):
    if not isnumber(n):
        raise ValueError(f"Error cannot determine suffix for non-number input '{n}'")
    if isinstance(n, str) and n.count(".") != 0:
        raise ValueError(f"Error cannot determine suffix for non-integer input '{n}'")
    if not isinstance(n, str):
        n = str(n)
    # if len(n) < 2:
    #     n = f"0{n}"
    if n[-1] == "1":
        res = "st"
        if len(n) > 1:
            if n[-2] == "1":
                res = "th"
    elif n[-1] == "2":
        res = "nd"
        if len(n) > 1:
            if n[-2] == "1":
                res = "th"
    elif n[-1] == "3":
        res = "rd"
        if len(n) > 1:
            if n[-2] == "1":
                res = "th"
    else:
        res = "th"
    return res


class Dict2Class:
    """Sets a class attribute for every key in every dictionary recursively in a given dictionary."""

    def __init__(self, dictionary: dict):

        def process(d_, pref=""):
            if d_ is not None:
                for key, value in d_.items():
                    new_key = f"{pref}_{key}".removeprefix("_")
                    if isinstance(value, dict):
                        # print(f"{pref=}, {key=}")
                        process(value, new_key)
                    else:
                        setattr(self, new_key, value)

        process(dictionary)


def collect_all_files(root):
    """Return a list of absolute file paths for files in and below a given root directory."""
    walked = os.walk(root)
    all_files = []

    for root, directories, files in walked:
        all_files += [os.path.normpath(f"{root}/{file}") for file in files]

    return all_files


def mc_mac_title(name: str) -> str:
    names = name.split(" ")
    if len(names) > 1:
        # print(f"A", end="")
        f_names = " ".join([n.strip() for n in names[:-1] if n]).title()
        last_name = names[-1].lower().strip()
        if last_name.startswith("mc"):
            # print(f"A", end="")
            last_name = f"Mc{last_name[2:].title()}"
        elif last_name.startswith("mac"):
            # print(f"B", end="")
            last_name = f"Mac{last_name[2:].title()}"
        else:
            # print(f"C, '{f_names}', '{last_name}'", end="")
            last_name = last_name.title()
        r_name = f"{f_names} {last_name}"
    else:
        # print(f"B", end="")
        r_name = name
    # print(f" {r_name=}")
    return r_name


def nz(val: Any, length: int):

	def helper(val_: str, length_: int):
		if len(val_) > length_:
			return val_[:length_] + "... "
		return val_

	if isinstance(val, (pd.Series, pd.DataFrame)):
		if val.empty:
			return ""
		else:
			for i, va in enumerate(val):
				val[i] = va[:length]
			return val
	if pd.isna(val):
		return ""
	return helper(str(val))


BLK_ONE = "1", "  1  \n  1  \n  1  \n  1  \n  1  "
BLK_TWO = "2", "22222\n    2\n22222\n2    \n22222"
BLK_THREE = "3", "33333\n    3\n  333\n    3\n33333"
BLK_FOUR = "4", "    4\n4   4\n44444\n    4\n    4"
BLK_FIVE = "5", "55555\n5     \n55555\n    5\n55555"
BLK_SIX = "6", "66666\n6    \n66666\n6   6\n66666"
BLK_SEVEN = "7", "77777\n    7\n    7\n    7\n    7"
BLK_EIGHT = "8", "88888\n8   8\n88888\n8   8\n88888"
BLK_NINE = "9", "99999\n9   9\n99999\n    9\n    9"
BLK_ZERO = "0", "00000\n00  0\n0 0 0\n0  00\n00000"
BLK_A = "A", "  A  \n A A \nAA AA\nAAAAA\nA   A"
BLK_B = "B", "BBBB \nB  BB\nBBBB \nB   B\nBBBBB"
BLK_C = "C", " CCCC\nC    \nC    \nC    \n CCCC"
BLK_D = "D", "DDDD \nD   D\nD   D\nD   D\nDDDD "
BLK_E = "E", "EEEEE\nE    \nEEE  \nE    \nEEEEE"
BLK_F = "F", "FFFFF\nF    \nFFF  \nF    \nF    "
BLK_G = "G", "GGGGG\nG    \nG  GG\nG   G\nGGGGG"
BLK_H = "H", "H   H\nH   H\nHHHHH\nH   H\nH   H"
BLK_I = "I", "IIIII\n  I  \n  I  \n  I  \nIIIII"
BLK_J = "J", "JJJJJ\n  J  \n  J  \nJ J  \nJJJ  "
BLK_K = "K", "K   K\nK  K \nKKK  \nK  K \nK   K"
BLK_L = "L", "L    \nL    \nL    \nL    \nLLLLL"
BLK_M = "M", " M M \nMMMMM\nM M M\nM M M\nM M M"
BLK_N = "N", "N   N\nNN  N\nN N N\nN  NN\nN   N"
BLK_O = "O", " OOO \nO   O\nO   O\nO   O\n OOO "
BLK_P = "P", "PPPP \nP   P\nPPPP \nP    \nP    "
BLK_Q = "Q", " QQQ \nQ   Q\nQ   Q\nQ  QQ\n QQQQ"
BLK_R = "R", "RRRR \nR   R\nRRRR \nR  R \nR   R"
BLK_S = "S", " SSS \nS    \n SSS \n    S\n SSS "
BLK_T = "T", "TTTTT\n  T  \n  T  \n  T  \n  T  "
BLK_U = "U", "U   U\nU   U\nU   U\nU   U\n UUU "
BLK_V = "V", "V   V\nV   V\nV   V\n V V \n  V  "
BLK_W = "W", "W W W\nW W W\nW W W\nWWWWW\n W W "
BLK_X = "X", "X   X\n X X \n  X  \n X X \nX   X"
BLK_Y = "Y", "Y   Y\n Y Y \n  Y  \n  Y  \n  Y  "
BLK_Z = "Z", "ZZZZZ\n   Z \n  Z  \n Z   \nZZZZZ"
BLK_ADDITION = "+", "     \n  +  \n +++ \n  +  \n     "
BLK_SUBTRACTION = "-", "     \n     \n --- \n     \n     "
BLK_MULTIPLICATION = "X", "     \n X X \n  X  \n X X \n     "
BLK_DIVISON = "/", "     \n   / \n  /  \n /   \n     "
BLK_PERCENTAGE = "%", "%   %\n   % \n  %  \n %   \n%   %"


if __name__ == '__main__':
    print(f"\n\tVersion:\n{VERSION}\n")
    print(f"Details: {VERSION_DETAILS()}.")
    print(f"{VERSION_NUMBER()=}.")
    print(f"{VERSION_DATE()=}.")
    print(f"{VERSION_AUTHORS()=}.")
