#!/usr/bin/env python

import argparse
import requests
from bs4 import BeautifulSoup as bs
import re
import sys
import copy
import grequests

def main():
    p = argparse.ArgumentParser(description="A command line tool to help book tickets on the Indian Railways.")
    p.add_argument("-v", "--verbose", help="turn on verbose mode", action='store_false', dest='verbose', default=False)
    sp = p.add_subparsers(help="sub-command help")
    p_optimize = sp.add_parser('optimize', help="calculate the best possible route to take between two stations")
    p_optimize.add_argument("-t", "--train_no", help="train number", required=True, dest='train_no')
    p_optimize.add_argument("-s", "--src", help="source station code", required=True, dest='src')
    p_optimize.add_argument("-d", "--dst", help="destination station code", required=True, dest='dst')
    p_optimize.add_argument("-D", "--day", help="day of travel (dd)", required=True, dest='day')
    p_optimize.add_argument("-m", "--month", help="month of travel (mm)", required=True, dest='month')
    p_optimize.add_argument("-c", "--class", help="class of travel",
                            choices=['1A', '2A', '3A', 'SL', 'CC'], default='3A', dest='class_')
    p_optimize.add_argument("-q", "--quota", help="class code",
                            choices=['GN', 'CK'], default='GN', dest='quota')
    def __optimize(args):
        optimize(args.train_no, args.src, args.dst, args.day, args.month, args.class_, args.quota, args.verbose)
    p_optimize.set_defaults(func=__optimize)
    p_availability = sp.add_parser('avail', help="find availability between two stations")
    p_availability.add_argument("-t", "--train_no", help="train number", required=True)
    p_availability.add_argument("-s", "--src", help="source station code", required=True)
    p_availability.add_argument("-d", "--dst", help="destination station code", required=True)
    p_availability.add_argument("-D", "--day", help="day of travel (dd)", required=True)
    p_availability.add_argument("-m", "--month", help="month of travel (mm)", required=True)
    p_availability.add_argument("-c", "--class", help="class of travel",
                                choices=['1A', '2A', '3A', 'SL', 'CC'], default='3A', dest='class_')
    p_availability.add_argument("-q", "--quota", help="class code",
                                choices=['GN', 'CK'], default='GN')
    def __get_avail(args):
        print get_avail(args.train_no, args.src, args.dst, args.day, args.month, args.class_, args.quota)
    p_availability.set_defaults(func=__get_avail)
    args = p.parse_args()
    args.func(args)

AVAIL_URI = 'http://www.indianrail.gov.in/cgi_bin/inet_accavl_cgi.cgi'
schd_uri = 'http://www.indianrail.gov.in/cgi_bin/inet_trnnum_cgi.cgi'

# example params and headers, must set explicitly before sending request

__params = {
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

__headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.9; rv:26.0) Gecko/20100101 Firefox/26.0',
    'Host': 'www.indianrail.gov.in',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Accept-Encoding': 'gzip, deflate',
    'Referer': 'http://www.indianrail.gov.in/seat_Avail.html'
}

def __scrape_avail(html):
    soup = bs(html)
    avail_str = ''
    avail_str = soup.select('tr.heading_table_top')[1].find_next_siblings('tr')[0].find_all('td')[2].text.strip()
    return avail_str

def __scrape_stations_list(html):
    soup = bs(html)
    stations = []
    offsets = []
    for row in soup.select("tr.heading_table_top")[1].find_next_siblings('tr'):
        stations.append(row.select('td')[1].text.strip())
        offsets.append(int(row.select('td')[8].text.strip()) - 1)
    return {'names': stations, 'offsets': offsets}


def __correct_date(day, month, offset):
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

def get_avail(train_no, src, dst, day, month, class_, quota, offset = 0):

    day = int(day)
    month = int(month)

    (day, month) = __correct_date(day, month, offset)

    __params['lccp_trnno'] = train_no
    __params['lccp_srccode'] = src
    __params['lccp_dstncode'] = dst
    __params['lccp_class1'] = class_
    __params['lccp_quota'] = quota
    __params['lccp_day'] = day
    __params['lccp_month'] = month
    __headers['Referer'] = 'http://www.indianrail.gov.in/seat_Avail.html'
    __headers['Content-Type'] = 'application/x-www-form-urlencoded1; charset=UTF-8;'
    r = requests.post(AVAIL_URI, data=__params, headers=__headers)
    return __scrape_avail(r.text)

def get_stations(train_no):
    __params['lccp_trnname'] = train_no
    __headers['Referer'] = 'http://www.indianrail.gov.in/train_Schedule.html'
    r = requests.post(schd_uri, data=__params, headers=__headers)
    return __scrape_stations_list(r.text)

def is_avail(avail_str):
    return (re.match(r"AVAILABLE|RAC", avail_str) != None)

def print_nC2_avail(train_no, day, month, class_, quota):
    stations = get_stations(train_no)
    i = 0; j = 1
    last_avail = r"AVAILABLE"
    while True:
        avail_str = get_avail(train_no, stations['names'][i], stations['names'][j], day, month, class_, quota, stations['offsets'][i])
        if (re.match("AVAILABLE", avail_str)):
            last_avail = r"AVAILABLE"
        elif (re.match("RAC", avail_str)):
            last_avail = r"RAC"
        else:
            last_avail = r"foobar" # should not match with 'Regret' or 'WL'

        not_avail_flag = False

        while (re.match(last_avail, avail_str) != None or
               (last_avail == "foobar" and re.match("AVAILABLE", avail_str)) or
               (re.match("NOT AVAILABLE", avail_str) != None)):

            if (re.match("NOT AVAILABLE", avail_str) != None):
                not_avail_flag = True
            else:
                not_avail_flag = False
            print "Intermediate: ", "Day:", stations['offsets'][i] + 1, "\t", stations['names'][i], " - ", stations['names'][j], " : ",
            print get_avail(train_no, stations['names'][i], stations['names'][j], day, month, class_, quota, stations['offsets'][i])
            j += 1
            if j == len(stations['names']):
                break
            avail_str = get_avail(train_no, stations['names'][i], stations['names'][j], day, month, class_, quota, stations['offsets'][i])

        if i == j - 1:
            j += 1
        if (not_avail_flag):
                not_avail_flag = False
                j += 1
        print stations['names'][i], " - ", stations['names'][j-1], " : ",
        print get_avail(train_no, stations['names'][i], stations['names'][j-1], day, month, class_, quota, stations['offsets'][i])
        i = j-1
        if j == len(stations['names']):
            break

def get_optimum_segments(train_no, src, dst, day, month, class_, quota, avail = None, stations = None):
    if (avail == None):
        avail = {}
    if (src not in avail):
        avail[src] = {}
    if (stations == None):
        stations = get_stations(train_no)
    src_no = 0; dst_no = 0
    while (stations['names'][src_no] != src):
        src_no += 1
    while (stations['names'][dst_no] != dst):
        dst_no += 1
    print "Calculating segments for (", src_no + 1, ", ", dst_no + 1, ")"
    if (dst not in avail[src]):
        avail[src][dst] = get_avail(train_no, src, dst, day, month, class_, quota, stations['offsets'][src_no])
    print "avail for ", src, " and ", dst, " is ", avail[src][dst]
    if (dst_no - src_no < 5 or is_avail(avail[src][dst])):
        return [(src, dst, avail[src][dst])]
    else:
        possible_segmentations = []
        for i in range(src_no + 1, dst_no):
            possible_segmentations.append(
                get_optimum_segments(train_no, stations['names'][src_no], stations['names'][i],
                             day, month, class_, quota, avail, stations) +
                get_optimum_segments(train_no, stations['names'][i], stations['names'][dst_no],
                             day, month, class_, quota, avail, stations)
            )
        final_segmentation = possible_segmentations[0]
        min = len(possible_segmentations[0])
        print "Possibilities: "
        print possible_segmentations

        for candidate in possible_segmentations:
            if (len(candidate)) < min:
                final_segmentation = candidate
                min = len(candidate)
        print "Final segment: ", final_segmentation
        return final_segmentation

def print_progress(p, prompt='', text=''):
    sys.stdout.write("\r" + " " * (len(prompt) + len(text) + len(str(p))) +
                     "\r%s%d%%%s" %(prompt, p, text))
    sys.stdout.flush()

def __on_response(day, month, src, dst, avail):
    def on_response(response, *args, **kwargs):
        __on_response.counter += 1
        print_progress(__on_response.counter * 100 / __on_response.tot,
                       prompt="Fetching availability... ")
        if (src not in avail):
            avail[src] = {}
        try:
            avail[src][dst] = __scrape_avail(response.text)
        except IndexError:
            print "\nWarning: Couldn't detect availability for %s/%s from %s to %s" %(day, month, src, dst)
            avail[src][dst] = "UNAVAILABLE"
    return on_response

__on_response.counter = 0
__on_response.tot = 1

def __get_all_avail(train_no, day, month, class_, quota, stations=None, concurrency=100):
    if (stations == None):
        sys.stdout.write("Getting stations...")
        sys.stdout.flush()
        stations = get_stations(train_no)
        print " done."
    names = stations['names']
    rs = []
    __on_response.counter = 0
    __on_response.tot = (len(names) * (len(names) - 1)) / 2
    avail = {}
    print "Using up to", concurrency, "concurrent connections."
    for i in range(len(names) - 1):
        for j in range(i + 1, len(names)):
            (c_day, c_month) = __correct_date(int(day), int(month), stations['offsets'][i])
            __params['lccp_trnno'] = train_no
            __params['lccp_srccode'] = names[i]
            __params['lccp_dstncode'] = names[j]
            __params['lccp_class1'] = class_
            __params['lccp_quota'] = quota
            __params['lccp_day'] = c_day
            __params['lccp_month'] = c_month
            __headers['Referer'] = 'http://www.indianrail.gov.in/seat_Avail.html'
            __headers['Content-Type'] = 'application/x-www-form-urlencoded1; charset=UTF-8;'
            rs.append(
                grequests.post(
                    AVAIL_URI,
                    data=copy.copy(__params),
                    headers=copy.copy(__headers),
                    hooks=dict(response=__on_response(day=c_day,
                                                      month=c_month,
                                                      src=names[i],
                                                      dst=names[j],
                                                      avail=avail))))
    responses = grequests.map(rs, size=concurrency)
    print
    return avail

def __segment_cost(v1, v2, avail, names, indices):
    #if v1 is ahead of v2
    if (indices[v1] >= indices[v2]):
        return (0, 0, 10 * (indices[v1] - indices[v2]))
    elif re.match("AVAILABLE", avail[v1][v2]):
        return (0, 0, 1)
    elif re.match("RAC", avail[v1][v2]):
        return (0, 1, 0)
    wl = re.findall('/WL(\d+)', avail[v1][v2])
    if len(wl) == 1:
        return (int(wl[0]), indices[v2] - indices[v1], 0)
    else:
        return (1000, 0, 0)

def __cost_lt(cost1, cost2):
    for i in range(len(cost1)):
        if (cost1[i] < cost2[i]):
            return True
        elif (cost1[i] > cost2[i]):
            return False
    return False

def __cost_sum(cost1, cost2):
    return (cost1[0] + cost2[0], cost1[1] + cost2[1], cost1[2] + cost2[2])

def optimize(train_no, src, dst, day, month, class_, quota, verbose = False):
    sys.stdout.write("Fetching stations on route... ")
    sys.stdout.flush()
    stations = get_stations(train_no)
    print "done."
    names = stations['names']
    offsets = stations['offsets']
    indices = {}
    for i in range(len(names)):
        indices[names[i]] = i
    print "Stations found: ", indices
    src_no = indices[src]; dst_no = indices[dst]
    avail = __get_all_avail(train_no, day, month, class_, quota, stations)
    cost = {}
    cost[names[dst_no]] = {}
    previous = {}
    for i in range(src_no, len(names) - 1):
        cost[names[i]] = {}
        cost[names[i]][names[i]] = (0, 0, 0)
        for j in range(i + 1, len(names)):
            cost[names[i]][names[j]] = (float("inf"), 0, 0)
    for i in range(dst_no + 1, len(names)):
        if names[i] not in cost:
            cost[names[i]] = {}
        cost[names[i]][dst] = (float("inf"), 0, 0)
    for i in range(0, src_no):
        cost[src][names[i]] = (float("inf"), 0, 0)
        if names[i] not in cost:
            cost[names[i]] = {}
            for j in range(src_no + 1, len(names)):
                cost[names[i]][names[j]] = (float("inf"), 0, 0)
    for v1 in [src] + names[0:src_no] + names[src_no + 1:]:
        if (verbose):
            print "v1 = ", v1
        for v2 in cost[v1]:
            if (v1 == v2):
                continue
            if (verbose):
                print "v2 = ", v2
                print "segment cost =", __segment_cost(v1, v2, avail, names, indices),
                if v1 in cost[src]:
                    print "cost[%s][%s] = %s" %(src, v1, cost[src][v1]),
                if v2 in cost[src]:
                    print "cost[%s][%s] = %s" %(src, v2, cost[src][v2]),
            if __cost_lt(__cost_sum(__segment_cost(v1, v2, avail, names, indices), cost[src][v1]), cost[src][v2]):
                cost[src][v2] = __cost_sum(__segment_cost(v1, v2, avail, names, indices), cost[src][v1])
                previous[v2] = v1
            if (verbose):
                print "Final cost[%s][%s] =" %(src, v2), cost[src][v2]
    if (verbose):
        print "Cost from ", src, " to ", dst, " is ", cost[src][dst]
    optimum = [dst]
    currentVertex = dst
    while (currentVertex != src):
        currentVertex = previous[currentVertex]
        optimum.insert(0, currentVertex)
    print "Optimum plan is: "
    for i in range(len(optimum) - 1):
        print optimum[i], " --> ", optimum[i + 1],
        print "(", indices[optimum[i + 1]] - indices[optimum[i]], " stations )",
        if (indices[optimum[i+1]] > indices[optimum[i]]):
            print ":", avail[optimum[i]][optimum[i+1]]
        else:
            if indices[optimum[i+1]] < indices[src]:
                print ":", "Get on at %s" %optimum[i]
            else:
                print ":", "Get off at %s" %optimum[i+1]

if __name__ == '__main__':
    main()
