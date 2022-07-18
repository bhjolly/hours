#!/usr/bin/env python3


from datetime import datetime, timedelta, date
import holidays
import os, sys, argparse, calendar

from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('--date', default=None, help="Date to calculate from (YYYY-MM-DD) [first day of this month]")
parser.add_argument('--leave', type=Path, default='holidays.txt', help="Path to holidays file [holidays.txt]")
parser.add_argument('--hours', type=float, default=7.0, help="number of usable hours in a workday (after breaks) [7]")
parser.add_argument('--eofy', type=int, default=6, help="End month of FY [6]")
parser.add_argument('--html', default=None, help="Generate html code instead of printed output and store in file")
parser.add_argument('--country', default="NZ", help="Country code [NZ]")
parser.add_argument('--prov', default="WGN", help="Holiday region/provence code [WGN] (AUK/CAN/OTA/...)")
parser.add_argument('--state', default=None, help="State code [None]")
parser.add_argument('--wait', action='store_true', help='Wait for user input before exiting (useful for Windows shortcuts)')
parser.add_argument('--noleave', action='store_true', help='do not read holidays.txt file (but still count stats)')


args = parser.parse_args()

handle = None
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


def output(string):
    global handle
    if handle is not None:
        handle.write(string + '\n')
    else:
        print(string)

if args.date is not None:
    start = datetime.strptime(args.date, '%Y-%m-%d')
else:
    start = datetime.now()
    start = datetime(start.year, start.month, 1)

sy, sm, sd = start.year, start.month, start.day
ed = calendar.monthrange(sy, sm)[1]

eofy_y, eofy_m = sy + (1 if sm > args.eofy else 0), args.eofy
eofy_d = calendar.monthrange(eofy_y, eofy_m)[1]

#start = datetime(sy, sm, sd)
eofy = datetime(eofy_y, eofy_m, eofy_d)

years = [sy, ] + ([eofy_y,] if eofy_y > sy else [])

busdays_in_fy = (start + timedelta(days=i) for i in range((eofy - start).days + 1))
busdays_in_fy = [d for d in busdays_in_fy if d.weekday() < 5]

months_in_fy = [i % 12 + 1 for i in range(sm-1, eofy_m + 12 * (sm > eofy_m))]
#months_in_fy = list(set(d.month for d in busdays_in_fy))

output(f"Getting stat holidays for: {args.prov} ({args.country})")
leave = [datetime.fromordinal(d.toordinal()) for d in holidays.CountryHoliday(args.country, prov=args.prov, state=args.state, years=years)]
leave = [d for d in leave if d >= start and d <= eofy]

if not args.leave.exists():
    args.leave = Path.home() / 'holidays.txt'


if args.leave.exists() and not args.noleave:
    output(f"Adding leave from {args.leave}")
    for line in open(args.leave):
        if line[0] == '#':
            continue
        line = line.strip()
        if len(line) == 0:
            continue
        dates = []
        line = line.replace(' - ', ' to ')
        if ' to ' in line:
            dates = line.split(' to ')
            assert len(dates) == 2, "Date ranges must consist of two dates separated by 'to' (ie: 2017-12-24 to 2018-01-10)"
            dates = [datetime.strptime(date, '%Y-%m-%d') for date in dates]
            dates = [dates[0] + timedelta(days=i) for i in range((dates[1] - dates[0]).days + 1)]
        elif ',' in line:
            dates = line.split(',')
            begin = dates[0].split('-')
            dates = [dates[0], ] + ['-'.join(begin[:2] + [x, ]) for x in dates[1:]]
            dates = [datetime.strptime(d, '%Y-%m-%d') for d in dates]
        else:
            dates = [datetime.strptime(line, '%Y-%m-%d')]

        leave += [d for d in dates if d >= start and d <= eofy]

else:
    output(f"Not counting leave days {'(--noleave set)' if args.noleave else f'(please add file at: {args.leave})'}")

holiday_days = [d for d in leave if d in busdays_in_fy] # need to do this to discount 'leave' days that cover weekends (can happen with ranges)
working_days = [d for d in busdays_in_fy if d not in holiday_days]

nhols_fy = len(busdays_in_fy) - len(working_days)
nwork_fy = len(working_days)
output("Start day: {0} at 08:00...".format(start.strftime('%Y-%m-%d')))
fmt = "{0:9} {1:7d} {2:7d} {3:7.0f}"
output("{0:9} {1:7} {2:7} {3:7}".format("Month", "H.day", "W.day", "Chg Hrs"))
for month in months_in_fy:
    str_month = calendar.month_name[month]
    nhols_month = len([d for d in holiday_days if d.month == month])
    nwork_month = len([d for d in working_days if d.month == month])
    output(fmt.format(str_month, nhols_month, nwork_month, nwork_month * args.hours))

output(fmt.format("FY", nhols_fy, nwork_fy, nwork_fy * args.hours))

if args.html is not None:
    handle.write("</pre></body></html>")
    handle.close()

if args.wait:
    input("Done, press enter to finish")
