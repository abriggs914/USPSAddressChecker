import calendar
import datetime
import numpy as np
from dateutil import parser
from dateutil.relativedelta import relativedelta
from utility import minmax, clamp, choice, dict_print

"""
	General datetime Utility Functions
	Version..............1.14
	Date...........2024-05-22
	Author.......Avery Briggs
"""


class datetime2(datetime.datetime):

    def __init__(self, *args, **kwargs):
        super().__init__()

    def add_month(self, n_months=1):
        return self + relativedelta(months=n_months)


def add_business_days(d, bd, holidays=None):
    if holidays is None:
        holidays = []
    i = 0
    t = datetime.datetime(d.year, d.month, d.day)
    # print("holidays: " + str(holidays))
    bd = max(i, bd)
    while i < bd:
        t = t + datetime.timedelta(days=1)
        # print("t: " + str(t) + ", (t not in holidays): " + str(t not in holidays))
        if t.weekday() < 5 and t not in holidays:
            i += 1
    return t


def business_days_between(d1, d2, holidays=None):
    business_days = 0
    if holidays is None:
        holidays = []
    date_1 = d1 if type(d1) == datetime.datetime else datetime.datetime.strptime(d1, "%d-%b-%y")
    date_2 = d2 if type(d2) == datetime.datetime else datetime.datetime.strptime(d2, "%d-%b-%y")

    date_1, date_2 = minmax(date_1, date_2)

    diff = (date_2 - date_1).days
    temp = date_1
    for i in range(diff):
        temp = date_1 + datetime.timedelta(days=i + 1)
        if temp.weekday() < 5 and temp not in holidays:  # Monday == 0, Sunday == 6
            business_days += 1
    i = 0
    while temp.weekday() >= 5 or temp in holidays:
        temp = temp + datetime.timedelta(days=1)
        if temp not in holidays:
            business_days += 1
            break
    # print("temp: {temp}\ndate_2: {date_2}\ntemp < date_2: {td2}".format(temp=temp, date_2=date_2, td2=(temp < date_2)))
    # print("business_days: " + str(business_days))
    return business_days


def same_calendar_day(d1, d2):
    if type(d1) != type(d2) and type(d1) != datetime.datetime:
        raise ValueError(
            "Check types of d1: <{d1}> and d2: <{d2}>.\nBoth values must be datetime.datetime objects.".format(d1=d1,
                                                                                                               d2=d2))
    return all([
        d1.year == d2.year,
        d1.month == d2.month,
        d1.day == d2.day
    ])


def date_suffix(day):
    if isinstance(day, datetime.datetime):
        s_day = f"{day:%Y-%m-%d}"
    else:
        s_day = str(day)
    if s_day[-1] == "1":
        res = "st"
        if len(s_day) > 1:
            if s_day[-2] == "1":
                res = "th"
    elif s_day[-1] == "2":
        res = "nd"
        if len(s_day) > 1:
            if s_day[-2] == "1":
                res = "th"
    elif s_day[-1] == "3":
        res = "rd"
        if len(s_day) > 1:
            if s_day[-2] == "1":
                res = "th"
    else:
        res = "th"
    return res


# Takes "2021-08-03"                                            -> August 3rd, 2021
# dictionary = datetime.datetime(2023,1,1, 8, 30)
# date_str_format(dictionary)                                            -> January 1st, 2023
# date_str_format(dictionary, include_time=True)                         -> January 1st, 2023 at 8:30 AM
# date_str_format(dictionary, include_time=True, include_weekday=True)   -> Sunday January 1st, 2023 at 8:30 AM
# date_str_format(dictionary, file_name)                                 -> 2021-08-03 0830
def date_str_format(date_str, include_time=False, include_weekday=False, short_month=False, short_weekday=False,
                    short_time=True, delim=" at ", file_name=False):
    """Return a date as a nicely formatted date or date and time string."""
    if isinstance(date_str, datetime.datetime):
        date_obj = date_str
    else:
        date_obj = datetime.datetime.fromisoformat(date_str)

    if file_name:
        h, m = date_obj.hour, date_obj.minute
        res = f"{date_obj:%Y-%m-%d} {f'00{h}'[-2:]}{f'00{m}'[-2:]}"
    else:
        suffix = date_suffix(date_obj)
        res = datetime.datetime.strftime(date_obj, f"%{'b' if short_month else 'B'} %d###, %Y").replace("###", suffix)
        s_res = res.split(" ")
        x = s_res[1] if s_res[1][0] != "0" else s_res[1][1:]
        res = " ".join([s_res[0], x, s_res[2]])
        if include_time:
            h = str(date_obj.hour)
            if short_time and (date_obj.hour > 12):
                h = str(date_obj.hour - 12)
            if short_time and (h == "0"):
                h = "12"
            h = h.removeprefix("0")
            m = ("00" + str(date_obj.minute))[-2:]
            p = date_obj.strftime("%p") if short_time else ""
            res = f"{res}{delim}{h}:{m} {p}".strip()

        if include_weekday:
            res = f"{date_obj:%{'a' if short_weekday else 'A'}}, {res}"
    return res


# leap year calculation: https://www.timeanddate.com/date/leapyear.html
def random_date(start_year=1, end_year=10000, start_m=None, start_d=None):
    start_year, end_year = minmax(start_year, end_year)
    start_year = clamp(1, start_year, end_year)
    end_year = clamp(start_year + 1, end_year + 1, 10000)

    r_y = list(range(start_year, end_year))
    r_m = list(range(1, 13))
    r_d = list(range(1, 32))
    r_dsm = list(range(1, 31))
    r_df = list(range(1, 29))
    r_dfl = list(range(1, 30))
    r_sm = [2, 4, 6, 9, 11]
    y = choice(r_y)
    m = choice(r_m)
    if start_m in r_m:
        m = start_m
    if m in r_sm:
        d = choice(r_dsm)
        if start_d in r_dsm:
            d = start_d
    else:
        d = choice(r_d)
        if start_d in r_d:
            d = start_d

    if m == 2:
        d = choice(r_df)
        if start_d in r_df:
            d = start_d
        if y % 4 == 0 and (y % 100 != 0 or y % 400 == 0):
            d = choice(r_dfl)
            if start_d in r_dfl:
                d = start_d

    return "{}-{}-{}".format(("0000" + str(y))[-4:], ("00" + str(m))[-2:], ("00" + str(d))[-2:])


def is_date_w_fmt(date_in, fmt="%Y-%m-%d"):
    if isinstance(date_in, datetime.datetime) or isinstance(date_in, datetime.date):
        return True
    try:
        d = datetime.datetime.strptime(date_in, fmt)
        return True
    except TypeError:
        print("Cannot determine if date param \"{}\" is a valid date using datetime format: {}".format(date_in, fmt))
    except ValueError:
        print("Cannot determine if date param \"{}\" is a valid date using datetime format: {}".format(date_in, fmt))

    return False


def is_date(date_string):
    if isinstance(date_string, datetime.datetime) or isinstance(date_string, datetime.date):
        return True
    if not date_string:  # Check if the input string is empty
        return False
    try:
        # Attempt to parse the input string as a date
        return parser.parse(date_string)
    except (ValueError, TypeError):
        return None


def first_of_day(date_in):
    """Return the given date at 00:00 that morning."""
    assert isinstance(date_in, datetime.datetime)
    return datetime.datetime(date_in.year, date_in.month, date_in.day)


def end_of_day(date_in):
    """Return the given date at 23:59 that night."""
    assert isinstance(date_in, datetime.datetime)
    return datetime.datetime(date_in.year, date_in.month, date_in.day, 23, 59, 59, 9)


def first_of_week(date_in):
    """Return the date corresponding to the beginning of the week (Sunday) for a given date's calendar week."""
    assert isinstance(date_in, datetime.datetime)
    print("date_in:", date_in)
    # return datetime.datetime.fromisoformat("2022-02-02")
    wd = 0 if date_in.isocalendar()[2] == 7 else date_in.isocalendar()[2]
    return date_in + datetime.timedelta(days=-wd)
    # return datetime.datetime.fromisocalendar(date_in.isocalendar()[0], date_in.isocalendar()[1], 1) + datetime.timedelta(hours=date_in.hour, minutes=date_in.minute, seconds=date_in.second)
    # return datetime.datetime(date_in.year, date_in.month, 1, date_in.hour, date_in.minute, date_in.second)


def end_of_week(date_in):
    """Return the date corresponding to the ending of the week (Saturday) for a given date's calendar week."""
    assert isinstance(date_in, datetime.datetime)
    print("date_in:", date_in)
    # return datetime.datetime.fromisoformat("2022-02-02")
    wd = 6 - (0 if date_in.isocalendar()[2] == 7 else date_in.isocalendar()[2])
    return date_in + datetime.timedelta(days=wd)
    # return datetime.datetime.fromisocalendar(date_in.isocalendar()[0], date_in.isocalendar()[1], 1) + datetime.timedelta(hours=date_in.hour, minutes=date_in.minute, seconds=date_in.second)
    # return datetime.datetime(date_in.year, date_in.month, 1, date_in.hour, date_in.minute, date_in.second)


def first_of_month(date_in):
    """Return the date corresponding to the beginning of the month for a given date."""
    assert isinstance(date_in, datetime.datetime)
    return datetime.datetime(date_in.year, date_in.month, 1, date_in.hour, date_in.minute, date_in.second)


def end_of_month(date_in):
    """Return the date corresponding to the ending of the month for a given date."""
    assert isinstance(date_in, datetime.datetime), "Parameter date_in needs to be a datetime.datetime object."
    y, m = date_in.year, date_in.month
    num_days = calendar.monthrange(y, m)[-1]
    return datetime.datetime(y, m, num_days)


def datetime_is_tz_aware(datetime_in):
    """Return weather or not a datetime object is aware of timezones or not.
    https://stackoverflow.com/questions/5802108/how-to-check-if-a-datetime-object-is-localized-with-pytz#:~:text=From%20datetime%20docs%3A%201%20a%20datetime%20object%20d,d.tzinfo%20is%20None%20or%20d.tzinfo.utcoffset%20%28d%29%20is%20None"""
    assert isinstance(datetime_in, datetime.datetime), "Error param 'datetime_in' must be an instance of a datetime."
    return datetime_in.tzinfo is not None and datetime_in.tzinfo.utcoffset(datetime_in) is not None


def hours_diff(d1, d2):
    assert isinstance(d1, datetime.datetime), f"Parameter d1: \"{d1}\" needs to be a datetime.datetime instance."
    assert isinstance(d2, datetime.datetime), f"Parameter d2: \"{d2}\" needs to be a datetime.datetime instance."
    return ((d2 - d1).days * 24) + ((d2 - d1).seconds / (60 * 60))


def replace_timestamp_datetime(str_in, col_in_question=None):
    """Take a dict.__repr__ before calling eval, and replace all instances of Timestamp("YYYY-MM-DD HH:MM:SS")
     with calls to datetime.datetime.strptime with appropriate parsing sequence.

     Usage:
        s = "{'DateCreated': Timestamp('2022-11-15 16:30:00'), 'Name': 'NAME HERE'}"
        s = eval(replace_timestamp_datetime(s, col_in_question='DateCreated'))  # =>
     """
    result = ""
    split_val = ", '"
    spl = str_in.split(split_val)
    r_in = "datetime.datetime.strptime"
    r_out = "Timestamp"
    if col_in_question is None:
        col_in_question = []
    if not isinstance(col_in_question, list) and not isinstance(col_in_question, tuple):
        col_in_question = [col_in_question]
    # print(f"{col_in_question=}")
    for s in spl:
        # print_by_line([(s.replace("{'", "").startswith(col), col, s) for col in col_in_question])
        if not col_in_question or any([s.replace("{'", "").startswith(col) for col in col_in_question]):
            end = s[-22:-1] + ", '%Y-%m-%d %H:%M:%S')"
            ss = s.replace(r_out, r_in)
            ss = ss[:-22] + end
            result += ss
        else:
            result += s
        result += split_val
    result = result[:len(result) - len(split_val)]
    # print(f"result: '{result}'")
    return result


def is_date_dtype(df, col_name):
    """
    Check if the data type of a column in a Pandas DataFrame is a date or time data type.
    Args:
        df (pandas.DataFrame): The DataFrame containing the column to check.
        col_name (str): The name of the column to check.
    Returns:
        bool: True if the column data type is a date or time data type, False otherwise.
    """
    dtype = df.dtypes[col_name]
    return np.issubdtype(dtype, np.datetime64) or np.issubdtype(dtype, np.timedelta64)


def time_between(date_1: datetime.datetime, date_2: datetime.datetime):
    date_format = "%Y-%m-%d"

    # Convert the date strings to datetime objects
    if isinstance(date_1, str):
        date1 = datetime.datetime.strptime(date_1, date_format)
    else:
        date1 = date_1
    if isinstance(date_2, str):
        date2 = datetime.datetime.strptime(date_2, date_format)
    else:
        date2 = date_2

    # Calculate the difference between the dates
    delta = date2 - date1
    days = delta.days

    # Calculate years, months, and days
    years, remainder = divmod(days, 365)

    # Adjust for leap years using calendar module
    leap_years = sum(calendar.isleap(year) for year in range(date1.year, date2.year + 1))
    days_without_leap_years = days - leap_years

    years = years + leap_years / 365  # Adjust for leap years

    months, days = divmod(days_without_leap_years, 30)

    # Format the description
    parts = []
    if int(years) > 0:
        parts.append(f"{int(years)} {'year' if int(years) == 1 else 'years'}")
    if int(months) > 0:
        parts.append(f"{int(months)} {'month' if int(months) == 1 else 'months'}")
    if int(days) > 0:
        parts.append(f"{int(days)} {'day' if int(days) == 1 else 'days'}")

    return ", ".join(parts) if parts else "0 days"

    # s_p_m = 60
    # s_p_h = 60 * s_p_m
    # s_p_d = 24 * s_p_h
    #
    # y1, m1, d1, h1, n1, s1 = date_1.year, date_1.month, date_1.day, date_1.hour, date_1.minute, date_1.second
    # y2, m2, d2, h2, n2, s2 = date_2.year, date_2.month, date_2.day, date_2.hour, date_2.minute, date_2.second
    # yd, md, dd, hd, nd, sd = y2 - y1, m2 - m1, d2 - d1, h2 - h1, n2 - n1, s2 - s1
    #
    # result = f""
    #
    # print(dict_print({
    #     "d1": date_1,
    #     "d2": date_2,
    #     "yd": yd,
    #     "md": md,
    #     "dd": dd,
    #     "hd": hd,
    #     "nd": nd,
    #     "sd": sd,
    # }, "A"))
    #
    # if (yd > 1) or (yd == 1 and (md >= 0) and (dd >= 0)):
    #     # at least one year has passed
    #     result += f"{yd} year{'s' if yd != 1 else ''}"
    # else:
    #     yd = 0
    #
    # new_date_1 = date_1 + relativedelta(years=yd)
    # rem = (date_2 - new_date_1)
    # # rem is the total time LESS THAN 1 year
    # md = date_2.month - new_date_1.month
    # if md > 1:
    #     if result:
    #         result += f", "
    #     result += f"{md} month{'s' if md != 1 else ''}"
    #
    # print(dict_print({
    #     "d1": date_1,
    #     "d2": date_2,
    #     "yd": yd,
    #     "md": md,
    #     "dd": dd,
    #     "hd": hd,
    #     "nd": nd,
    #     "sd": sd,
    # }, "B"))
    #
    # months = range(new_date_1.month, date_2.month)
    # months_days = [calendar.monthrange(new_date_1.year, m)[1] for m in months]
    # t_months_days = sum(months_days)
    # # t_months_seconds = t_months_days * s_p_d
    #
    # new_date_1 = new_date_1 + relativedelta(days=t_months_days)
    # dd = date_2.day - new_date_1.day
    # if dd > 1:
    #     if result:
    #         result += f", "
    #     result += f"{dd} day{'s' if dd != 1 else ''}"
    #
    # print(dict_print({
    #     "d1": date_1,
    #     "d2": date_2,
    #     "yd": yd,
    #     "md": md,
    #     "dd": dd,
    #     "hd": hd,
    #     "nd": nd,
    #     "sd": sd,
    # }, "C"))
    #
    # hours = range(new_date_1.hour, date_2.hour)
    # t_day_hours = len(hours)
    # new_date_1 = new_date_1 + relativedelta(hours=t_day_hours)
    # hd = date_2.hour - new_date_1.hour
    # if hd > 1:
    #     if result:
    #         result += f", "
    #     result += f"{hd} hour{'s' if hd != 1 else ''}"
    #
    # print(f"{rem=}, {months=}, {months_days=}, {new_date_1=}")
    #
    # return result
    #
    # # s_p_m = 60
    # # s_p_h = 60 * s_p_m
    # # s_p_d = 24 * s_p_h
    # #
    # # diff = (d2 - d1).total_seconds()
    # #
    # # cd1, cd2 = minmax(d1, d2)
    # # print(f"{cd1=}, {cd2=}")
    # # years = range(cd1.year, cd2.year + 1)
    # # leap_years = [is_leap_year(datetime.datetime(y, 1, 1)) for y in years]
    # # if leap_years:
    # #     if leap_years[0]:
    # #         # if this date is after the leap date, then exclude
    # #         if cd1 > datetime.datetime(cd1.year, 2, 29):
    # #             leap_years[0] = False
    # #     if leap_years[-1]:
    # #         # if this date is before the leap date, then exclude
    # #         if cd2 < datetime.datetime(cd2.year, 2, 29):
    # #             leap_years[-1] = False
    # #
    # # seconds_years = [s_p_d * (365 + (1 if ly else 0)) for ly in leap_years]
    # # seconds_years[0] = (datetime.datetime(cd1.year, 12, 31, 23, 59, 59) - cd1).total_seconds()
    # # seconds_years[1] = (cd2 - datetime.datetime(cd2.year, 1, 1)).total_seconds()
    # # t_seconds_years = sum(seconds_years)
    # #
    # # ys_cd1 = datetime.datetime(cd1.year, 1, 1)
    # # ye_cd2 = datetime.datetime(cd2.year, 1, 1)
    # # py_m_cd1 = (cd1.month - 1) / 12.0
    # # py_m_cd2 = (cd2.month - 1) / 12.0
    # #
    # # py_d_cd1 = (cd1.day - 1)
    # #
    # #
    # # result = f""
    # # rem_y = diff - t_seconds_years
    # # if rem_y > 0:
    # #     n_y = len(leap_years)
    # #     result += f"{n_y} years{'s' if n_y != 1 else ''}"
    # #
    # # print(f"{diff=}, {cd1=}, {cd2=}, {years=}, {leap_years=}, {seconds_years=}, {t_seconds_years=}, {result=}")
    # #
    # # # s_m_m = 24 * 60 * 60 * 30
    # # # s_p_y = 365 * 24 * 60 * 60
    # #
    # # # years, rem_y = divmod(diff, s_p_y)
    # # # months, rem_m = divmod(rem_y, )
    # # return result


def is_leap_year(date_in: datetime.datetime):
    """
    Is a date in a leap year?
    https://www.timeanddate.com/date/leapyear.html
    """
    # y = date_in.year
    # return all([
    #     ((y % 4) == 0),
    #     ((y % 100) != 0),
    #     ((y % 400) == 0)
    # ])
    return calendar.isleap(date_in.year)


def date_to_datetime(date: datetime.date) -> datetime.datetime:
    # print(f"CONVERT {date=}")
    return datetime.datetime(int(date.year), int(date.month), int(date.day))


if __name__ == '__main__':
    # d2 = datetime.datetime(2022, 10, 10)
    # d1 = datetime2(2022, 10, 10, 23, 48, 12)
    # print("d1:", d1)
    # print("d1 + M:", d1.add_month(3))

    tests = {
        "test1": ((datetime.datetime(2022, 8, 3), datetime.datetime(2023, 12, 11)), "1 year, 4 months, 8 days"),
        "test2": ((datetime.datetime(2022, 8, 3), datetime.datetime(2023, 8, 3)), "1 year"),
        "test3": ((datetime.datetime(2022, 8, 3), datetime.datetime(2023, 8, 2, 23, 30)), "11 months, 30 days, 23 hours, 30 minutes"),
        "test4": ((datetime.datetime(2022, 8, 3), datetime.datetime(2023, 8, 3, 0, 30)), "1 year, 30 minutes")
    }

    for test_name, test_data in tests.items():
        d1, d2, answer = None, None, None
        if isinstance(test_data, tuple):
            l1 = len(test_data)
            if l1 == 2:
                if isinstance(test_data[0], tuple):
                    # with answer
                    l2 = len(test_data[0])
                    if l2 == 2:
                        params, answer = test_data
                        d1, d2 = params

                else:
                    # no answer
                    d1, d2 = test_data

        if d1 is None or d2 is None:
            raise ValueError(f"{d1=}, {d2=}")

        print(f"{test_name=}\n\t{d1=}\n\t{d2=}\n\t{time_between(d1, d2)=}\n\t{answer=}")
