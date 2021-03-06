## Purpose: provide a generic service for testing API calls
## Author : Simon Li
## Date   : May 5, 2020
## hostname refer settings.json in .vscode folder
##
## Usage:  
## import TTDataService
## ttdata = TTDataService("108.48.52.183")
from pprint import pprint 
import pandas as pd
import numpy as np
import os
import requests
import json
import time 
from datetime import datetime
import logging
from requests.auth import HTTPBasicAuth

class TTDataService:
    def __init__(self):
        '''
            TTDataService: ()
        '''
        # self.__url = url
        # "http://%s:%d" % (host, port)
        self.__url = None
        self.__appkey = None

    @staticmethod
    def getUrl(base, route):
        '''
           make a url string
           In : base(str), route(str)
           Out: url(str) 
        '''
        url = base
        if route[0] != '/':
           url += '/' + route
        else:
            url += route
        return url
    
    @staticmethod
    def JSONParseIfPossible(text):
        '''
           JSON parse the string to dict if possible
           In : text(str)
           Out: a dict or original string
        '''
        try: 
            result = json.loads(text) 
        except:
            result = text
        return result

    @property
    def url(self):
        return self.__url

    @property
    def appkey(self):
        return self.__appkey

    @appkey.setter
    def appkey(self, appkey):
        self.__appkey = appkey

    @property
    def json(self):
        '''
           expose json 
        '''
        return json

    @property
    def requests(self):
        '''
           expose requests 
        '''
        return requests

    @url.setter
    def url(self, url):
        self.__url = url
    
    def get(self, route):
        '''
           GET request
           In :  route(str), e.g. /getshareddata?data_type=2&device_id=ttdata
           Out: tuple(int, dict/str)
        '''
        url = TTDataService.getUrl(self.__url, route)

        if self.__appkey:  # Use the auth if we have one
            response = requests.get(url, headers={'appkey': self.__appkey})
        else:
            response = requests.get(url)
        return (response)

    def post(self, route, payload):
        '''
           POST request
           In : route(str), payload(dict or json string)
           Out: tuple(int, dict/str)
        '''
        url = TTDataService.getUrl(self.__url, route)
        if isinstance(payload, dict):
            if self.__appkey:
                response = requests.post(url, json=payload, headers={'appkey': self.__appkey})
            else:
                response = requests.post(url, json=payload)
        else:
            try:
                if self.__appkey:
                	response = requests.post(url, json=payload, headers={'appkey': self.__appkey})
                else:
                    response = requests.post(url, json=json.loads(payload))
            except:
                if self.__appkey:
                	response = requests.post(url, data=payload, headers={'appkey': self.__appkey})
                else:    
                	response = requests.post(url, data=payload)  

        #response.status_code, TTDataService.JSONParseIfPossible(response.text)
        return (response)

def transform_names(df):
    '''
       need to have standard names
    '''
    df.columns = [x.lower() for x in df.columns]
    df.rename(columns={'province/state': 'province_state',
                   'admin2'            : 'county',
                   'country/region'    : 'country_region',
                   'last update'       : 'last_update',
                   "long_":          "longitude",
                   "long":          "longitude",
                   "lat":           "latitude",
                   "lat_":           "latitude",
                  }, inplace=True)
    
    if ("combined_key" in df.columns):
       df.drop(columns=['combined_key'], inplace=True)
       
    keycolumn = "country_region|province_state|date"

    if ("county" in df.columns):
        keycolumn = "country_region|province_state|county|date"
  
    return (df, keycolumn)

def covid19data_to_ttdata(pre_did, source_file, data_date, blocksize, num_batches):
    print("processing: ", source_file)
    logging.info("processing: " + source_file)
    df = pd.read_csv(source_file, dtype = {'FIPS': str, 'ZIP': str, "ZIP_CODE": str})
    df, key = transform_names(df)
    #errorCount = 0    

    totalsize = df.shape[0]
    batches =[list(range(i, min(i+blocksize, totalsize))) for i in range(0,totalsize,blocksize) ]

    run_num_batches = 0
    reg_num = 0
    for aBatch in batches:
        run_num_batches += 1
        if (run_num_batches > num_batches) :
            break
        json_data_list = []
        for i in aBatch:
            row = df.iloc[i]
            #row_as_dic = row.to_dict()
            device_data = {"date":data_date }
            device_data.update(json.loads(row.to_json()))
            json_data_list.append(device_data)

        logging.info("For batch from: %d to %d" % (aBatch[0], aBatch[-1]))        
        print("\nFor batch from: ", aBatch[0], ", to:", aBatch[-1])
        payload = {
             "data_type": 2, 
             "device_id": pre_did, #+ "-" + str(reg_num),
             "key" : key,
             "device_data": json_data_list                
              }
        #print(payload)
        #ttdata.appkey = appkey
        response = ttdata.post("/uploaddata", payload)
        logging.info(response.elapsed.total_seconds())
        logging.info(response.status_code)
        logging.info(response.text)
        print(response.elapsed.total_seconds())
        print(response.status_code)
        print(response.text)
        reg_num += 1
        #time.sleep(waitsec)
    
    return int(totalsize / blocksize)
        
def check_status(stage,response):    
    if (response.ok):
        logging.info(stage + ": pass")
        print(stage + ": pass")
    else: 
        logging.info(stage + ": failed")
        print(stage, ": failed")
        #TODO send sms to the system admin

def check_covid19_upload(did, blocksize, num_batches):
    github_root = "https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_daily_reports"
    #blocksizeNum = 200
    #waitsecNum = 0
    file = github_root + "/05-17-2020" + ".csv"
    ts = time.time()
    
    #didNum =
    covid19data_to_ttdata(did, source_file= file, 
                            data_date = "2020-05-09", 
                            blocksize = blocksize,
                            num_batches = num_batches)
    te = time.time()

    logging.info('%s  %2.2f sec' % ("uploaddata", (te - ts) ))
    print('%s  %2.2f sec' % ("uploaddata", (te - ts)))
    logging.info("== /getshareddata ==")
    print("\n== /getshareddata ==")

    #for i in range(didNum):
    ts = time.time()   
    response = ttdata.get("/getshareddata?data_type={0}&device_id={1}".format(2, did))
    
    check_status("getshareddata", response)
    te = time.time()
    logging.info('%s  %2.2f sec' % ("getshareddata", (te - ts) ))

def register(did):
    payload = {
                "device_id": did,
                "category": "TEST"
            }
    response = ttdata.post("/register", payload)
    appkey = json.loads(response.text)["data"]
    return(appkey)


def check_reg_upload_getdata(did):
    print("== /register ==")
    appkey = register(did)
    print(appkey)
    #check_status("register", appkey)
    # Upload data
    print("\n== /uploaddata ==")
    #headers = {"Accept": "application/json"}
    #auth = HTTPBasicAuth("appkey", appkey )
    payload = {
                "data_type": 2, 
                "device_id": did, 
                "key": "date|province_state|county|country_region",
                "device_data": [{
                                    "date": "2020-05-09", 
                                    "province_state": "ON",
                                    "country_region": "Canada", 
                                    "county": "Toronto",
                                    "last_update": "2020-05-03T10:43:02",
                                    "confirmed":370,
                                    "deaths": 84,
                                    "recovered": 14,
                                    "latitude":43.6532,
                                    "longitude": 79.3832	
                }]   
    }
    # Set the appkey for authorization
    ttdata.appkey = appkey
    response = ttdata.post("/uploaddata", payload)
    #print(json.dumps(payload))
    print(response)
    check_status("uploaddata", response)
    # Get shared data
    print("\n== /getshareddata ==")
    response = ttdata.get("/getshareddata?data_type={0}&device_id={1}".format(2, did))
    print(response)
    check_status("getshareddata", response)

if __name__ == '__main__':
    host_url = 'http://ixinbuy.com:7061'
    #host_url = 'http://192.168.1.196:7061'

    #create a log file
    timestr = datetime.now().strftime("%Y%m%d")    
    log_fname = 'log_' + timestr
    log_filename = 'logs/'+log_fname
    logging.basicConfig(filename=log_filename, level=logging.INFO, format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')
    
    logging.info('starting ttdataTestingScript.py ...')
    logging.info('using ' + host_url)
    print(host_url)
    appkey = ""
    ttdata = TTDataService()
    ttdata.url = host_url    

    #create a new device_id before run
    device_id = "test-ttdata-20200610"
    check_reg_upload_getdata(device_id)

    # Register
    logging.info("== /covid19 with 32 ids==")
    print("\n== /covid19 with 32 ids==")

    #using the 3rd para to define blocksize
    #using the 4th para to define how many blocks you want to upload, 
    #   0 means for none
    #   any number larger than totalsize of the data / blocksize means for all
    # 
    check_covid19_upload(device_id, 200, 9999)

    
    

    