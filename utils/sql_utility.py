import re
from typing import Literal, Any

from utils.pyodbc_connection import connect
from itertools import combinations
import pandas as pd
import datetime

#######################################################################################################################
#######################################################################################################################
#######################################################################################################################

VERSION = \
    """	
    General SQL Utility Functions
    Version..............1.04
    Date...........2024-12-05
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


def no_specials(text: str, r_char: str = "") -> str:
    """ Exception on '_' """
    invalid = {
        " ", "!", "@", "#", "$", "%",
        "^", "&", "*", "(", ")", "-",
        "+", "=", "'", "\"", "[", "]",
        "{", "}", "\\", "|", ":", ";",
        "<", ",", ">", ".", "?", "/",
        "~", "`"
    }
    for c in invalid:
        text = text.replace(c, r_char)
    return text


def date_first(msg: str, keyword="date") -> str:
    """
        Ensure that a column name that specifies data follows the 'date-first' noming convention
        1 pass only! If the keyword appears
        EX: date_first("Quote Date") => "DateQuote"
    """

    r_msg = msg
    l_msg = msg.lower()
    l_key = keyword.lower()
    if l_key in l_msg:
        i = l_msg.index(l_key)
        # ensure that the word isn't "update"
        if l_msg[i - 2:i] != "up":
            r_msg = f"Date{msg[:i]}{msg[i + len(keyword):]}"
    return r_msg.strip()

    # lmsg = msg.lower()
    # if keyword in msg:
    #     idx = msg.index(keyword)
    #     if msg[idx - 2 : idx].lower() != "up":
    #         msg = f"Date{msg[:idx]}{msg[idx + len(keyword):]}"
    # print(f"RETURNED MESSAGE '{msg=}'")
    # return msg


def wrap(val: Any, is_col: bool = True, sanitize: bool = True) -> str:
    """
        Add '[' prefix and ']' suffix to a string, ensuring a unique identifier in SSMS
        Used heavily in 'parse_where' and 'create_sql' functions.

        see tests below in test_create_sql_parse_where_wrap()
    """
    if not str(val).strip():
        return ""
    # print(f"wrap: {val}")
    if is_col:
        v: str = f"[{str(val).removeprefix('[').removesuffix(']')}]"
    else:
        if isinstance(val, str) and val != "NULL":
            v: str = f"'{val}'"
        elif isinstance(val, datetime.datetime):
            v: str = f"'{val:%Y-%m-%d %H:%M:%S}'"
        elif isinstance(val, datetime.date):
            v: str = f"'{val:%Y-%m-%d}'"
        elif val is None:
            v: str = "NULL"
        else:
            v: str = str(val)
    if sanitize:
        v = v.strip()
        if v:
            v_first, *v_end = v
            v = v_first + re.sub(r"[;'\\\"]", "", v[1:-1]) + "".join(v_end[-1:])
    return v


def parse_where(clauses: Any, in_line: bool = True) -> str | list[str]:
    """
        Function to read a data structure of clauses and column names to output appropriate SQL WHERE clause

        see tests below in test_create_sql_parse_where_wrap()
    """
    trace: bool = False
    where_clause = ""

    print(f"PW type={type(clauses)}, {clauses=}")

    def op_process(var, ops_dict: dict[str: Any]) -> str:

        print(f"{var=}, {ops_dict=}")

        ops_clause = []
        for op, value_s in ops_dict.items():
            # op_s = "="
            op = op.lower()
            match op:
                case "!=":
                    op = "<>"
                case "<" | ">" | "<=" | ">=":
                    op = op
                case "in" | "not in" | "between":
                    op = op.upper()
                case "like":
                    op = "LIKE"
                case _:
                    op = "="
            # op = op_s
            test = ""
            # if not isinstance(value_s, (list, tuple)):
            value_s = [value_s]
            for i, val in enumerate(value_s):
                if op == "BETWEEN":
                    v0, v1 = val
                    ops_clause.append(f"{var} {op} {wrap(v0, is_col=False)} AND {wrap(v1, is_col=False)}")
                else:
                    if isinstance(val, (list, tuple)):
                        if op in ("IN", "NOT IN"):
                            in_mem = []
                            for j, val_ in enumerate(val):
                                in_mem.append(wrap(val_, is_col=False))
                            ops_clause.append(f"{var} {op} ({', '.join(in_mem)})")
                        else:
                            for j, val_ in enumerate(val):
                                ops_clause.append(f"{var} {op} {wrap(val_, is_col=False)}")
                    else:
                        ops_clause.append(f"{var} {op} {wrap(val, is_col=False)}")
            # test = []
            # print(f"OP {op=}, {value_s=}")
            # if not isinstance(value_s, (list, tuple)):
            #     value_s = [value_s]
            # for i, val in enumerate(value_s):
            #     if isinstance(val, (list, tuple)):
            #         if op_s == "between":
            #             v0, v1 = val
            #             test.append(f"{v0} AND {v1}")
            #         else:
            #             for j, val
            #     else:
            #
            #         test.append(f" {val}")
            #     # test = value_s
            #     print(f"OP {test=}")

            # ops_clause.append(f"{var} {op_s} {test}")
        ops_clause = "(" + (") AND (".join(ops_clause)) + ")"
        print(f"OP type={type(ops_clause)}, {ops_clause=}")
        return ops_clause

    def help_parse(clause_stmt, logic="OR", nest_level: int = 1) -> str:  # list[str]:

        if not clause_stmt:
            return ""

        # ts = ("####" * nest_level)
        ologic: str = "OR" if logic == "AND" else "AND"
        nl = "" if in_line else "\n"
        ts = "\t"
        ts1 = ("\t" * (nest_level + 0))
        # a = ts + ("(" if in_line else f"A(")
        a = ("(" if in_line else f"(")
        # b = ts + (f" {logic} " if in_line else f"\n{ts1}{logic}Z")
        b = (f" {logic} " if in_line else f"\n{ts1}{logic} ")
        c = ")" if in_line else f")"

        if trace:
            print(f"HP, LG={logic}, type={type(clause_stmt)}, {clause_stmt=}")

        if isinstance(clause_stmt, str):
            return ("=0=" if trace else "") + nl + ts + a + (
                b.join([clause_stmt]).removesuffix(logic).removeprefix("(").removesuffix(")")) + c
            # if in_line:
            #     return "(" + (f" {logic} ".join([clause_stmt]).strip().removesuffix(logic).strip()) + ")"
            # else:
            #     return "\t(" + (f" {logic} ".join([clause_stmt]).strip().removesuffix(logic).strip()) + ")"

        if isinstance(clause_stmt, (list, tuple)) and (len(clause_stmt) == 2) and isinstance(clause_stmt[1], dict):
            var, stmt_data_s = clause_stmt
            if (isinstance(var, str) and isinstance(stmt_data_s, dict)):
                d = (f" {ologic} " if in_line else f"\n{ts1}{ologic}Z")
                return ("=1=" if trace else "") + nl + ts + a + (
                    d.join([op_process(var, stmt_data_s)]).removesuffix(logic).removeprefix("(").removesuffix(")")) + c
                # return "=1=" + ts + a + (b.join([op_process(var, stmt_data_s)]).removesuffix(logic).removeprefix("(").removesuffix(")")) + c
                # return a + (b.join([op_process(var, stmt_data_s)]).strip().removesuffix(logic)) + c

            # # else:
            #     if in_line:
            #         return "(" + (f" {logic} ".join([op_process(var, stmt_data_s)]).strip().removesuffix(logic).strip()) + ")"
            #     else:
            #         return "\t(" + (f"\n\t{logic} ".join([op_process(var, stmt_data_s)]).strip().removesuffix(logic).strip()) + ")"
            # # else:
            # #     for
        if isinstance(clause_stmt, dict):
            return ("=2=" if trace else "") + nl + ts + a + (
                b.join([op_process(k, v).removeprefix("(").removesuffix(")") for k, v in clause_stmt.items()])) + c
            # if in_line:
            #     return "(" + (f" {logic} ".join([op_process(k, v) for k, v in clause_stmt.items()])) + ")"
            # else:
            #     return "\t(" + (f"\n\t{logic} ".join([op_process(k, v) for k, v in clause_stmt.items()])) + ")"

        res_clauses = []
        for i, clause_data in enumerate(clause_stmt):
            if trace:
                print(f"HP LOOP {i=}, type={type(clause_data)}, {clause_data=}")
            if isinstance(clause_stmt, dict):
                var = clause_data
                clause_data = clause_stmt[clause_data]
                if not isinstance(clause_data, dict):
                    res_clauses.extend(
                        [("=4=" if trace else "") + help_parse(cd, nest_level=nest_level + 1) for cd in clause_data])
                    # res_clauses += ["A"]
                else:
                    res_clauses.append(("=5=" if trace else "") + op_process(var, clause_data))
                    # res_clauses += ["B"]
            else:
                if isinstance(clause_data, (list, tuple)):
                    ret_val = help_parse(
                        clause_data,
                        logic=ologic,
                        nest_level=0
                    ).strip().removeprefix("(").removesuffix(")").strip()

                    res_clauses.append(
                        ("=6=" if trace else "") + "(" + ret_val + ")"
                    )
                    # res_clauses.append(op_process(var, clause_data))
                    # res_clauses += ["C"]
                elif isinstance(clause_data, str):
                    res_clauses.append(("7" if trace else "") + clause_data)
                else:
                    if isinstance(clause_data, dict):
                        res_clauses.extend([("=8=" if trace else "") + help_parse(clause_data, logic=ologic,
                                                                                  nest_level=nest_level + 1)])
                        # res_clauses += ["D"]
                    else:
                        res_clauses += [f"INVESTIGATE THIS CLAUSE_DATA {type(clause_data)=}"]
        if res_clauses:
            res_clauses[0] = f"({res_clauses[0]}"
            res_clauses[-1] = f"{res_clauses[-1]})"
        # return a + (b.join(res_clauses)) + c
        # return b.join(res_clauses)
        return f"{nl}\t" + f"{nl}\t{logic} ".join(res_clauses)
        # if in_line:
        #     return "(" + (f" {logic} ".join(res_clauses).strip().removesuffix(logic).strip()) + ")"
        # else:
        #     return "\t(" + (f"\n\t{logic} ".join(res_clauses).strip().removesuffix(logic).strip()) + ")"

    return help_parse(clauses)


def create_sql(
        table: str,
        mode: Literal["select", "insert", "update", "delete"] = "select",
        where: str | dict[str: dict[str: Any]] = "",
        group:
        tuple[tuple[str]] |
        tuple[list[str]] |
        list[tuple[str]] |
        list[list[str]] |
        list[str] |
        tuple[str] |
        str = "",
        order:
        tuple[tuple[str]] |
        tuple[list[str]] |
        list[tuple[str]] |
        list[list[str]] |
        list[str] |
        tuple[str] |
        str = "",
        default_order: str = "ASC",
        data: dict[str: Any] | list[str] | tuple[str] | str = None,
        sanitize: Literal["all", "none"] | list[str] | tuple[str] = "all",
        database: str = "BWSdb",
        ignore_no_where: bool = False,
        include_no_lock: bool = False,
        in_line: bool = False,
        transaction_wrap: bool = False,
        fetch_cols: bool = False
):
    """
        Generates SQL for a given table with optionally parameters to group, order, filter, and style output statement.
        Supports writing SELECT, UPDATE, INSERT, and DELETE statements on a single table. If your logic requires JOINs,
        this function can only provide you a starting skeleton.
        
        see tests in test_create_sql_parse_where_wrap() below.
    """

    sql_lines = []
    sql = ""

    if isinstance(sanitize, (list, tuple)):
        sanitize = [str(s).lower() for s in sanitize]
    else:
        sanitize = sanitize.lower()

    def do_sanitize(val: Any) -> bool:
        if sanitize == "all":
            return True
        if sanitize == "none":
            return False
        if isinstance(sanitize, (list, tuple)):
            return val.lower() in sanitize
        return True

    if mode in ("update", "delete"):
        if not where and not ignore_no_where:
            raise ValueError(
                f"Highly recommend including a where clause when updating or deleting. If you don't want to include a where clause, set 'ignore_no_where' to True. ")
    if mode == "update":
        if not isinstance(data, dict):
            raise ValueError(f"When updating, data must be a dictionary where keys are table column names.")

    # if table.lower().count(".dbo.") == 1:
    #     table = table.split(".dbo.")[-1]
    # elif table.lower().count(".[dbo].") == 1:
    #     table = table.split(".[dbo].")[-1]
    spl = schema_parse(table)
    table = spl[-1]
    table_str = table
    table = wrap(table)
    if spl[0]:
        database = spl[0]
    # print(f"-> {table=}, {database=}")
    if include_no_lock:
        if mode != "select":
            raise ValueError("Cannot include 'WITH (NOLOCK)' when not performing a generic select.")
        else:
            table = f"{table} WITH (NOLOCK)"
    if transaction_wrap:
        if mode == "select":
            raise ValueError(f"Shouldn't wrap select statements with Transaction.")
    if isinstance(where, str):
        where = where.replace("==", "=")
    else:
        # print(f"{where=}")
        where = parse_where(where, in_line=in_line)
    if database:
        table = f"{wrap(database)}.[dbo].{table}"
    if data is None:
        data = {}
    elif isinstance(data, str):
        data = [wrap(data)]
    elif (mode == "select") and isinstance(data, (list, tuple)):
        if data and not isinstance(data[0], str):
            raise ValueError(f"You can only pass a list of data line(s) for insertion method.")
    if data:
        # cols = "[" + "], [".join(data) + "]"
        if (mode == "insert") and isinstance(data, (list, tuple)):
            cols = list(map(wrap, data[0]))
            if in_line:
                cols = ", ".join(cols)
        else:
            cols = list(map(wrap, data))
            if in_line:
                cols = ", ".join(cols)
    else:
        if group:
            raise ValueError(f"You must specify columns for the select statement when addind a 'GROUP BY' clause.")
        if mode not in ("select", "delete"):
            raise ValueError(f"You must specify columns when not performing a generic select or delete.")

        if fetch_cols:

            try:
                # print(f"""SELECT * FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = N'{table_str}'""")
                cd = {"database": database}
                cd = parse_connection_data(cd)
                df = connect(f"""SELECT * FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = N'{table_str}'""", **cd)
                # print(f"{df=}")
                col_names = df["COLUMN_NAME"].values.tolist()
                # print(f"{col_names=}")
                if col_names:
                    cols: str = (", " if in_line else ",\n\t").join(map(wrap, col_names))
                else:
                    # cols: str = "*FAIL"
                    raise Exception()
            except Exception as e:
                # print(f"FAILURE")
                cols: str = "*"
        else:
            cols: str = "*"

    if mode == "select":
        # sql = f"SELECT {cols} FROM {table}"
        sql_lines.append(f"SELECT")
        sql_lines.append(cols)
        sql_lines.append(f"FROM")
        sql_lines.append(f"{table}")
        if where:
            # sql += f" WHERE {where}"
            sql_lines.append(f"WHERE")
            sql_lines.append(f"{where}")

        if group:
            if not isinstance(group, (list, tuple)):
                group = [group]
            group = [wrap(col) for col in group]
            if in_line:
                group = ", ".join(group)
            # sql += f" GROUP BY {group}"
            sql_lines.append(f"GROUP BY")
            sql_lines.append(group)

        if order:
            if isinstance(order, (list, tuple)):
                if len(order) == 2:
                    order = f"{wrap(order[0])} {order[1]}"
                else:
                    order = [
                        f"{wrap(col[0])} {(col[1] if len(col) == 2 else default_order).upper()}"
                        if isinstance(col, (list, tuple))
                        else f"{wrap(col)} {default_order}"
                        for col in order
                    ]
                    if in_line:
                        order = ", ".join(order)
            else:
                order = wrap(order)
            # sql += f" ORDER BY {order}"
            sql_lines.append(f"ORDER BY")
            sql_lines.append(order)
    elif mode == "insert":
        if not data or not isinstance(data, (dict, list, tuple)):
            raise ValueError(
                f"You must specify key-value pairs in the 'data' param, indicating which columns and values to insert.")
        if isinstance(data, dict):
            vals: list[str] = [wrap(val, False, sanitize=do_sanitize(key)) for key, val in data.items()]
        else:
            vals: list[str] = [("(" * min(i, 1)) + ", ".join(
                [wrap(val, False, sanitize=do_sanitize(key)) for key, val in dat.items()]) + (
                                           ")" * (1 if i < (len(data) - 1) else 0)) for i, dat in enumerate(data)]
        if in_line:
            vals: str = ", ".join(vals)
        # sql = f"INSERT INTO {table} ({cols}) VALUES ({vals})"
        sql_lines.append(f"INSERT INTO")
        sql_lines.append(f"{table}")
        sql_lines.append(f"(")
        sql_lines.append(cols)
        sql_lines.append(")")
        sql_lines.append("VALUES")
        sql_lines.append("(")
        sql_lines.append(vals)
        sql_lines.append(f")")
    elif mode == "update":
        # sql = f"UPDATE {table} SET "
        # sql += ", ".join([f"{wrap(key)} = {wrap(val, is_col=False, sanitize=do_sanitize(key))}" for key, val in data.items()])
        sql_lines.append(f"UPDATE")
        sql_lines.append(f"{table}")
        sql_lines.append("SET")
        if in_line:
            sql_lines.append(", ".join(
                [f"{wrap(key)} = {wrap(val, is_col=False, sanitize=do_sanitize(key))}" for key, val in data.items()]))
        else:
            sql_lines.append(
                [f"{wrap(key)} = {wrap(val, is_col=False, sanitize=do_sanitize(key))}" for key, val in data.items()])

        # vals: list[str] = [wrap(val, False, sanitize=do_sanitize(key)) for key, val in data.items()]
        if where:
            # sql += f" WHERE {where}"
            sql_lines.append(f"WHERE ")
            sql_lines.append(f"{where}")
    elif mode == "delete":
        # sql = f"DELETE FROM {table}"
        sql_lines.append(f"DELETE FROM")
        sql_lines.append(f"{table}")
        if where:
            # sql += f" WHERE {where}"
            sql_lines.append(f"WHERE")
            sql_lines.append(f"{where}")

    sc = "\n" if not in_line else " "
    sql = sc.join(map(
        lambda line:
        # f",{sc}".join(line) if isinstance(line, (list, tuple)) else line.strip()
        f"WW" if isinstance(line, (list, tuple)) else line.strip()
        , sql_lines
    ))
    if transaction_wrap:
        sql = f"BEGIN TRAN;{sc}{sql}"
    sql += "\n;" if not in_line else ";"
    if transaction_wrap:
        sql += f"{sc}ROLLBACK;{sc}COMMIT;"
    if not in_line:
        tbs: bool = False
        keywords = {
            "BEGIN TRAN",
            "ROLLBACK",
            "COMMIT",
            "DELETE FROM",
            "SELECT",
            "INSERT INTO",
            "VALUES",
            "UPDATE",
            "SET",
            "(",
            ")",
            "FROM",
            "WHERE",
            "GROUP BY",
            "ORDER BY"
        }
        sql = ""
        if transaction_wrap:
            sql = "BEGIN TRAN;\n\n"
        # shrink: bool = False
        print(f"{sql_lines=}")
        for i, sql_line in enumerate(sql_lines):
            print(f"{i=}, {sql_line=}")
            if isinstance(sql_line, (list, tuple)):
                for j, line in enumerate(sql_line):
                    # print(f"{i=}, {j=}, {line=}")
                    sql += f"{'\t' * int(tbs)}{line},\n"
                sql = sql.rstrip().removesuffix(",") + "\n"
            else:
                sql += f"{'\t' * int(tbs)}{sql_line}\n"
            if i < (len(sql_lines) - 1):
                # prev_line = sql_lines[i - 1].strip().upper()
                next_line = str(sql_lines[i + 1]).strip().upper()
                print(f"{next_line=}")
                for kwd in keywords:
                    if tbs or (sql_line == "VALUES"):
                        if next_line.strip().upper().startswith(kwd):
                            tbs = False
                            break
                    else:
                        # if sql_line != "VALUES":
                        if sql_line.strip().upper().startswith(kwd):
                            if ((sql_line != ")") and (next_line != "VALUES")):
                                tbs = True
                                break
                    # if prev_line.startswith(kwd):
                    #     tbs = True
                    #     break
                    # # elif tbs and any([s_line.strip().upper() for s_line in keywords])
                    # elif tbs and sql_line.strip().upper().startswith(kwd):
                    #     tbs = False
                    #     break
            # if shrink:
            #     tbs -= 1
        sql = sql.strip()
        sql += f"\n;\n"
        if transaction_wrap:
            sql += "\nROLLBACK;\nCOMMIT;"

    return sql


def parse_connection_data(data: dict | str) -> dict:
    """
        Given a dictionary of ODBC connection data, verify that the user and password are pre-verified.
        Optionally pass a single string matching the key for a known valid ODBC connection (BWSdb).
    """

    valid_ = {
        "bwsdb": {
            "uid": "user5",
            "pwd": "M@gic456"
        },
        "stargatedb": {
            "uid": "SGeu1",
            "pwd": "Pupplies-Hagard->Rio0"
        },
        "sysprocompanya": {
            "uid": "SRS",
            "pwd": ""
        },
        "sysprocompanys": {
            "uid": "SCSRS",
            "pwd": ""
        }
        ,
        "sysprocompanyl": {
            "uid": "RLeu1",
            "pwd": "5Certnord2@"
        },
        "unipoint_live": {
            "uid": "SRS",
            "pwd": ""
        },
        "companyh": {
            "uid": "user5",
            "pwd": "M@gic456"
        }
    }

    if isinstance(data, dict):
        server = data.get("server", "SERVER3").lower()
        database = data.get("database", "BWSdb").lower()
        uid = data.get("uid", valid_[database].get("uid", None))
        pwd = data.get("pwd", valid_[database].get("pwd", None))

        r_uid = valid_[database]["uid"]
        r_pwd = valid_[database]["pwd"]

        if (uid == r_uid) and (pwd == r_pwd):
            return {
                "server": server,
                "database": database,
                "uid": uid,
                "pwd": pwd
            }
    elif isinstance(data, str):
        server = "SERVER3"
        database = data.lower()
        uid = valid_[database]["uid"]
        pwd = valid_[database]["pwd"]
        if database in valid_:
            return {
                "server": server,
                "database": database,
                "uid": uid,
                "pwd": pwd
            }

    return dict()


def select_with_alias(
        table: str | list | tuple,
        alias: str | None = None,
        prefix: str | None = None,
        f_keys: list | tuple | dict = None,
        no_spaces: bool = True,
        specials_replace: bool = True,
        do_print: bool = False,
        connection_data: dict | None = None,
        with_no_locks: bool = True,
        default_join_style: Literal[
            'INNER', 'LEFT', 'RIGHT', 'FULL', 'LEFT OUTER', 'RIGHT OUTER', 'FULL OUTER'] = "INNER"
) -> str:
    """
        Select table data from an SQL Server using a table alias and column-prefixes.
        Use 'alias' to set an alias for the selecting table.
        Use 'prefix' to add a prefix to each of the columns being selected.
        'no_spaces' and 'specials_replace' modify the column names to be without spaces and specials respectively.
        'with_no_locks' adds the optional "WITH (NOLOCK)" when accessing tables.
        'default_join_style' will affect the method used to join a list of tables together.
        'connection_data' param is meant to be parsed by parse_connection function.

        See 'test_select_with_alias' in the __main__ section below, for examples.
    """

    is_str = isinstance(table, str)
    is_lst = isinstance(table, (tuple, list))
    if is_lst and (len(table) > 2) and (not f_keys):
        raise ValueError(
            f"When joining more than 2 tables, you must use pass join criterion through the 'f_keys' parameter.")

    placeholder = "##__PLACEHOLDER__##"

    l_table_names = []
    l_table_alias = []
    l_alias = []
    l_keys = []
    l_cds = []

    specials = {
        "#": "Num",
        "%": "Pctg",
        "$": "Dollars",
        "?": "",
        "/": "",
        "date": date_first
    }
    og_keys = list(specials.keys())

    for k in og_keys:
        val = specials[k]

        if (lk := len(k)) > 1:
            combos = []
            for i in range(lk + 1):
                combos_sub = list(combinations(range(lk), i))
                combos += combos_sub

            for combo in combos:
                new_key = k
                for ci in combo:
                    new_key = new_key[:ci] + k[ci].upper() + new_key[ci + 1:]
                # print(f"{k=}, {new_key=}, {combo=}")
                specials[new_key] = val

    # print(f"1 {prefix=}", end="")

    if not table:
        raise ValueError(f"'table' can't be None or empty")
    else:
        if not alias:
            # print(f" A", end="")
            if not isinstance(table, (tuple, list)):
                raise ValueError(f"'alias' can't be None or empty string")
        else:
            # print(f" B", end="")
            if not prefix:
                # print(f" C", end="")
                prefix = alias
                # raise ValueError(f"'prefix' can't be None or empty string")
            # else:
            #     prefix = prefix

    # print(f"\n2 {prefix=}")

    if not is_lst:
        tables = [(table, alias, prefix)]
    else:
        tables = table

    if f_keys is not None:
        if isinstance(f_keys, (list, tuple)) and isinstance(f_keys[0], (list, tuple)) and (len(tables) > len(f_keys)):
            # print(f"--AA")
            f_keys = list(f_keys) + [f_keys[-1] for _ in range(len(tables) - len(f_keys))]
        elif isinstance(f_keys, (list, tuple)) and (not isinstance(f_keys[0], (list, tuple))):
            # print(f"--BB")
            f_keys = [f_keys for _ in range(len(tables))]
        elif len(tables) != len(f_keys):
            # print(f"--CC")
            f_keys = list(f_keys) + [f_keys[-1] for _ in range(len(tables) - len(f_keys))]

    # print(f"{tables=}\n{f_keys=}")

    i = 0
    for tn, ta, *a in tables:
        # print(f"{tn=}, {ta=}, {a=}, {i=}, {f_keys=}")
        cd = None
        fk = (None, None, None)
        if f_keys:
            fk = f_keys[i]
        if not a:
            # no prefix | connection data | foreign key given
            a = ta
        else:
            if isinstance(a, (list, tuple)) and (len(a) > 1):
                fk = (default_join_style, a[1], placeholder)
            a = a[0]

        # print(f">> {tn=}, {ta=}, {a=}, {cd=}, {fk=}")

        l_table_names.append(tn)
        l_table_alias.append(ta)
        l_alias.append(a)
        l_keys.append(fk)
        l_cds.append(cd)
        i += 1

    select_statement = "SELECT\n"
    if do_print:
        print(select_statement)
    first = True

    re_connect = True
    if connection_data is not None:
        re_connect = False
        connection_data = parse_connection_data(connection_data)

    join_msg = ""
    cols = {}

    for tn, ta, a, cd, l_key in zip(l_table_names, l_table_alias, l_alias, l_cds, l_keys):

        if not a.endswith("_"):
            a += "_"

        # print(f"{tn=}, {ta=}, {a=}, {cd=}, {l_key=}")

        if re_connect:
            connection_data = parse_connection_data(cd)

        spl = schema_parse(tn)
        db = spl[0]
        if db:
            connection_data["database"] = db
            connection_data = parse_connection_data(connection_data)
        tn_ = schema_parse(tn)[-1]
        # if tn.lower().count(".dbo.") == 1:
        #     tn_ = tn.split(".dbo.")[-1].removeprefix("]").removeprefix(".").removeprefix("[").removesuffix("]")
        # elif tn.lower().count(".[dbo].") == 1:
        #     tn_ = tn.split(".[dbo].")[-1].removeprefix("]").removeprefix(".").removeprefix("[").removesuffix("]")
        # # if (tn.count(".dbo.") == 1) or (tn.count(".[dbo].") == 1):
        # #     tn_ = tn.split("dbo")[-1]
        # else:
        #     tn_ = tn

        # print(f"{tn=}, {tn_=}")
        df = connect(f"""SELECT * FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = N'{tn_}'""", **connection_data)
        # print(df)

        col_names = df["COLUMN_NAME"].values.tolist()

        if specials_replace:
            spec_results = []
            for word in [ta, a]:
                # l_word = word.lower()
                r_word = word
                for spec in specials:
                    # print(f"1 {spec=}, {r_word=}")
                    if spec in r_word:
                        if callable(specials[spec]):
                            r_word = specials[spec](r_word)
                        else:
                            r_word = r_word.replace(spec, "")
                spec_results.append(r_word)
            ta, a = spec_results

        if no_spaces:
            ta = ta.replace(" ", "")
            a = a.replace(" ", "")

        # print(f"{col_names=}")

        for name in col_names:
            # print(f"{name=}")

            if name not in cols:
                cols[name] = ta

            og_name = name
            if specials_replace:
                r_word = name
                for spec in specials:
                    # print(f"2 {spec=}, {r_word=}")
                    if spec in r_word:
                        if callable(specials[spec]):
                            r_word = specials[spec](r_word, spec)
                        else:
                            r_word = r_word.replace(spec, "")
                name = r_word

            if no_spaces:
                name = name.replace(" ", "")

            result = f"\t{'' if first else ','}[{ta}].[{og_name}] AS [{a}{name}]"
            select_statement += result + "\n"
            if do_print:
                print(result)
            first = False

    select_statement += "FROM\n"
    if do_print:
        print(f"FROM")

    # print(f"{cols=}")

    # print(f"{l_table_names=}, {l_table_alias=}, {l_alias=}, {l_cds=}, {l_keys=}")
    # msg = ""
    for i, lsts in enumerate(zip(l_table_names, l_table_alias, l_alias, l_cds, l_keys)):
        tn, ta, a, cd, l_key = lsts
        # print(f"<< {tn=}, {ta=}, {a=}, {cd=}, {l_key=}")
        msg = f"\t{wrap(tn)} AS {wrap(ta)}" + (" WITH (NOLOCK)" if with_no_locks else "")
        if join_msg:
            msg += join_msg.format(OTHERTABLE=ta)
            msg = msg.replace(placeholder, l_key[1])
            join_msg = ""
            # msg = msg.strip()
            select_statement += msg
        else:
            msg += ","
            select_statement += msg + "\n"

        if do_print:
            print(msg)
        if l_key:
            j_style, l1, l2 = l_key
            if j_style and l1 and l2:
                try:
                    table = cols[l1]
                except KeyError as ke:
                    raise KeyError(f"Invalid join column name '{l1}'")
                select_statement = select_statement.removesuffix(",\n") + "\n"
                msg = f"{j_style.upper()} JOIN"
                join_msg = f"\nON\n\t{wrap(table)}.[{l1}] = [{{OTHERTABLE}}].[{l2}]"
                # print(f"{i=}, {msg=}, {j_style=}, {l1=}, {l2=}")
                if i < (len(l_table_names) - 1):
                    # select_statement = select_statement.removesuffix("\n\n") + msg + "\n"
                    select_statement += msg + "\n"
                if do_print:
                    print(msg)

    select_statement = select_statement.strip().removesuffix(",").strip() + "\n;"
    select_statement = select_statement.removesuffix(",\n")

    # print(f"\n--" + ("#" * 120) + "\n")

    return select_statement


def create_history_table_202302161335(
        table: str,
        history_table: str = "",
        connection_data: dict | None = None,
        block_warnings: bool = True,
        create_alter: Literal['CREATE', 'ALTER'] = "CREATE"
):
    # TODO correct the trigger to support MULTIPLE transactions on the same table.
    #  Right now using the OldID and NewID method, only 1 record is updated in any trigger call.


    # DO NOT USE THIS FUNCTION.
    return "DO NOT USE THIS FUNCTION."


    if block_warnings:
        import warnings
        warnings.filterwarnings("ignore", category=UserWarning)

    if " " in table:
        if "[" in table or "]" in table:
            raise ValueError(f"Invalid table name '{table}'.")
        # table = f"[{table}]"

    sql = """
    SELECT *
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_NAME = '{TABLE}';
    """

    hist_table = f"[{table}_History]" if not history_table else history_table

    connection_data = parse_connection_data(connection_data)

    df = connect(sql.format(TABLE=table), **connection_data)

    if df.empty:
        raise ValueError(
            f"Couldn't find any data on table '{table}' for this database. Please check spelling and connection data settings.\n{connection_data=}")

    df_pk = df.loc[(df["TABLE_NAME"] == table) & (df["IS_NULLABLE"] == "NO") & (df["DATA_TYPE"] == "int")]
    if df_pk.empty:
        df_pk = df.loc[(df["TABLE_NAME"] == table) & (df["IS_NULLABLE"] == "NO")]

    pk = df_pk.loc[0]["COLUMN_NAME"]

    # print(f"{pk=}")

    df_history = connect(sql.format(TABLE=hist_table))

    if not df_history.empty:
        raise ValueError(f"Error this table name is already in use '{hist_table}'.")

    new_hist_columns = [
        # "[History_ID]",  # do not include PK
        "[History_DateCreated]",
        "[History_Action]",
        "[History_User]",
        "[History_Column]",
        "[History_OldValue]",
        "[History_NewValue]",
    ]

    sql_create_table = f"""{create_alter} TABLE [dbo].{hist_table} ( 
    [History_ID] [int] IDENTITY(0, 1) NOT NULL, 
    [History_DateCreated] [datetime] NULL, 
    [History_Action] [nvarchar](max) NULL,
    [History_User] [nvarchar](max) NULL,
    [History_Column] [nvarchar](max) NULL,
    [History_OldValue] [nvarchar](max) NULL,
    [History_NewValue] [nvarchar](max) NULL,
    {{REST_COLUMNS}}
    CONSTRAINT [PK_{hist_table.replace('[', '').replace(']', '')}] PRIMARY KEY CLUSTERED 
(
	[History_ID] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON) ON [PRIMARY]
) ON [PRIMARY] TEXTIMAGE_ON [PRIMARY]
GO"""
    sql_trigger = """

-- BEGIN TABLE CREATION
    {SQL_TABLE_CREATION}


-- ================================================
-- Template generated from Template Explorer using:
-- Create Trigger (New Menu).SQL
--
-- Use the Specify Values for Template Parameters
-- command (Ctrl-Shift-M) to fill in the parameter
-- values below.
--
-- See additional Create Trigger templates for more
-- examples of different Trigger statements.
--
-- This block of comments will not be included in
-- the definition of the function.
-- ================================================
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
-- =============================================
-- Author:		<{AUTHOR}>
-- Create date: <{DATE_CREATED}>
-- Description:	<{DESCRIPTION}>
-- =============================================
{CREATE_ALTER} TRIGGER [dbo].[tr_Update{TABLE}History]
   ON [{TABLE}]
   --BEFORE
   AFTER
   --INSTEAD OF
   INSERT
   , DELETE
   , UPDATE
AS
BEGIN
	-- SET NOCOUNT ON added to prevent extra result sets from
	-- interfering with SELECT statements.
	SET NOCOUNT ON;

	IF TRIGGER_NESTLEVEL() < 2 BEGIN

	    -- Differences Table
	    {SQL_DIFF_TABLE}

	    -- Declarative Statements
	    {SQL_DECLARES}

	    -- Assignment Statements
	    {SQL_ASSIGNS}

		DECLARE @user NVARCHAR(20);
		DECLARE @activity NVARCHAR(20);

		-- Insert statements for trigger here
		IF EXISTS (SELECT * FROM inserted) AND EXISTS (SELECT * FROM deleted) BEGIN
			SET @activity = 'UPDATE';
			SET @user = SYSTEM_USER;
			{SQL_UPDATED}
		END
		IF EXISTS (SELECT * FROM inserted) AND NOT EXISTS (SELECT * FROM deleted) BEGIN
			SET @activity = 'INSERT';
			SET @user = SYSTEM_USER;
			{SQL_INSERTED}
		END
		IF EXISTS (SELECT * FROM deleted) AND NOT EXISTS (SELECT * FROM inserted) BEGIN
			SET @activity = 'DELETE';
			SET @user = SYSTEM_USER;
			{SQL_DELETED}
		END

		-- Check if new changes
		{SQL_DIFF}

		-- Update the History table for as many changes as were identified
		{SQL_HIST_UPDATE}

	END
END
GO
    """
    sql_declares = ["{TD}DECLARE @{COL} AS {TYP}", "", ""]
    sql_assigns = ["{TDp1}@{COL_A} = [{COL}]", "{TD}SELECT\n", "{TD}SELECT\n", "\n{TD}FROM\n{TDp1}{TAB_A}\n{TD};"]
    sql_differences_t = """
		DECLARE @t_to_update AS TABLE
		(
			[ID] INT IDENTITY(1, 1),
			[Column] NVARCHAR(MAX),
			[ValueBefore] NVARCHAR(MAX),
			[ValueAfter] NVARCHAR(MAX)
		)
	;
	"""
    sql_differences = [
        "{TD}IF {COLA} <> {COLB} BEGIN\n{TDp1}INSERT INTO @t_to_update ([Column], [ValueBefore], [ValueAfter])\n{TDp1}SELECT '{COL}', CAST({COLA} AS NVARCHAR(MAX)), CAST({COLB} AS NVARCHAR(MAX));\n{TD}END",
        ""]
    sql_hist_update = """
    -- Finally iteratively update [dbo].[IT Request History] for each changed value

		DECLARE @c AS INT;
		SELECT @c = COUNT(*) FROM @t_to_update;

		IF @c > 0 BEGIN

			IF @user IS NULL BEGIN
				SELECT @user = SYSTEM_USER;
			END

			DECLARE @i AS INT;
			DECLARE @column AS NVARCHAR(MAX);
			DECLARE @value_before AS NVARCHAR(MAX);
			DECLARE @value_after AS NVARCHAR(MAX);

			SELECT @i = 0;

			WHILE @i < @c BEGIN

				SELECT @i = @i + 1;

				SELECT
					@column = [Column]
					,@value_before = [ValueBefore]
					,@value_after = [ValueAfter]
				FROM
					@t_to_update
				WHERE
					[ID] = @i

				INSERT INTO
					[dbo].{HIST_TABLE}
				(
				    {NEW_HIST_COLUMNS}
				    ,{LIST_HISTORY_COLUMNS}
				)

				SELECT
				    {NEW_COLUMNS}
                    ,{LIST_COLUMNS}
				FROM
					[{TABLE}]
				WHERE
					[{PK}] = ISNULL(@new_{PK_A}, @old_{PK_A})

			END
		END
    """

    invalid_types = list(map(str.upper, ["text", "ntext", "image", "timestamp"]))
    td = 2 * "\t"
    tdp1 = (len(td) + 1) * "\t"
    sql_assigns[1] = sql_assigns[1].format(TD=td)
    sql_assigns[2] = sql_assigns[2].format(TD=td)

    rest_columns = ""
    # new_hist_columns = "NEW_HISTORY_COLUMNS"
    list_history_columns = ""
    new_columns = [
        # f"'{datetime.datetime.now():%Y-%m-%d %H:%M:%S}'",
        f"GETDATE()",
        "@activity",
        "@user",
        "@column",
        "@value_before",
        "@value_after"
    ]
    list_columns = ""

    # loop the table schema and collect the column names and types to prepare declarative statements.
    # 1 new and 1 old declare per column name
    for i, row in df.iterrows():
        col = row["COLUMN_NAME"]
        typ = row["DATA_TYPE"].upper()
        siz = row["CHARACTER_MAXIMUM_LENGTH"]

        if typ in invalid_types:
            continue

        old_col = no_specials(f"old_{col.replace(' ', '_')}")
        new_col = no_specials(f"new_{col.replace(' ', '_')}")

        siz = "MAX" if siz == -1 else (int(siz) if not pd.isnull(siz) else siz)
        # print(f"{i=}, {col=}, {typ=}, {siz=}")
        new_declare = sql_declares[0].format(TD=td, COL=old_col, TYP=typ)
        old_declare = sql_declares[0].format(TD=td, COL=new_col, TYP=typ)
        r_c_size = ""
        if typ == "NVARCHAR":
            new_declare += f"({siz})"
            old_declare += f"({siz})"
            r_c_size = f"({siz})"
        sql_declares[1] += new_declare + ";\n"
        sql_declares[2] += old_declare + ";\n"

        rest_columns += f"\t[{col}] [{typ}]{r_c_size} NULL,\n"
        list_history_columns += f"{td}{tdp1}[{col}],\n"

        old_assign = sql_assigns[0].format(TDp1=tdp1, COL_A=old_col, COL=col)
        new_assign = sql_assigns[0].format(TDp1=tdp1, COL_A=new_col, COL=col)
        sql_assigns[1] += old_assign + ",\n"
        sql_assigns[2] += new_assign + ",\n"

        diff = sql_differences[0].format(TD=td, TDp1=tdp1, COLA=f"@{old_col}", COLB=f"@{new_col}", COL=col)
        sql_differences[1] += diff + "\n"

    # print(f"A {len(sql_assigns[1])=}, {sql_assigns[1][-1]=}")

    # clean up
    sql_declares[1] = sql_declares[1].removesuffix("\n")
    sql_declares[2] = sql_declares[2].removesuffix("\n")
    sql_assigns[1] = sql_assigns[1].removesuffix(",\n")
    sql_assigns[2] = sql_assigns[2].removesuffix(",\n")

    # print(f"B {len(sql_assigns[1])=}, {sql_assigns[1][-1]=}")

    sql_assigns[1] += sql_assigns[3].format(TD=td, TDp1=tdp1, TAB_A=f"DELETED [D]")
    sql_assigns[2] += sql_assigns[3].format(TD=td, TDp1=tdp1, TAB_A=f"INSERTED [I]")

    author = "Avery Briggs"
    date_created = f"{datetime.datetime.now():%Y-%m-%d %H:%M:%S}"
    description = f"SQL Trigger to check changes to all columns, and if found, then will create a history record to mark the change"
    sql_c = sql_declares[1] + '\n' + sql_declares[2]
    sql_a = sql_assigns[1] + '\n' + sql_assigns[2]
    sql_u = "-- SQL Update"
    sql_i = "-- SQL Insert"
    sql_d = "-- SQL Delete"

    rest_columns = rest_columns.removeprefix("\t").removesuffix(",\n")
    new_hist_columns = f",\n{td}{tdp1}".join(new_hist_columns)
    new_columns = f",\n{td}{tdp1}".join(new_columns)
    list_history_columns = list_history_columns.strip().removesuffix(",")

    pk = pk
    pk_a = no_specials(pk)
    sql_create_table = sql_create_table.format(REST_COLUMNS=rest_columns)
    sql_hist_update = sql_hist_update.format(
        PK=pk,
        PK_A=pk_a,
        NEW_HIST_COLUMNS=new_hist_columns,
        LIST_HISTORY_COLUMNS=list_history_columns,
        TABLE=table,
        HIST_TABLE=hist_table,
        NEW_COLUMNS=new_columns,
        # LIST_COLUMNS=list_columns
        LIST_COLUMNS=list_history_columns
    )
    all_sql = sql_trigger.format(
        TABLE=table,
        CREATE_ALTER=create_alter,
        SQL_DECLARES=sql_c,
        SQL_ASSIGNS=sql_a,
        SQL_INSERTED=sql_i,
        SQL_UPDATED=sql_u,
        SQL_DELETED=sql_d,
        AUTHOR=author,
        DATE_CREATED=date_created,
        DESCRIPTION=description,
        SQL_DIFF_TABLE=sql_differences_t,
        SQL_DIFF=sql_differences[1],
        SQL_HIST_UPDATE=sql_hist_update,
        SQL_TABLE_CREATION=sql_create_table
    )

    # print(f"{all_sql=}")

    # print(f"{sql_declares[1]}")
    # print(f"{sql_declares[2]}")
    # print(f"{sql_assigns[1]}")
    # print(f"{sql_assigns[2]}")

    if block_warnings:
        warnings.resetwarnings()

    return all_sql


def create_history_table(
        table: str,
        history_table: str = "",
        connection_data: dict | None = None,
        block_warnings: bool = True,
        create_alter: Literal['CREATE', 'ALTER'] = "CREATE"
):
    # TODO correct the trigger to support MULTIPLE transactions on the same table.
    #  Right now using the OldID and NewID method, only 1 record is updated in any trigger call.

    if block_warnings:
        import warnings
        warnings.filterwarnings("ignore", category=UserWarning)

    if " " in table:
        if "[" in table or "]" in table:
            raise ValueError(f"Invalid table name '{table}'.")
        # table = f"[{table}]"

    sql = """
    SELECT *
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_NAME = '{TABLE}';
    """

    hist_table = f"[{table}_History]" if not history_table else history_table

    connection_data = parse_connection_data(connection_data)

    df = connect(sql.format(TABLE=table), **connection_data)

    if df.empty:
        raise ValueError(
            f"Couldn't find any data on table '{table}' for this database. Please check spelling and connection data settings.\n{connection_data=}")

    df_pk = df.loc[(df["TABLE_NAME"] == table) & (df["IS_NULLABLE"] == "NO") & (df["DATA_TYPE"] == "int")]
    if df_pk.empty:
        df_pk = df.loc[(df["TABLE_NAME"] == table) & (df["IS_NULLABLE"] == "NO")]

    pk = df_pk.loc[0]["COLUMN_NAME"]

    # print(f"{pk=}")

    df_history = connect(sql.format(TABLE=hist_table))

    if not df_history.empty:
        raise ValueError(f"Error this table name is already in use '{hist_table}'.")

    new_hist_columns = [
        # "[History_ID]",  # do not include PK
        "[History_DateCreated]",
        "[History_Action]",
        "[History_User]",
        "[History_Column]",
        "[History_OldValue]",
        "[History_NewValue]",
    ]

    sql_create_table = f"""{create_alter} TABLE [dbo].{hist_table} ( 
    [History_ID] [int] IDENTITY(0, 1) NOT NULL, 
    [History_DateCreated] [datetime] NULL, 
    [History_Action] [nvarchar](max) NULL,
    [History_User] [nvarchar](max) NULL,
    [History_Column] [nvarchar](max) NULL,
    [History_OldValue] [nvarchar](max) NULL,
    [History_NewValue] [nvarchar](max) NULL,
    {{REST_COLUMNS}}
    CONSTRAINT [PK_{hist_table.replace('[', '').replace(']', '')}] PRIMARY KEY CLUSTERED 
(
	[History_ID] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON) ON [PRIMARY]
) ON [PRIMARY] TEXTIMAGE_ON [PRIMARY]
GO"""
    sql_trigger = """

-- BEGIN TABLE CREATION
    {SQL_TABLE_CREATION}


-- ================================================
-- Template generated from Template Explorer using:
-- Create Trigger (New Menu).SQL
--
-- Use the Specify Values for Template Parameters
-- command (Ctrl-Shift-M) to fill in the parameter
-- values below.
--
-- See additional Create Trigger templates for more
-- examples of different Trigger statements.
--
-- This block of comments will not be included in
-- the definition of the function.
-- ================================================
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
-- =============================================
-- Author:		<{AUTHOR}>
-- Create date: <{DATE_CREATED}>
-- Description:	<{DESCRIPTION}>
-- =============================================
{CREATE_ALTER} TRIGGER [dbo].[tr_Update{TABLE}History]
   ON [{TABLE}]
   --BEFORE
   AFTER
   --INSTEAD OF
   INSERT
   , DELETE
   , UPDATE
AS
BEGIN
	-- SET NOCOUNT ON added to prevent extra result sets from
	-- interfering with SELECT statements.
	SET NOCOUNT ON;

	IF TRIGGER_NESTLEVEL() < 2 BEGIN

	    -- Differences Table
	    {SQL_DIFF_TABLE}

	    -- Declarative Statements
	    {SQL_DECLARES}

	    -- Assignment Statements
	    {SQL_ASSIGNS}

		DECLARE @user NVARCHAR(20);
		DECLARE @activity NVARCHAR(20);

		-- Insert statements for trigger here
		IF EXISTS (SELECT * FROM inserted) AND EXISTS (SELECT * FROM deleted) BEGIN
			SET @activity = 'UPDATE';
			SET @user = SYSTEM_USER;
			{SQL_UPDATED}
		END
		IF EXISTS (SELECT * FROM inserted) AND NOT EXISTS (SELECT * FROM deleted) BEGIN
			SET @activity = 'INSERT';
			SET @user = SYSTEM_USER;
			{SQL_INSERTED}
		END
		IF EXISTS (SELECT * FROM deleted) AND NOT EXISTS (SELECT * FROM inserted) BEGIN
			SET @activity = 'DELETE';
			SET @user = SYSTEM_USER;
			{SQL_DELETED}
		END

		-- Check if new changes
		{SQL_DIFF}

		-- Update the History table for as many changes as were identified
		{SQL_HIST_UPDATE}

	END
END
GO
    """
    sql_declares = ["{TD}DECLARE @{COL} AS {TYP}", "", ""]
    sql_assigns = ["{TDp1}@{COL_A} = [{COL}]", "{TD}SELECT\n", "{TD}SELECT\n", "\n{TD}FROM\n{TDp1}{TAB_A}\n{TD};"]
    sql_differences_t = """
		DECLARE @t_to_update AS TABLE
		(
			[ID] INT IDENTITY(1, 1),
			[Column] NVARCHAR(MAX),
			[ValueBefore] NVARCHAR(MAX),
			[ValueAfter] NVARCHAR(MAX)
		)
	;
	"""
    sql_differences = [
        "{TD}IF {COLA} <> {COLB} BEGIN\n{TDp1}INSERT INTO @t_to_update ([Column], [ValueBefore], [ValueAfter])\n{TDp1}SELECT '{COL}', CAST({COLA} AS NVARCHAR(MAX)), CAST({COLB} AS NVARCHAR(MAX));\n{TD}END",
        ""]
    sql_hist_update = """
    -- Finally iteratively update [dbo].[IT Request History] for each changed value

		DECLARE @c AS INT;
		SELECT @c = COUNT(*) FROM @t_to_update;

		IF @c > 0 BEGIN

			IF @user IS NULL BEGIN
				SELECT @user = SYSTEM_USER;
			END

			DECLARE @i AS INT;
			DECLARE @column AS NVARCHAR(MAX);
			DECLARE @value_before AS NVARCHAR(MAX);
			DECLARE @value_after AS NVARCHAR(MAX);

			SELECT @i = 0;

			WHILE @i < @c BEGIN

				SELECT @i = @i + 1;

				SELECT
					@column = [Column]
					,@value_before = [ValueBefore]
					,@value_after = [ValueAfter]
				FROM
					@t_to_update
				WHERE
					[ID] = @i

				INSERT INTO
					[dbo].{HIST_TABLE}
				(
				    {NEW_HIST_COLUMNS}
				    ,{LIST_HISTORY_COLUMNS}
				)

				SELECT
				    {NEW_COLUMNS}
                    ,{LIST_COLUMNS}
				FROM
					[{TABLE}]
				WHERE
					[{PK}] = ISNULL(@new_{PK_A}, @old_{PK_A})

			END
		END
    """

    invalid_types = list(map(str.upper, ["text", "ntext", "image", "timestamp"]))
    td = 2 * "\t"
    tdp1 = (len(td) + 1) * "\t"
    sql_assigns[1] = sql_assigns[1].format(TD=td)
    sql_assigns[2] = sql_assigns[2].format(TD=td)

    rest_columns = ""
    # new_hist_columns = "NEW_HISTORY_COLUMNS"
    list_history_columns = ""
    new_columns = [
        # f"'{datetime.datetime.now():%Y-%m-%d %H:%M:%S}'",
        f"GETDATE()",
        "@activity",
        "@user",
        "@column",
        "@value_before",
        "@value_after"
    ]
    list_columns = ""

    # loop the table schema and collect the column names and types to prepare declarative statements.
    # 1 new and 1 old declare per column name
    for i, row in df.iterrows():
        col = row["COLUMN_NAME"]
        typ = row["DATA_TYPE"].upper()
        siz = row["CHARACTER_MAXIMUM_LENGTH"]

        if typ in invalid_types:
            continue

        old_col = no_specials(f"old_{col.replace(' ', '_')}")
        new_col = no_specials(f"new_{col.replace(' ', '_')}")

        siz = "MAX" if siz == -1 else (int(siz) if not pd.isnull(siz) else siz)
        # print(f"{i=}, {col=}, {typ=}, {siz=}")
        new_declare = sql_declares[0].format(TD=td, COL=old_col, TYP=typ)
        old_declare = sql_declares[0].format(TD=td, COL=new_col, TYP=typ)
        r_c_size = ""
        if typ == "NVARCHAR":
            new_declare += f"({siz})"
            old_declare += f"({siz})"
            r_c_size = f"({siz})"
        sql_declares[1] += new_declare + ";\n"
        sql_declares[2] += old_declare + ";\n"

        rest_columns += f"\t[{col}] [{typ}]{r_c_size} NULL,\n"
        list_history_columns += f"{td}{tdp1}[{col}],\n"

        old_assign = sql_assigns[0].format(TDp1=tdp1, COL_A=old_col, COL=col)
        new_assign = sql_assigns[0].format(TDp1=tdp1, COL_A=new_col, COL=col)
        sql_assigns[1] += old_assign + ",\n"
        sql_assigns[2] += new_assign + ",\n"

        diff = sql_differences[0].format(TD=td, TDp1=tdp1, COLA=f"@{old_col}", COLB=f"@{new_col}", COL=col)
        sql_differences[1] += diff + "\n"

    # print(f"A {len(sql_assigns[1])=}, {sql_assigns[1][-1]=}")

    # clean up
    sql_declares[1] = sql_declares[1].removesuffix("\n")
    sql_declares[2] = sql_declares[2].removesuffix("\n")
    sql_assigns[1] = sql_assigns[1].removesuffix(",\n")
    sql_assigns[2] = sql_assigns[2].removesuffix(",\n")

    # print(f"B {len(sql_assigns[1])=}, {sql_assigns[1][-1]=}")

    sql_assigns[1] += sql_assigns[3].format(TD=td, TDp1=tdp1, TAB_A=f"DELETED [D]")
    sql_assigns[2] += sql_assigns[3].format(TD=td, TDp1=tdp1, TAB_A=f"INSERTED [I]")

    author = "Avery Briggs"
    date_created = f"{datetime.datetime.now():%Y-%m-%d %H:%M:%S}"
    description = f"SQL Trigger to check changes to all columns, and if found, then will create a history record to mark the change"
    sql_c = sql_declares[1] + '\n' + sql_declares[2]
    sql_a = sql_assigns[1] + '\n' + sql_assigns[2]
    sql_u = "-- SQL Update"
    sql_i = "-- SQL Insert"
    sql_d = "-- SQL Delete"

    rest_columns = rest_columns.removeprefix("\t").removesuffix(",\n")
    new_hist_columns = f",\n{td}{tdp1}".join(new_hist_columns)
    new_columns = f",\n{td}{tdp1}".join(new_columns)
    list_history_columns = list_history_columns.strip().removesuffix(",")

    pk = pk
    pk_a = no_specials(pk)
    sql_create_table = sql_create_table.format(REST_COLUMNS=rest_columns)
    sql_hist_update = sql_hist_update.format(
        PK=pk,
        PK_A=pk_a,
        NEW_HIST_COLUMNS=new_hist_columns,
        LIST_HISTORY_COLUMNS=list_history_columns,
        TABLE=table,
        HIST_TABLE=hist_table,
        NEW_COLUMNS=new_columns,
        # LIST_COLUMNS=list_columns
        LIST_COLUMNS=list_history_columns
    )
    all_sql = sql_trigger.format(
        TABLE=table,
        CREATE_ALTER=create_alter,
        SQL_DECLARES=sql_c,
        SQL_ASSIGNS=sql_a,
        SQL_INSERTED=sql_i,
        SQL_UPDATED=sql_u,
        SQL_DELETED=sql_d,
        AUTHOR=author,
        DATE_CREATED=date_created,
        DESCRIPTION=description,
        SQL_DIFF_TABLE=sql_differences_t,
        SQL_DIFF=sql_differences[1],
        SQL_HIST_UPDATE=sql_hist_update,
        SQL_TABLE_CREATION=sql_create_table
    )

    # print(f"{all_sql=}")

    # print(f"{sql_declares[1]}")
    # print(f"{sql_declares[2]}")
    # print(f"{sql_assigns[1]}")
    # print(f"{sql_assigns[2]}")

    if block_warnings:
        warnings.resetwarnings()

    return all_sql


def get_database_tables(database: str) -> pd.DataFrame:
    sel_col_names = {
        "TABLE_CATALOG": "CA_0",
        "TABLE_NAME": "CA_1",
        "COLUMN_NAME": "CA_2",
        "PRIMARY_KEY": "CA_3",
        "DATA_TYPE": "CA_4",
        "CHARACTER_MAXIMUM_LENGTH": "CA_5"
    }
    sql_table_template = """
                            SELECT
                    	        [{CA_0}]
                                ,[{CA_1}]
                                ,[{CA_2}]
                                ,(CASE WHEN [IS_NULLABLE] = 'NO' THEN 1 ELSE 0 END) AS [{CA_3}]
                                ,[{CA_4}]
                                ,[{CA_5}]
                            FROM
                                INFORMATION_SCHEMA.COLUMNS
                            ORDER BY
                                [TABLE_NAME],
                                [COLUMN_NAME]
                            ;
                            """
    sql_table_template = sql_table_template.format(**{v: k for k, v in sel_col_names.items()})
    cd = {
        "database": database
    }
    cd = parse_connection_data(cd)
    try:
        df = connect(
            sql=sql_table_template,
            **cd
        )
    except Exception as e:
        df = pd.DataFrame(columns=list(sel_col_names))

    return df


def get_table_cols(table: str, database: str = "BWSdb", use_streamlit_cache: bool = False):
    if not use_streamlit_cache:
        spt = schema_parse(table)
        spd = schema_parse(database)
        spd = spd[0 if spd[0] else 1]
        tbl = spt[1].lower()
        df = get_database_tables(spd)
        return df.loc[df["TABLE_NAME"].str.lower() == tbl]
    else:
        spt = schema_parse(table)
        spd = schema_parse(database)
        sel_col_names = {
            "TABLE_CATALOG": "CA_0",
            "TABLE_NAME": "CA_1",
            "COLUMN_NAME": "CA_2",
            "PRIMARY_KEY": "CA_3",
            "DATA_TYPE": "CA_4",
            "CHARACTER_MAXIMUM_LENGTH": "CA_5",
            spt[1]: "table_str"
        }

        sql_table_template = """
                                SELECT
                        	        [{CA_0}]
                                    ,[{CA_1}]
                                    ,[{CA_2}]
                                    ,(CASE WHEN [IS_NULLABLE] = 'NO' THEN 1 ELSE 0 END) AS [{CA_3}]
                                    ,[{CA_4}]
                                    ,[{CA_5}]
                                FROM
                                    INFORMATION_SCHEMA.COLUMNS
                                WHERE
                                    [TABLE_NAME] = N'{table_str}'
                                ORDER BY
                                    [TABLE_NAME],
                                    [COLUMN_NAME]
                                ;
                                """
        # print(f"{df=}")
        # col_names = df["COLUMN_NAME"].values.tolist()
        sql_table_template = sql_table_template.format(**{v: k for k, v in sel_col_names.items()})
        cd = {
            "database": spd[0 if spd[0] else 1]
        }
        cd = parse_connection_data(cd)
        try:
            df = connect(
                sql=sql_table_template,
                **cd
            )
        except Exception as e:
            df = pd.DataFrame(columns=list(sel_col_names))

        return df


def schema_parse(table: str, wrapped: bool = False) -> tuple[str, str]:
    t_og = table
    table = table.lower()
    r = "0"
    spl = "", ""
    if table.lower().count(".dbo.") == 1:
        r = "1"
        spl = table.split(".dbo.")
        table = spl[-1]
        db = spl[0]
    elif (table.lower().count("dbo.") == 1) and (table.lstrip()[0] == ""):
        r = "2"
        spl = table.split(".dbo.")
        table = spl[-1]
        db = spl[0]
    elif table.lower().count("[dbo].") == 1:
        r = "3"
        spl = table.split("[dbo].")
        table = spl[-1]
        db = spl[0].removesuffix("]").removesuffix(".")
    elif table:
        r = "4"
        db = ""
        table = table.removeprefix(".").removeprefix("dbo").removeprefix("]").removeprefix(".").removeprefix("[")
    else:
        r = "5"
        db, table = spl

    t_idx = t_og.lower().index(table)
    d_idx = t_og.lower().index(db)
    table = t_og[t_idx: t_idx + len(table)]
    db = t_og[d_idx: d_idx + len(db)]

    # if is_title:
    #     r += "a"
    #     f = str.title
    # elif is_lower:
    #     r += "b"
    #     f = str.lower
    # elif is_upper:
    #     r += "e"
    #     f = str.upper
    # else:
    #     r += "d"
    #     f = lambda x: x
    #
    # table = f(table)
    # database = f(database)

    if not wrapped:
        r += "x"
        table = table.removeprefix("[").removesuffix("]")
        db = db.removeprefix("[").removesuffix("]")
    else:
        r += "y"
        table = wrap(table)
        db = wrap(db)
    # return t_og, r, database, table
    return db, table


if __name__ == '__main__':


    def test_select_with_alias():
        # cross join example
        print(select_with_alias([
            ("ITR Customers", "C", "C"),
            ("ITD Dept", "D", "D")
        ]))
        # cross join example
        print(select_with_alias([
            ("Orders", "O", "O"),
            ("OrdersV2", "O2", "O2")
        ]))
        # cross join example
        print(select_with_alias([
            ("ITD Dept", "D"),
            ("ITF Flags", "F")
        ]))
        # inner join example using f_keys
        print(select_with_alias(
            [
                ("Orders", "O"),
                ("Dealers", "D")
            ],
            f_keys=("inner", "DealerID", "ID")
        ))
        # inner join example using keys in the table list
        print(select_with_alias(
            [
                ("Orders", "O", "O", "DealerID"),
                ("Dealers", "D", "D", "ID")
            ]
        ))
        # inner join across multiple tables using f_keys
        print(select_with_alias(
            [
                ("Orders", "O", "O"),
                ("Dealers", "D", "D"),
                # ("Orders", "O", "O", "DealerID"),
                # ("Sales Staff", "S", "S", "Sales PersonID")
                ("Sales Staff", "S", "S")
            ],
            f_keys=(
                ("inner", "DealerID", "ID"),
                ("inner", "Sale PersonID", "ID-SaleStaff")
            )
        ))
        # left joins using f_keys
        print(select_with_alias(
            [
                ("Orders", "O"),
                ("Dealers", "D"),
                ("Sales Staff", "S"),
                ("Products", "P")
            ],
            f_keys=(
                ("left", "DealerID", "ID"),
                ("left", "Sale PersonID", "ID-SaleStaff"),
                ("left", "ProductID", "IDTrailer")
            )
        ))
        # single-table select
        print(select_with_alias(
            "Dealers", alias="D", prefix="DEAL_"
        ))


    def test_create_sql_parse_where_wrap():

        import streamlit as st

        insert_data: dict[str: Any] = {
            "Request": "Request Text",
            "DueDate": datetime.datetime.now(),
            "Company": "BWS",
            "Department": 87,
            "Priority": 3,
            "SubPriority": 1,
            "RequestType": "Hardware",
            "RequestSubType": "Computer",
            "RequestedBy": "Avery Briggs",
            "RequestFollowUpPersonnel": "avery.briggs@bwstrailers.com;abriggs914@gmail.com",
            "RequestDate": datetime.datetime.now(),
            "Status": "Queued",
            "RequestDateOriginal": "2024-11-21 17:01:59",
            "Directory": r"C:\Users\abriggs\Documents\BWS\Nulls being weird.sql"
        }
        sanitize_cols = list(insert_data.keys())
        sanitize_cols.remove("RequestFollowUpPersonnel")  # preserve semicolons delimiting email addresses
        sanitize_cols.remove("Directory")  # preserve backslashes in path

        wheres = [
            [
                ["[ITRequestID#]", {"between": [105445, 235564]}],
                ["[RequestedBy]", {"=": "Darth Vader"}]
            ],
            [
                [["[ITRequestID#]", {"between": [105445, 235564]}]],
                [["[RequestedBy]", {"=": "Darth Vader"}]]
            ],
            [
                [
                    ["[ITRequestID#]", {"between": [105445, 235564]}],
                    ["[RequestedBy]", {"=": "Darth Vader"}]
                ],
                ["[RequestedDate]", {"between": ["2050-01-01", "2051-01-01"]}]
            ],
            "[ITRequestID#] == 1",
            ["[Status] = 'Complete'"],
            ["[Status] = 'Complete'",],
            ["[ITRequestID#]", {"=": 1054789}],
            [
                [["RequestedBy", {"like": "%avery%"}]],
                [["RequestDate", {"between": ["2024-11-01", "2024-11-30 23:59:59"]}]]
            ],
            [
                [["RequestedBy", {"like": "%avery%"}],],
                [["RequestDate", {"between": ["2024-11-01", "2024-11-30 23:59:59"]}],]
            ],
            [
                ["RequestedBy", {"like": "%avery%"}],
                ["RequestDate", {"between": ["2024-11-01", "2024-11-30 23:59:59"]}]
            ],
            [
                [
                    ["RequestedBy", {"like": "%avery%"}],
                    ["RequestDate", {"between": ["2024-11-01", "2024-11-30 23:59:59"]}]
                ]
            ],
            [
                [
                    [["RequestedBy", {"like": "%avery%"}]],
                    [["RequestDate", {"between": ["2024-11-01", "2024-11-30 23:59:59"]}]]
                ]
            ],
            [
                [
                    ["RequestedBy", {"like": "%avery%"}],
                    ["RequestDate", {"between": ["2024-11-01", "2024-11-30 23:59:59"]}]
                ]
            ],
            [
                [
                    ["RequestedBy", {"like": "%avery%"}],
                    ["RequestDate", {"between": ["2024-11-01", "2024-11-30 23:59:59"]}]
                ],
                [
                    ["RequestedBy", {"like": "%james%"}],
                    ["RequestDate", {"between": ["2024-11-01", "2024-11-30 23:59:59"]}]
                ]

            ]
        ]
        for i, wh in enumerate(wheres):
            st.text(f"{i=}, {wh}")
            st.text(f"WHERE{parse_where(wh, in_line=True)}")
            st.write(f"---")
            # print(f"SUCCESS {i=}")

        # test_sqls = [
        #     create_sql(
        #         "IT Requests",
        #         data={
        #             "Request": "sample_0",
        #             "DueDate": datetime.datetime.now(),
        #             "Company": "Stargate",
        #             "Priority": 3
        #         },
        #         mode="update",
        #         where="[ITRequestID#] == 1",
        #         transaction_wrap=True
        #     ),
        #     create_sql("IT Requests", data=["Status"], include_no_lock=True),
        #     create_sql("IT Requests", where="[Status] = 'Complete'", include_no_lock=True),
        #     create_sql("IT Requests", data=["Status"], where="[Status] = 'Complete'", include_no_lock=True),
        #     create_sql("IT Requests", order="Status", include_no_lock=True),
        #     create_sql("IT Requests", order=("Status", "ASC"), include_no_lock=True),
        #     create_sql("IT Requests", data=["Status"], order="Status", include_no_lock=True),
        #     create_sql("IT Requests", where="[Status] = 'Complete'", order="Status", include_no_lock=True),
        #     create_sql("IT Requests", data=["Status"], where="[Status] = 'Complete'", order="Status",
        #                        include_no_lock=True),
        #
        #     create_sql("IT Requests", order=("Status", "DESC"), include_no_lock=True),
        #     create_sql("IT Requests", data=["Status", "Company", "RequestedBy"],
        #                        order=["Status", "Company", "RequestedBy"], include_no_lock=True),
        #     create_sql("IT Requests", where="[Status] = 'Complete'", data=["Status", "Company", "RequestedBy"],
        #                        order=[["Status", "asc"], ["Company", "desc"], "RequestedBy"], include_no_lock=True),
        #
        #     create_sql("IT Requests", data="Status", order=("Status", "DESC"), group="Status",
        #                        include_no_lock=True),
        #     create_sql("IT Requests", data=["Status", "Company", "RequestedBy"],
        #                        order=["Status", "Company", "RequestedBy"], group=["Status", "Company", "RequestedBy"],
        #                        include_no_lock=True),
        #     create_sql("IT Requests", where="[Status] = 'Complete'", data=["Status", "Company", "RequestedBy"],
        #                        order=[["Status", "asc"], ["Company", "desc"], "RequestedBy"], include_no_lock=True),
        #
        #     create_sql("IT Requests", mode="delete", where="[ITRequestID#] = 105445", transaction_wrap=True),
        #     create_sql("IT Requests", mode="delete", where=("[ITRequestID#]", {"=": 1054789}),
        #                        transaction_wrap=True),
        #     create_sql(
        #         "IT Requests",
        #         mode="delete",
        #         where=(
        #             ("[ITRequestID#]", {"between": [105445, 235564]}),
        #             ("[RequestedBy]", {"=": "Darth Vader"})
        #         ),
        #         transaction_wrap=True
        #     ),
        #
        #     # should be or
        #     create_sql(
        #         "IT Requests",
        #         mode="delete",
        #         where=(
        #             (("[ITRequestID#]", {"between": [105445, 235564]})),
        #             (("[RequestedBy]", {"=": "Darth Vader"}))
        #         ),
        #         transaction_wrap=True
        #     ),
        #
        #     create_sql(
        #         "IT Requests",
        #         mode="delete",
        #         where=(
        #             (
        #                 ("[ITRequestID#]", {"between": [105445, 235564]}),
        #                 ("[RequestedBy]", {"=": "Darth Vader"})
        #             ),
        #             ({"between": ["2050-01-01", "2051-01-01"]})
        #         ),
        #         transaction_wrap=True
        #     ),
        #
        #     create_sql(
        #         "IT Requests",
        #         data=insert_data,
        #         mode="insert",
        #         sanitize=sanitize_cols,
        #         transaction_wrap=True
        #     )
        # ]
        #
        # for i, sql in enumerate(test_sqls):
        #     # print(f"{sql}")
        #     st.text(sql)
        #     st.write("---")

        # st.text(create_sql(
        #     "IT Requests",
        #     data={
        #         "Request": "sample_0",
        #         "DueDate": datetime.datetime.now(),
        #         "Company": "Stargate",
        #         "Priority": 3
        #     },
        #     mode="update",
        #     where="[ITRequestID#] == 1",
        #     transaction_wrap=True
        # ))
        # st.text(create_sql("IT Requests", data=["Status"], include_no_lock=True))
        # st.text(create_sql("IT Requests", where="[Status] = 'Complete'", include_no_lock=True))
        # st.text(create_sql("IT Requests", data=["Status"], where="[Status] = 'Complete'", include_no_lock=True))
        # st.text(create_sql("IT Requests", order="Status", include_no_lock=True))
        # st.text(create_sql("IT Requests", order=("Status", "ASC"), include_no_lock=True))
        # st.text(create_sql("IT Requests", data=["Status"], order="Status", include_no_lock=True))
        # st.text(create_sql("IT Requests", where="[Status] = 'Complete'", order="Status", include_no_lock=True))
        # st.text(create_sql("IT Requests", data=["Status"], where="[Status] = 'Complete'", order="Status", include_no_lock=True))
        #
        # st.text(create_sql("IT Requests", order=("Status", "DESC"), include_no_lock=True))
        # st.text(create_sql("IT Requests", data=["Status", "Company", "RequestedBy"], order=["Status", "Company", "RequestedBy"], include_no_lock=True))
        # st.text(create_sql("IT Requests", where="[Status] = 'Complete'", data=["Status", "Company", "RequestedBy"], order=[["Status", "asc"], ["Company", "desc"], "RequestedBy"], include_no_lock=True))
        #
        # st.text(create_sql("IT Requests", data="Status", order=("Status", "DESC"), group="Status", include_no_lock=True))
        # st.text(create_sql("IT Requests", data=["Status", "Company", "RequestedBy"], order=["Status", "Company", "RequestedBy"], group=["Status", "Company", "RequestedBy"], include_no_lock=True))
        # st.text(create_sql("IT Requests", where="[Status] = 'Complete'", data=["Status", "Company", "RequestedBy"], order=[["Status", "asc"], ["Company", "desc"], "RequestedBy"], include_no_lock=True))
        #
        # st.text(create_sql("IT Requests", mode="delete", where="[ITRequestID#] = 105445", transaction_wrap=True))
        # st.text(create_sql("IT Requests", mode="delete", where=("[ITRequestID#]", {"=": 1054789}), transaction_wrap=True))
        # st.text(create_sql(
        #     "IT Requests",
        #     mode="delete",
        #     where=(
        #         ("[ITRequestID#]", {"=": [105445, 235564]}),
        #         ("[RequestedBy]", {"=": "Darth Vader"})
        #     ),
        #     transaction_wrap=True
        # ))
        # insert_data: dict[str: Any] = {
        #     "Request": "Request Text",
        #     "DueDate": datetime.datetime.now(),
        #     "Company": "BWS",
        #     "Department": 87,
        #     "Priority": 3,
        #     "SubPriority": 1,
        #     "RequestType": "Hardware",
        #     "RequestSubType": "Computer",
        #     "RequestedBy": "Avery Briggs",
        #     "RequestFollowUpPersonnel": "avery.briggs@bwstrailers.com;abriggs914@gmail.com",
        #     "RequestDate": datetime.datetime.now(),
        #     "Status": "Queued",
        #     "RequestDateOriginal": "2024-11-21 17:01:59",
        #     "Directory": r"C:\Users\abriggs\Documents\BWS\Nulls being weird.sql"
        # }
        # sanitize_cols = list(insert_data.keys())
        # sanitize_cols.remove("RequestFollowUpPersonnel")  # preserve semicolons delimiting email addresses
        # sanitize_cols.remove("Directory")  # preserve backslashes in path
        # st.text(create_sql(
        #     "IT Requests",
        #     data=insert_data,
        #     mode="insert",
        #     sanitize=sanitize_cols,
        #     transaction_wrap=True
        # ))
        #
        # # # st.text(
        # # #     op_process("[ITRequestID#]", {"=": [105445,235567]})
        # # # )
        # # # st.text(
        # # #     op_process("[RequestDate]", {"between": ['2024-11-20', '2024-11-21 23:59:59']})
        # # # )
        # # # st.text(
        # # #     op_process("[ITRequestID#]", {"!=": "15444"})
        # # # )
        # # # st.text(
        # # #     op_process("[ITRequestID#]", {"in": [6565, 454848, 454481]})
        # # # )
        # # # st.text(
        # # #     op_process("[Status#]", {"not in": ["Complete", "Declined", "Incomplete"]})
        # # # )
        # #
        # # st.text(
        # #     parse_where((
        # #         ("[ITRequestID#]", {"between": [105445, 235564]}),
        # #         ("[RequestedBy]", {"=": "Darth Vader"})
        # #     ))
        # # )
        # # st.text(parse_where("[ITRequestID#] = 105445"))
        # # st.text(parse_where(("[ITRequestID#]", {"=": 1054789})))
        # # # st.text(
        # # #     parse_where("[RequestDate]", {"between": ['2024-11-20', '2024-11-21 23:59:59']})
        # # # )
        # # # st.text(
        # # #     parse_where("[ITRequestID#]", {"!=": "15444"})
        # # # )
        # # # st.text(
        # # #     parse_where("[ITRequestID#]", {"in": [6565, 454848, 454481]})
        # # # )
        # # # st.text(
        # # #     parse_where("[Status#]", {"not in": ["Complete", "Declined", "Incomplete"]})
        # # # )


    # test_select_with_alias()
    # test_create_sql_parse_where_wrap()
