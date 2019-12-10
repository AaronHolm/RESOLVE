"""
module to store file in and out related function

############################ LICENSE INFORMATION ############################
This file is part of the E3 RESOLVE Model.

Copyright (C) 2019 Energy and Environmental Economics, Inc.
For contact information, go to www.ethree.com

The E3 RESOLVE Model is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

The E3 RESOLVE Model is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with the E3 RESOLVE Model (in the file LICENSE.TXT). If not,
see <http://www.gnu.org/licenses/>.
#############################################################################
"""

import csv as _csv
import numpy as _np
from datetime import datetime as _datetime
from collections import defaultdict as _defaultdict
from functools import reduce
import sys


def dictfromfile(path,
                 header_as_keys,
                 num_columns_as_keys,
                 skiprows=None,
                 knowncsvfile=True,
                 autoparse=True,
                 stripwhitespace=True,
                 removerowblanks=False,
                 removeblankcolumns=False):
    """Reads a file and puts the data into a dictionary

    Args:
        path (string): File path
        num_columns_as_keys (int): Number of columns, starting from 0 that are keys.
        header_as_keys (bool): Indicates whether the first row should also be made a key.
        skiprows (int): number of rows to skip. Defaults to 0. This happens FIRST, before reading headers.
        knowncsvfile (bool): indicates if the file is known to be a CSV. Defaults to False.

    Returns:
        recurivedict: data in a set of default dictionaries

    Notes:
        1. Data is parsed using dataparse
        2. Blank values are included
        3. Skiprows happen BEFORE any header is read

    """
    assert num_columns_as_keys >= 1 or header_as_keys
    if not is_strint(str(num_columns_as_keys)):
        raise TypeError("num_columns_as_keys argument must be type int()")
    if skiprows is not None and not is_strint(str(skiprows)):
        raise TypeError("skiprows argument must be type int()")
    if type(header_as_keys) is not bool:
        raise TypeError("skiprows argument must be type int()")

    datalist = listfromfile(
        path, skiprows, knowncsvfile,
        autoparse, stripwhitespace, removerowblanks,
        removeblankcolumns
    )
    assert len(datalist[0]) > 1

    return list2dict(datalist, header_as_keys, num_columns_as_keys)


def listfromfile(path,
                 skiprows=None,
                 knowncsvfile=True,
                 autoparse=True,
                 stripwhitespace=True,
                 removerowblanks=False,
                 removeblankcolumns=False):
    """Reads data from a file into a list
    Note: this function strips whitespace from data as it is read
    csv2list uses fileio.parse_row function to datatype the data for each row

    Args:
        path (string): File path
        skiprows (int): Number of rows to skip. Defaults to zero.
        removeblanks (bool): if True, empty strings "" are ignored. Defaults to False.
        knowncsvfile (bool): indicates if the file is known to be a CSV. Defaults to False.
        autoparse (bool): automatically parse data. Defaults to True.

    Returns:
        list: list of data by row

        If the data is 1 dimensional, a single dimension is returned

    """
    reader = csvreader(path) if knowncsvfile else filereader(path)

    if skiprows is not None:
        if not is_strint(str(skiprows)):
            raise TypeError("skiprows argument must be type int()")
        for i in range(skiprows):
            reader.next()

    data = [
        parserow(row, stripwhitespace, removerowblanks) if autoparse else row
        for row in reader
    ]
    if removeblankcolumns:
        data = rstrip_blank_columns(data)
    # remove blanks at the end of the row
    if removerowblanks:
        data = [rstrip_blank_columns([row])[0] for row in data]
    if all([len(d) == 1 for d in data]):  # checks to see if 1d
        data = flatten_list(data)  # if so, flattens data

    return data


def list2dict(datalist, header_as_keys, num_columns_as_keys):
    datadict = recursivedict()

    if num_columns_as_keys == 0 and header_as_keys:
        # Case where keys are only in header and each column becomes a list
        for row in map(list, zip(*datalist)):  # transpose the list
            key, value = row[0], row[1:]
            # If all of the data is numeric, set as numpy array
            if all([type(d) is int for d in value]):
                value = _np.array(value, dtype=int)
            elif all([(type(d) is int) or (type(d) is float) for d in value]):
                value = _np.array(value, dtype=float)
            datadict[key] = value
    else:
        # Case where each row also contains a key and header may also contain keys
        headerkeys = datalist[0][num_columns_as_keys:] if header_as_keys else None
        startrow = 1 if header_as_keys else 0

        for row in datalist[startrow:]:
            maplist = row[:num_columns_as_keys]
            values = row[num_columns_as_keys:]

            if header_as_keys:
                for headerkey, value in zip(headerkeys, values):
                    setdict_with_list(datadict, maplist + [headerkey], value)
            else:
                setdict_with_list(datadict, maplist, values[0] if len(values) == 1 else values)

    return freeze_recursivedict(datadict)


def is_strint(s):
    """
    Checks to see if a string is an integer.

    Args:
        s (string)

    Returns:
        Boolean
    """
    try:
        int(s)
        return True
    except ValueError:
        return False


def is_iterable(some_object):
    """
    Checks to see if an object is iterable.

    Args:
        s (string)

    Returns:
        Boolean
    """
    try:
        iter(some_object)
        return True
    except:
        return False


def is_strnumeric(s):
    """
    Checks to see if a string is numeric.

    Args:
        s (string)

    Returns:
        Boolean
    """
    try:
        float(s)
        return True
    except ValueError:
        return False


def is_strtrue(s):
    """
    Checks to see if a string is true or t.

    Args:
        s (string)

    Returns:
        Boolean
    """
    if s.lower() == 'true' or s.lower() == 't':
        return True
    else:
        return False


def is_strdate(s, dateformat):
    """
    Checks to see if a string matches a datetime format.

    Args:
        s (string)
        dateformat (string): format as used by python Datetime in strptime

    Returns:
        Boolean

    Example:

    """
    try:
        _datetime.strptime(s, dateformat)
        return True
    except:
        return False


def is_strbool(s):
    """
    Checks to see if a string is true, t, false, or f.

    Args:
        s (string)

    Returns:
        Boolean
    """
    if is_strtrue(s) or is_strfalse(s):
        return True
    else:
        return False


def is_strfalse(s):
    """
    Checks to see if a string is false or f.

    Args:
        s (string)

    Returns:
        Boolean
    """
    if s.lower() == 'false' or s.lower() == 'f':
        return True
    else:
        return False


def csvreader(path):
    """Returns a generator that yields one line of a file at a time

    Function uses csv.Sniffer to determine file format
    """
    with open(path, 'r') as infile:
        for row in _csv.reader(infile, delimiter=','):
            yield row


def filereader(path):
    """Returns a generator that yields one line of a file at a time

    Function uses csv.Sniffer to determine file format
    """
    with open(path, 'r') as infile:
        try:
            dialect = _csv.Sniffer().sniff(infile.read(1024))
        except:
            infile.seek(0)
            dialect = _csv.Sniffer().sniff(infile.read(10024))
        infile.seek(0)
        for row in _csv.reader(infile, dialect):
            yield row


def filewriter(path, buffering=-1):
    """Creates new text file."""
    if sys.version_info[0] >= 3:
        return open(path, 'w', newline='', buffering=buffering)
    else:
        return open(path, 'wb', buffering=buffering)


def csvwriter(path):
    """Creates new CSV file."""
    return _csv.writer(filewriter(path))


def parserow(row, stripwhitespace=True, removerowblanks=False):
    """Parse row takes a list of strings and sets datatypes

    Datatyping is done in a specific order:
        1. First, white space is deleted and blanks are removed
        2. Next, the data is made an integer if possible
        3. Next, the data is made a floating point number if possible
        4. Next, the data is made a boolean if possible
        5. Next, the data is made a Date object if possible
        6. Next, the data is made a Datetime object if possible
        7. Next, is the string 'None'
        8. Otherwise, the data is left as a string

    dateformats = ["%m/%d/%Y"]

    datetimeformats = ["%Y-%m-%d %H:%M:%S"]

    Args:
        row (list): list of strings to parse
        removeblanks (bool): remove empty strings. Defaults to False.

    Returns:
        list: the list after data has been parsed

    Example:
        >>> print parserow(['2010-01-01 00:00:00', '1/4/1950', 'my_data.csv',
        >>> '1', '1.0', 'true', 't', ''])
        [datetime.datetime(2010, 1, 1, 0, 0), datetime.date(1950, 1, 4),
        'my_data.csv', 1, 1.0, True, True]

    """
    if not is_iterable(row):
        raise TypeError(str(type(row)) + " is not iterable")
    # remove blanks and strip white space
    if stripwhitespace:
        row = [s.rstrip().lstrip() for s in row]

    # replace integers
    newdata = [int(d) if is_strint(d) else nd for nd, d in zip(row, row)]
    # replace floats
    newdata = [
        float(d) if (is_strnumeric(d) and not is_strint(d)) else nd
        for nd, d in zip(newdata, row)
    ]
    # replace booleans
    newdata = [
        is_strtrue(d) if is_strbool(d) else nd for nd, d in zip(newdata, row)
    ]

    # replace dates with Datetime
    def parsedate(d, dateformats, datetimeformats):
        for dformat in dateformats + datetimeformats:
            if is_strdate(d, dformat):
                if dformat in dateformats:
                    return _datetime.strptime(d, dformat).date()
                else:
                    return _datetime.strptime(d, dformat)

    dateformats, datetimeformats = ["%m/%d/%Y"], ["%Y-%m-%d %H:%M:%S"]
    newdata = [
        parsedate(d, dateformats, datetimeformats) if parsedate(
            d, dateformats, datetimeformats) else nd
        for nd, d in zip(newdata, row)
    ]

    newdata = [
        None if isinstance(d, str) and d.lower() == 'none' else d
        for d in newdata
    ]

    return newdata


def rstrip_blank_columns(list_of_lists):
    """
    Args:
        list_of_lists: a list of lists, which should be square

    Returns:
        a list of lists where columns at the end that are all blank have been removed
    """
    transpose = list(map(list, zip(*list_of_lists)))
    column_is_blank = [all([r == '' for r in row]) for row in transpose]
    if all(column_is_blank):
        raise ValueError('all columns are blank')
    column_cutoff = len(transpose) - column_is_blank[-1::-1].index(False)
    return [r[:column_cutoff] for r in list_of_lists]


def flatten_list(list_to_flatten):
    """
    Collapse a list of lists into a single list
    """
    return [item for sublist in list_to_flatten for item in sublist]


def recursivedict():
    """recursivedict creates a dictionary of any depth"""
    return _defaultdict(recursivedict)


def setdict_with_list(dictionary, maplist, value):
    """
    Allows setting a key in a dictionary from a list
    where each value in the list is one layer deeper

    Args:
        recursivedict (recursivedict): dictionary where value will be set
        maplist (list): list of keys where each key is a dictionary layer
        value (object): value to assign to the dictionary

    """
    getdict_with_list(dictionary, maplist[:-1])[maplist[-1]] = value


def getdict_with_list(dictionary, maplist):
    """Retrieve from a dictionary using a list where each item is a layer"""
    return reduce(lambda d, k: d[k], maplist, dictionary)


def freeze_recursivedict(recursivedict):
    recursivedict = dict(recursivedict)
    for key, value in recursivedict.items():
        if isinstance(value, _defaultdict):
            recursivedict[key] = freeze_recursivedict(value)
    return recursivedict
