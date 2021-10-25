import os, json

FILE_NAME = "utils.py"
INFO = "[INFO]["+ FILE_NAME +"] - " 
DEBUG = os.getenv('DEBUG','')

def get_toolkit_credentials(CONFIG_FILES_DIR):
    toolkit_credentials = None
    if os.path.isfile(CONFIG_FILES_DIR + "/toolkit-creds.json"):
        with open(CONFIG_FILES_DIR + "/toolkit-creds.json") as f:
            toolkit_credentials = json.load(f)
    else:
        toolkit_credentials = {}
    return toolkit_credentials

def get_env_config(CONFIG_FILES_DIR):
    env_config = None
    if os.path.isfile(CONFIG_FILES_DIR + "/config.json"):
        with open(CONFIG_FILES_DIR + "/config.json") as f:
            env_config = json.load(f)
    else:
        env_config = {}
    return env_config

def pretty_print_request(req):
    """
    At this point it is completely built and ready
    to be fired; it is "prepared".

    However pay attention at the formatting used in 
    this function because it is programmed to be pretty 
    printed and may differ from the actual request.
    """
    print(INFO + "---------- Request start ----------")
    print(INFO + req.method + ' ' + req.url)
    for k, v in req.headers.items():
        print(INFO + '{}: {}'.format(k, v))
    print(INFO, req.body)
    print(INFO + "---------- Request end ----------")