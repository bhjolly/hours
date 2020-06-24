# 'hours' Python script
Calculate how many 'working' hours are left in a month or FY, accounting for stat holidays and leave

## Requirements
'Holidays' - https://pypi.org/project/holidays/
```
pip install holidays
```

## Usage
```
python hours.py --help
```

## Annual/sick leave
Upcoming leave can be entered into an arbitrary text file, see holidays.txt for examples, basic format is:
```
# Comment (e.g. My Trip to Canada)
2020-06-01 to 2020-06-30

# Or maybe
2020-06-01,02,03,04,05,06

# Or even
2020-06-01
2020-06-02
2020-06-03
```

