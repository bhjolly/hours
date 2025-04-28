#!/usr/bin/env python3
from datetime import datetime, timedelta, date
import holidays
import re
import os, sys, calendar

from pathlib import Path

handle = None
suppress_output = False

def output(string):
    global handle, suppress_output
    if not suppress_output:
        if handle is not None:
            handle.write(string + '\n')
        else:
            print(string)

def get_holidays(leave_file, country, provence, start, eofy, noleave=False):
    output(f"Getting stat holidays for: {provence} ({country})")
    years = list(set([start.year, eofy.year]))
    stat_days = [datetime.fromordinal(d.toordinal()) for d in holidays.CountryHoliday(country, prov=provence, state=args.state, years=years)]
    #leave = [d for d in leave if d >= start and d <= eofy]
    leave_days = dict()
    # print(stat_days)
    if not leave_file.exists():
        leave_file = Path.home() / 'holidays.txt'

    if leave_file.exists() and not noleave:
        output(f"Adding leave from {leave_file}")
        for line in open(leave_file):
            if line[0] == '#':
                continue
            line = line.strip()
            if len(line) == 0:
                continue
            dates = []

            fte = 1
            fte_set = False
            for ftestr in re.findall(r'\s*\*\s*([\d\.]+)', line):
                assert not fte_set, "can only set FTE once per line"
                fte = float(ftestr)
                fte_set = True
                line = re.sub(r'\s*\*\s*[\d\.]+', '', line)

            parts = re.split('( to )|( - )', line)
            if len(parts) > 1:
                assert len(parts) == 4, "Date ranges must consist of two dates separated by 'to' (ie: 2017-12-24 to 2018-01-10)"
                dates = [datetime.strptime(date, '%Y-%m-%d') for date in parts[0::3]]
                dates = [dates[0] + timedelta(days=i) for i in range((dates[1] - dates[0]).days + 1)]
            else:
                parts = re.split(r'\s*,\s*', line)
                if len(parts) > 1:
                    begin = parts[0].split('-')
                    dates = [parts[0], ] + ['-'.join(begin[:2] + [x, ]) for x in parts[1:]]
                    dates = [datetime.strptime(d, '%Y-%m-%d') for d in dates]
                else:
                    dates = [datetime.strptime(line, '%Y-%m-%d')]

            for date in [d for d in dates if d >= start and d <= eofy]:
                leave_days[date] = fte 

    else:
        output(f"Not counting leave days {'(--noleave set)' if noleave else f'(please add file at: {leave_file})'}")

    return stat_days, leave_days

def get_workdaysinfy(start, workdays, workhours, eofy, workdaysbegin=None):

    workdays = [x[:3].lower() for x in workdays]
    if type(workhours) is not list:
        workhours = list(workhours)
    if len(workhours) == 1:
        workhours *= len(workdays)
    workdaysset = list(set(workdays))
    daysofweek = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']

    nweeks = max(workdays.count(dow) for dow in daysofweek)
    cycle = [False,] * 7 * nweeks
    cycle_hours = [0,] * 7 * nweeks
    prevday = -1
    week = 0
    for day, hours in zip(workdays, workhours):
        i = daysofweek.index(day)
        if i < prevday:
            week += 1
        prevday = i
        cycle[i + week*7] = True
        cycle_hours[i + week*7] = hours
    print(cycle)
    cyclelen = 7 * nweeks
    
    if workdaysbegin is None:
        workdaysbegin = start - timedelta(days=start.weekday()*-1)

    if workdaysbegin < start - timedelta(days=cyclelen):
        offset = (start - workdaysbegin).days % cyclelen
        workdaysbegin = start - timedelta(days=offset)
    elif workdaysbegin > start:
        offset = (workdaysbegin - start).days % cyclelen
        workdaysbegin = start - timedelta(days=offset)
    days_in_fy = (workdaysbegin + timedelta(days=i) for i in range((eofy - workdaysbegin).days + 1))
    # else:
    #     days_in_fy = (start + timedelta(days=i) for i in range((eofy - start).days + 1))

    months_in_fy = [i % 12 + 1 for i in range(sm-1, eofy.month + 12 * (sm > eofy.month))]
    days_in_fy = [(day, cycle_hours[i % cyclelen]) for i, day in enumerate(days_in_fy) if day >= start and cycle[i % cyclelen]]
    return days_in_fy, months_in_fy

def summarise(leave_file, country, provence, start, eofy, workdays, workhours, workdaysbegin=None, noleave=False):

    stats_in_fy, leave_in_fy = get_holidays(leave_file, country, provence, start, eofy, noleave=noleave)
    workdays_in_fy, months_in_fy = get_workdaysinfy(start, workdays, workhours, eofy, workdaysbegin=workdaysbegin)
    
    working_days = []
    stat_days, leave_days = [], []

    for day, hours in workdays_in_fy:
        
        if day in stats_in_fy:
            stat_days.append((day, hours))
        elif day in leave_in_fy:
            fte = leave_in_fy[day]
            leave_days.append((day, fte * hours))
            if fte < 1:
                working_days.append((day, hours * (1 - fte)))
        else:
            working_days.append((day, hours))

    # nhols_fy = len(busdays_in_fy) - len(working_days)
    # nwork_fy = len(working_days)
    output("Start day: {0} at 08:00...".format(start.strftime('%Y-%m-%d')))
    fmt = "{0:9} {1:7d} {2:7d} {3:7d} {4:7.0f} {5:7.0f}"
    output("{0:9} {1:7} {2:7} {3:7} {4:7} {5:7}".format("Month", "Stats", "Leave", "Bus.Day", "Leave Hrs", "Chg Hrs"))
    hols_fy, lve_fy, wrk_fy = [], [], []
    for month in months_in_fy:
        str_month = calendar.month_name[month]
        hols_mth = [hours for day, hours in stat_days if day.month == month]
        lve_mth = [hours for day, hours in leave_days if day.month == month]
        wrk_mth = [hours for day, hours in working_days if day.month == month]
        # print(month, [day for day, hours in stat_days if day.month == month])
        hols_fy += hols_mth
        lve_fy += lve_mth
        wrk_fy += wrk_mth

        output(fmt.format(str_month, len(hols_mth), len(lve_mth), len(wrk_mth), sum(lve_mth), sum(wrk_mth)))

    output(fmt.format("FY", len(hols_fy), len(lve_fy), len(wrk_fy), sum(lve_fy), sum(wrk_fy)))

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--date', default=None, help="Date to calculate from (YYYY-MM-DD) [first day of this month]")
    parser.add_argument('--leave', type=Path, default='holidays.txt', help="Path to holidays file [holidays.txt]")
    #parser.add_argument('--hours', type=float, default=7.0, nargs='+', help="Chargeable hours in a workday (after breaks) [7], can take a list of len(workdays) if you want")
    parser.add_argument('--eofy', type=int, default=6, help="End month of FY [6]")
    parser.add_argument('--html', default=None, help="Generate html code instead of printed output and store in file")
    parser.add_argument('--country', default="NZ", help="Country code [NZ]")
    parser.add_argument('--prov', default="WGN", help="Holiday region/provence code [WGN] (AUK/CAN/OTA/...)")
    parser.add_argument('--state', default=None, help="State code [None]")
    parser.add_argument('--wait', action='store_true', help='Wait for user input before exiting (useful for Windows shortcuts)')
    parser.add_argument('--noleave', action='store_true', help='do not read holidays.txt file (but still count stats)')
    parser.add_argument('--workdays', nargs='+', type=str, default=['Mon', 'Tue', 'Wed', 'Thu', 'Fri'], help='Days that you work [Mon Tue Wed Thu Fri], can stretch more than 1 week if you work 9 day fortnights')
    parser.add_argument('--workhours', nargs='+', type=float, default=[7., ], help='Hours worked per day in workdays [7.0], can be a single value or a list the same length as --workdays')
    parser.add_argument('--workdaysbegin', type=datetime, default=None, help='If --workdays covers more than 1 week (ie 1 day off/fortnight), put a date here that represent the start of a cycle')

    args = parser.parse_args()

    if args.html is not None:
        handle = open(args.html, 'w')
        handle.write('''<!DOCTYPE html>
    <html lang="en">
        <head>
        <meta charset="utf-8">
        <title>Ben's Leave Calculator</title>
        <link rel="stylesheet" href="style.css">
        <script src="script.js"></script>
        </head>
        <body>
    <pre>


    ''')
    
    if args.date is not None:
        start = datetime.strptime(args.date, '%Y-%m-%d')
    else:
        start = datetime.now()
        start = datetime(start.year, start.month, 1)
    sy, sm, sd = start.year, start.month, start.day
    # ed = calendar.monthrange(sy, sm)[1]

    eofy_y = sy + (1 if sm > args.eofy else 0)
    eofy_d = calendar.monthrange(eofy_y, args.eofy)[1]

    #start = datetime(sy, sm, sd)
    eofy = datetime(eofy_y, args.eofy, eofy_d)

    summarise(args.leave, args.country, args.prov, start, eofy, args.workdays, args.workhours, workdaysbegin=args.workdaysbegin, noleave=args.noleave)

    if args.html is not None:
        handle.write("</pre></body></html>")
        handle.close()

    if args.wait:
        input("Done, press enter to finish")
