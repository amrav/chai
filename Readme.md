# Chai

A command line tool to help book tickets on the Indian Railways.

## Dependencies

    pip install bs4 grequests

## Usage

    python chai.py [-h] [-v] {optimize, avail} ...

Use `-h` to get help with any command.

## Example

    > python chai.py avail -t 12802 -s NDLS -d KGP -D 30 -m 4
	RAC3/RAC 3
    > python chai.py optimize -t 12802 -s NDLS -d KGP -D 30 -m 4
    Fetching stations on route... done.
    Using up to 100 concurrent connections.
    Fetching availibility... 100%
	Optimum plan is:
	NDLS  -->  CNB ( 1  stations ) : AVAILABLE 33
	CNB  -->  KGP ( 19  stations ) : AVAILABLE 3
