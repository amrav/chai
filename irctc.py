import requests
import re
from bs4 import BeautifulSoup as bs
import grequests
import sys
import copy

class IrctcParser:

    @classmethod
    def scrape_avail(self, html):
        soup = bs(html)
        avail_str = ''
        avail_str = soup.select('tr.heading_table_top')[1].find_next_siblings('tr')[0].find_all('td')[2].text.strip()
        return avail_str

    @classmethod
    def scrape_stations_list(self, html):
        soup = bs(html)
        stations = []
        offsets = []
        for row in soup.select("tr.heading_table_top")[1].find_next_siblings('tr'):
            stations.append(row.select('td')[1].text.strip())
            offsets.append(int(row.select('td')[8].text.strip()) - 1)
        return {'names': stations, 'offsets': offsets}

    @classmethod
    def is_avail(self, avail_str):
        return (re.match(r"AVAILABLE|RAC", avail_str) != None)

class IrctcClient:

    __AVAIL_URI = 'http://www.indianrail.gov.in/cgi_bin/inet_accavl_cgi.cgi'
    __SCHEDULE_URI = 'http://www.indianrail.gov.in/cgi_bin/inet_trnnum_cgi.cgi'

    # IRCTC specific header and param names
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

    @classmethod
    def get_avail(self, train_no, src, dst, day, month, class_, quota, offset = 0):

        day = int(day)
        month = int(month)

        (day, month) = self.__correct_date(day, month, offset)

        self.__params['lccp_trnno'] = train_no
        self.__params['lccp_srccode'] = src
        self.__params['lccp_dstncode'] = dst
        self.__params['lccp_class1'] = class_
        self.__params['lccp_quota'] = quota
        self.__params['lccp_day'] = day
        self.__params['lccp_month'] = month
        self.__headers['Referer'] = 'http://www.indianrail.gov.in/seat_Avail.html'
        self.__headers['Content-Type'] = 'application/x-www-form-urlencoded1; charset=UTF-8;'
        r = requests.post(self.__AVAIL_URI, data=self.__params, headers=self.__headers)
        try:
            return IrctcParser.scrape_avail(r.text)
        except IndexError:
            print "Error: Couldn't get availability. Aborting."
            sys.exit(1)

    @classmethod
    def __correct_date(self, day, month, offset):
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

    @classmethod
    def get_stations(self, train_no):
        self.__params['lccp_trnname'] = train_no
        self.__headers['Referer'] = 'http://www.indianrail.gov.in/train_Schedule.html'
        r = requests.post(self.__SCHEDULE_URI, data=self.__params,
                          headers=self.__headers)
        try:
            return IrctcParser.scrape_stations_list(r.text)
        except IndexError:
            print "Error: Couldn't get stations list. Aborting."
            sys.exit(1)

    @classmethod
    def __print_progress(self, p, prompt='', text=''):
        sys.stdout.write("\r" + " " * (len(prompt) + len(text) + len(str(p))) +
                     "\r%s%d%%%s" %(prompt, p, text))
        sys.stdout.flush()

    @classmethod
    def __on_response(self, day, month, src, dst, avail):
        def on_response(response, *args, **kwargs):
            self.__response_counter += 1
            self.__print_progress(self.__response_counter * 100 / self.__response_tot,
                           prompt="Fetching availability... ")
            if (src not in avail):
                avail[src] = {}
            try:
                avail[src][dst] = IrctcParser.scrape_avail(response.text)
            except IndexError:
                print "\nWarning: Couldn't detect availability for %s/%s from %s to %s" %(day, month, src, dst)
                avail[src][dst] = "UNAVAILABLE"
        return on_response

    __response_counter = 0
    __response_tot = 1

    @classmethod
    def get_all_avail(self, train_no, day, month, class_, quota, stations=None, concurrency=100):
        if (stations == None):
            sys.stdout.write("Getting stations...")
            sys.stdout.flush()
            stations = irctc.get_stations(train_no)
            print " done."
        names = stations['names']
        rs = []
        self.__response_counter = 0
        self.__response_tot = (len(names) * (len(names) - 1)) / 2
        avail = {}
        print "Using up to", concurrency, "concurrent connections."
        for i in range(len(names) - 1):
            for j in range(i + 1, len(names)):
                (c_day, c_month) = self.__correct_date(int(day), int(month), stations['offsets'][i])
                self.__params['lccp_trnno'] = train_no
                self.__params['lccp_srccode'] = names[i]
                self.__params['lccp_dstncode'] = names[j]
                self.__params['lccp_class1'] = class_
                self.__params['lccp_quota'] = quota
                self.__params['lccp_day'] = c_day
                self.__params['lccp_month'] = c_month
                self.__headers['Referer'] = 'http://www.indianrail.gov.in/seat_Avail.html'
                self.__headers['Content-Type'] = 'application/x-www-form-urlencoded1; charset=UTF-8;'
                rs.append(
                    grequests.post(
                        self.__AVAIL_URI,
                        data=copy.copy(self.__params),
                        headers=copy.copy(self.__headers),
                        hooks=dict(response=self.__on_response(day=c_day,
                                                          month=c_month,
                                                          src=names[i],
                                                          dst=names[j],
                                                          avail=avail))))
        responses = grequests.map(rs, size=concurrency)
        print
        return avail
