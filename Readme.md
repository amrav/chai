# Chai

A command line tool to help book tickets on the Indian Railways.

## Installation

Use `virtualenv` to install packages locally rather than globally.

```
$ pip install -r requirements.txt
```

## Usage

```
chai.py [-h] [-v] -t TRAIN_NO -s SRC -d DST -D DAY -m MONTH
               [-c {1A,2A,3A,SL,CC}] [-q {GN,CK}]
               {avail,optimize} ...

positional arguments:
  {avail,optimize}      sub-command help
    avail               find availability between two stations
    optimize            calculate the best possible route to take between two
                        stations

optional arguments:
  -h, --help            show this help message and exit
  -v, --verbose         turn on verbose mode
  -t TRAIN_NO, --train_no TRAIN_NO
                        train number
  -s SRC, --src SRC     source station code
  -d DST, --dst DST     destination station code
  -D DAY, --day DAY     day of travel (dd)
  -m MONTH, --month MONTH
                        month of travel (mm)
  -c {1A,2A,3A,SL,CC}, --class {1A,2A,3A,SL,CC}
                        class of travel
  -q {GN,CK}, --quota {GN,CK}
                        class code
```

## Example

```
$ python chai.py -t 12802 -s NDLS -d KGP -D 30 -m 4 avail
RAC3/RAC 3

$ python chai.py -t 12802 -s NDLS -d KGP -D 30 -m 4 optimize
Fetching stations on route... done.
Using up to 100 concurrent connections.
Fetching availability... 100%
Optimum plan is:
NDLS  -->  CNB ( 1  stations ) : AVAILABLE 33
CNB  -->  KGP ( 19  stations ) : AVAILABLE 3
```
