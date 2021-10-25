import os, json
import requests
from urllib3.util import Retry
from requests.adapters import HTTPAdapter
import utils

FILE_NAME = "api_calls.py"
INFO = "[INFO]["+ FILE_NAME +"] - " 
DEBUG = os.getenv('DEBUG','')

def get_bearer_token(apic_url, apic_username, apic_password, apic_realm, apic_rest_clientid, apic_rest_clientsecret): 

    try:
        url = "https://" + apic_url + "/api/token"
        reqheaders = {
            "Content-Type" : "application/json",
            "Accept" : "application/json"
        }

        reqJson = {
            "username": apic_username,
            "password": apic_password,
            "realm": apic_realm,
            "client_id": apic_rest_clientid,
            "client_secret": apic_rest_clientsecret,
            "grant_type": "password"
        }
        if DEBUG:
          print(INFO + "Get Bearer Token")
          print(INFO + "----------------")
          print(INFO + "Url:", url)
          print(INFO + "Username:", apic_username)
          print(INFO + "Client ID:", apic_rest_clientid)
        s = requests.Session()
        retries = Retry(total=3, backoff_factor=1, status_forcelist=[ 500, 502, 503, 504 ])
        s.mount(url, HTTPAdapter(max_retries=retries))
        response = s.post(url, headers=reqheaders, json=reqJson, verify=False, timeout=20)
        resp_json = response.json()
        if DEBUG:
          print(INFO + "This is the request made:")
          utils.pretty_print_request(response.request)
          print(INFO + "This is the response's status_code:", response.status_code)
          print(INFO + "This is the response in json:", resp_json)
        if response.status_code != 200:
          raise Exception("Return code for getting the Bearer token isn't 200. It is " + str(response.status_code))
        return resp_json['access_token']
    except Exception as e:
        raise Exception("[ERROR] - Exception in " + FILE_NAME + ": " + repr(e))

def make_api_call(url, bearer_token, verb, data=None):

    try:
        if data:
            reqheaders = {
                "Accept" : "application/json",
                "Content-Type" : "application/json",
                "Authorization" : "Bearer " + bearer_token
            }
        else:
           reqheaders = {
                "Accept" : "application/json",
                "Authorization" : "Bearer " + bearer_token
            } 
        s = requests.Session()
        retries = Retry(total=3, backoff_factor=1, status_forcelist=[ 502, 503, 504 ])
        s.mount(url, HTTPAdapter(max_retries=retries))

        if verb == "get":
            if data:
                response = s.get(url, headers=reqheaders, json=data, verify=False, timeout=300)
            else:
                response = s.get(url, headers=reqheaders, verify=False, timeout=300)
        if verb == "post":
            if data:
                response = s.post(url, headers=reqheaders, json=data, verify=False, timeout=300)
            else:
                response = s.post(url, headers=reqheaders, verify=False, timeout=300)
        if verb == "put":
            if data:
                response = s.put(url, headers=reqheaders, json=data, verify=False, timeout=300)
            else:
                response = s.put(url, headers=reqheaders, verify=False, timeout=300)
        if verb == "patch":
            if data:
                response = s.patch(url, headers=reqheaders, json=data, verify=False, timeout=300)
            else:
                response = s.patch(url, headers=reqheaders, verify=False, timeout=300)

        if DEBUG:
            print(INFO + "This is the request made:")
            utils.pretty_print_request(response.request)
            print(INFO + "This is the response's status_code", response.status_code)
            print(INFO + "This is the response in json", json.dumps(response.json(), indent=4, sort_keys=False))

    except Exception as e:
        raise Exception("[ERROR] - Exception in " + FILE_NAME + ": " + repr(e))

    return response