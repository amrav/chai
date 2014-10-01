import requests
import re
from bs4 import BeautifulSoup as bs
import sys
import copy
import os
import inspect

# hack to include grequests from http://stackoverflow.com/a/6098238/1448759
cmd_subfolder = os.path.realpath(os.path.abspath(os.path.join(os.path.split(inspect.getfile( inspect.currentframe() ))[0],"grequests")))
if cmd_subfolder not in sys.path:
    sys.path.insert(0, cmd_subfolder)
import grequests

session = grequests.Session()
session.mount('http://', requests.adapters.HTTPAdapter(max_retries=10))

def scrape_avail(html):
    soup = bs(html)
    avail_str = ''
    avail_str = soup.select('tr.heading_table_top')[1].find_next_siblings('tr')[0].find_all('td')[2].text.strip()
    return avail_str

def scrape_stations_list(html):
    soup = bs(html)
    stations = []
    offsets = []
    for row in soup.select("tr.heading_table_top")[1].find_next_siblings('tr'):
        stations.append(row.select('td')[1].text.strip())
        offsets.append(int(row.select('td')[8].text.strip()) - 1)
    return {'names': stations, 'offsets': offsets}

def is_avail(avail_str):
    return (re.match(r"AVAILABLE|RAC", avail_str) != None)


AVAIL_URI = 'http://www.indianrail.gov.in/cgi_bin/inet_accavl_cgi.cgi'
SCHEDULE_URI = 'http://www.indianrail.gov.in/cgi_bin/inet_trnnum_cgi.cgi'

# IRCTC specific header and param names
params = {
    'lccp_trnno' : '12860',
    'lccp_day' : '4',
    'lccp_month': '2',
    'lccp_srccode': 'BSP',
    'lccp_dstncode': 'R',
    'lccp_class1': '3A', # or SL or 2A or 1A
    'lccp_quota': 'CK', # or GN
    'submit': 'Please+Wait...',
    'lccp_classopt': 'ZZ',
    'lccp_class2': 'ZZ',
    'lccp_class3': 'ZZ',
    'lccp_class4': 'ZZ',
    'lccp_class5': 'ZZ',
    'lccp_class6': 'ZZ',
    'lccp_class7': 'ZZ',
    'lccp_trnname': '22811',
    'getIt': 'Please+Wait...',
}

headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.9; rv:26.0) Gecko/20100101 Firefox/26.0',
    'Host': 'www.indianrail.gov.in',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Accept-Encoding': 'gzip, deflate',
    'Referer': 'http://www.indianrail.gov.in/seat_Avail.html'
}

def get_avail(train_no, src, dst, day, month, class_, quota, offset = 0):

    day = int(day)
    month = int(month)

    (day, month) = correct_date(day, month, offset)

    params['lccp_trnno'] = train_no
    params['lccp_srccode'] = src
    params['lccp_dstncode'] = dst
    params['lccp_class1'] = class_
    params['lccp_quota'] = quota
    params['lccp_day'] = day
    params['lccp_month'] = month
    headers['Referer'] = 'http://www.indianrail.gov.in/seat_Avail.html'
    headers['Content-Type'] = 'application/x-www-form-urlencoded1; charset=UTF-8;'
    r = requests.post(AVAIL_URI, data=params, headers=headers)
    try:
        return scrape_avail(r.text)
    except IndexError:
        print "Error: Couldn't get availability. Aborting."
        sys.exit(1)

def correct_date(day, month, offset):
    days_in_month = 30
    if (month == 1 or
        month == 3 or
        month == 5 or
        month == 7 or
        month == 8 or
        month == 10 or
        month == 12):
        days_in_month = 31
    elif (month == 2):
        days_in_month = 28
    if (day + offset > days_in_month):
        month += 1
        if (month > 12):
            month -= 12
    day += offset
    if (day > days_in_month):
        day -= days_in_month
    return (day, month)

def get_stations(train_no):
    params['lccp_trnname'] = train_no
    headers['Referer'] = 'http://www.indianrail.gov.in/train_Schedule.html'
    r = requests.post(SCHEDULE_URI, data=params,
                      headers=headers)
    try:
        return scrape_stations_list(r.text)
    except IndexError:
        print "Error: Couldn't get stations list. Aborting."
        sys.exit(1)

def print_progress(p, prompt='', text=''):
    sys.stdout.write("\r" + " " * (len(prompt) + len(text) + len(str(p))) +
                 "\r%s%d%%%s" %(prompt, p, text))
    sys.stdout.flush()

def get_all_avail(train_no, day, month, class_, quota, stations=None, concurrency=100):
    if (stations == None):
        sys.stdout.write("Getting stations...")
        sys.stdout.flush()
        stations = irctc.get_stations(train_no)
        print " done."
    names = stations['names']
    rs = []

    # hack because Python has weak closures
    response_counter = [0]
    response_tot = (len(names) * (len(names) - 1)) / 2

    def on_response(day, month, src, dst, avail):
        def _on_response(response, response_counter=response_counter, *args, **kwargs):
            response_counter[0] += 1
            print_progress(response_counter[0] * 100 / response_tot,
                           prompt="Fetching availability... ")
            if (src not in avail):
                avail[src] = {}
            try:
                avail[src][dst] = scrape_avail(response.text)
            except IndexError:
                print "\nWarning: Couldn't detect availability for %s/%s from %s to %s" %(day, month, src, dst)
                avail[src][dst] = "UNAVAILABLE"
        return _on_response

    failedRequests = []
    def exception_handler(request, exception, failedRequests=failedRequests):
        failedRequests.append(request)

    avail = {}
    print "Using up to", concurrency, "concurrent connections."
    for i in range(len(names) - 1):
        for j in range(i + 1, len(names)):
            (c_day, c_month) = correct_date(int(day), int(month), stations['offsets'][i])
            params['lccp_trnno'] = train_no
            params['lccp_srccode'] = names[i]
            params['lccp_dstncode'] = names[j]
            params['lccp_class1'] = class_
            params['lccp_quota'] = quota
            params['lccp_day'] = c_day
            params['lccp_month'] = c_month
            headers['Referer'] = 'http://www.indianrail.gov.in/seat_Avail.html'
            headers['Content-Type'] = 'application/x-www-form-urlencoded1; charset=UTF-8;'
            rs.append(
                grequests.post(
                    AVAIL_URI,
                    data=copy.copy(params),
                    headers=copy.copy(headers),
                    hooks=dict(response=on_response(day=c_day,
                                                      month=c_month,
                                                      src=names[i],
                                                      dst=names[j],
                                                      avail=avail))
                ))
    grequests.map(rs, size=concurrency, exception_handler=exception_handler)

    while len(failedRequests) != 0:
        print "\nWarning: Retrying %d failed requests." % len(failedRequests)
        requests = copy.copy(failedRequests)
        del failedRequests[:]
        grequests.map(requests, size=concurrency, exception_handler=exception_handler)

    print
    return avail
