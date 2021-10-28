import os, json
import utils
import api_calls

"""

API Connect v10 post install configuration steps --> https://www.ibm.com/docs/en/api-connect/10.0.x?topic=environment-cloud-manager-configuration-checklist

"""

FILE_NAME = "config_apicv10.py"
DEBUG = os.getenv('DEBUG','')

def info(step):
    return "[INFO]["+ FILE_NAME +"][STEP " + str(step) + "] - " 

try:

######################################################################################
# Step 1 - Get the IBM API Connect Toolkit credentials and environment configuration #
######################################################################################

    print(info(1) + "######################################################################################")
    print(info(1) + "# Step 1 - Get the IBM API Connect Toolkit credentials and environment configuration #")
    print(info(1) + "######################################################################################")

    toolkit_credentials = utils.get_toolkit_credentials(os.environ["CONFIG_FILES_DIR"])
    environment_config = utils.get_env_config(os.environ["CONFIG_FILES_DIR"])
    if DEBUG:
        print(info(1) + "These are the IBM API Connect Toolkit Credentials")
        print(info(1) + "-------------------------------------------------")
        print(info(1), json.dumps(toolkit_credentials, indent=4, sort_keys=False))
        print(info(1) + "These is the environment configuration")
        print(info(1) + "--------------------------------------")
        print(info(1), json.dumps(environment_config, indent=4, sort_keys=False))

##################################################################
# Step 2 - Get the IBM API Connect Cloud Management Bearer Token #
##################################################################

    print(info(2) + "##################################################################")
    print(info(2) + "# Step 2 - Get the IBM API Connect Cloud Management Bearer Token #")
    print(info(2) + "##################################################################")
    
    admin_bearer_token = api_calls.get_bearer_token(environment_config["APIC_ADMIN_URL"],
                                                    "admin",
                                                    environment_config["APIC_ADMIN_PASSWORD"],
                                                    "admin/default-idp-1",
                                                    toolkit_credentials["toolkit"]["client_id"],
                                                    toolkit_credentials["toolkit"]["client_secret"])
    if DEBUG:
        print(info(2) + "This is the Bearer Token to work against the IBM API Connect Cloud Management endpoints")
        print(info(2) + "--------------------------------------------------------------------------------------")
        print(info(2), admin_bearer_token)

#################################
# Step 3 - Get the Admin org ID #
#################################

    print(info(3) + "#################################")
    print(info(3) + "# Step 3 - Get the Admin org ID #")
    print(info(3) + "#################################")
    
    url = 'https://' + environment_config["APIC_ADMIN_URL"] + '/api/cloud/orgs'

    response = api_calls.make_api_call(url, admin_bearer_token, 'get')
    
    found = False
    admin_org_id = ''
    if response.status_code != 200:
          raise Exception("Return code for getting the Admin org ID isn't 200. It is " + str(response.status_code))
    for org in response.json()['results']:
        if org['org_type'] == "admin":
            found = True
            admin_org_id = org['id']
    if not found:
        raise Exception("[ERROR] - The Admin Organization was not found in the IBM API Connect Cluster instance")
    if DEBUG:
        print(info(3) + "Admin Org ID: " + admin_org_id)

####################################
# Step 4 - Create the Email Server #
####################################

    print(info(4) + "####################################")
    print(info(4) + "# Step 4 - Create the Email Server #")
    print(info(4) + "####################################")
    
    url = 'https://' + environment_config["APIC_ADMIN_URL"] + '/api/orgs/' + admin_org_id + '/mail-servers'
    
    # Create the data object
    data = {}
    data['title'] = 'Default Email Server'
    data['name'] = 'default-email-server'
    data['host'] = os.environ['EMAIL_HOST']
    data['port'] = int(os.environ['EMAIL_PORT'])
    credentials = {}
    credentials['username'] = os.environ['EMAIL_USERNAME']
    credentials['password'] = os.environ['EMAIL_PASSWORD']
    data['credentials'] = credentials
    data['tls_client_profile_url'] = None
    data['secure'] = False

    if DEBUG:
        print(info(4) + "This is the data object:")
        print(info(4), data)
        print(info(4) + "This is the JSON dump:")
        print(info(4), json.dumps(data))

    response = api_calls.make_api_call(url, admin_bearer_token, 'post', data)

    if response.status_code != 201:
          raise Exception("Return code for creating the Email Server isn't 201. It is " + str(response.status_code))
    email_server_url = response.json()['url']
    if DEBUG:
        print(info(4) + "Email Server url: " + email_server_url)

##################################################
# Step 5 - Sender and Email Server Configuration #
##################################################

    print(info(5) + "##################################################")
    print(info(5) + "# Step 5 - Sender and Email Server Configuration #")
    print(info(5) + "##################################################")

    url = 'https://' + environment_config["APIC_ADMIN_URL"] + '/api/cloud/settings'
    
    # Create the data object
    # Ideally this would also be loaded from a sealed secret
    data = {}
    data['mail_server_url'] = email_server_url
    email_sender = {}
    email_sender['name'] = 'APIC Administrator'
    email_sender['address'] = 'test@test.com'
    data['email_sender'] = email_sender

    if DEBUG:
        print(info(5) + "This is the data object:")
        print(info(5), data)
        print(info(5) + "This is the JSON dump:")
        print(info(5), json.dumps(data))

    response = api_calls.make_api_call(url, admin_bearer_token, 'put', data)

    if response.status_code != 200:
          raise Exception("Return code for Sender and Email Server configuration isn't 200. It is " + str(response.status_code))

####################################################
# Step 6 - Register Gateway and Analytics Services #
####################################################

    print(info(6) + "####################################################")
    print(info(6) + "# Step 6 - Register Gateway and Analytics Services #")
    print(info(6) + "####################################################")

    print(info('6A') + "######################################")
    print(info('6A') + "# Step 6A - Get common configuration #")
    print(info('6A') + "######################################")

    # Array of Availability Zones
    gtw_a7s_azs = environment_config["GTW_A7S_AZS"].split(',')
    print(info('6A') + "Availability Zones: ", gtw_a7s_azs)
    # Replace spaces with '-' for the raw data in the call
    gtw_a7s_azs_formated = environment_config["GTW_A7S_AZS"].replace(" ","-").split(',')
    gtw_a7s_domains = environment_config["GTW_A7S_DOMAINS"].strip().split(',')
    print(info('6A') + "Domains: ", gtw_a7s_domains)

    # Get the Datapower API Gateway integration endpoint

    url = 'https://' + environment_config["APIC_ADMIN_URL"] + '/api/cloud/integrations/gateway-service/datapower-api-gateway'

    response = api_calls.make_api_call(url, admin_bearer_token, 'get')

    if response.status_code != 200:
        raise Exception("Return code for getting the Datapower API Gateway integration endpoint isn't 200. It is " + str(response.status_code))

    datapower_api_gateway_url = response.json()['url']
    if DEBUG:
        print(info(6) + "DataPower API Gateway url: " + datapower_api_gateway_url)

    # Second, we need to get the TLS server profiles

    url = 'https://' + environment_config["APIC_ADMIN_URL"] + '/api/orgs/' + admin_org_id + '/tls-server-profiles'

    response = api_calls.make_api_call(url, admin_bearer_token, 'get')

    found = False
    tls_server_profile_url = ''
    if response.status_code != 200:
        raise Exception("Return code for getting the TLS server profiles isn't 200. It is " + str(response.status_code))
    for profile in response.json()['results']:
        if profile['name'] == "tls-server-profile-default":
            found = True
            tls_server_profile_url = profile['url']
    if not found:
        raise Exception("[ERROR] - The default TLS server profile was not found in the IBM API Connect Cluster instance")

    if DEBUG:
        print(info(6) + "Default TLS server profile url: " + tls_server_profile_url)

    # Third, we need to get the TLS client profiles

    url = 'https://' + environment_config["APIC_ADMIN_URL"] + '/api/orgs/' + admin_org_id + '/tls-client-profiles'

    response = api_calls.make_api_call(url, admin_bearer_token, 'get')

    found = False
    tls_client_profile_url = ''
    if response.status_code != 200:
        raise Exception("Return code for getting the TLS client profiles isn't 200. It is " + str(response.status_code))
    for profile in response.json()['results']:
        if profile['name'] == "gateway-management-client-default":
            found = True
            tls_client_profile_url = profile['url']
    if not found:
        raise Exception("[ERROR] - The Gateway Management TLS client profile was not found in the IBM API Connect Cluster instance")

    if DEBUG:
        print(info(6) + "Gateway Management TLS server profile url: " + tls_client_profile_url)


    # We need to store the different Gateway Service IDs to associate these with the Sandbox catalog
    gateway_service_id = []

    for availability_zone in range(len(gtw_a7s_azs)):
    
    ##################################################
    # Step 6B - Register the Default Gateway Service #
    ##################################################

        print(info('6B') + "######################################")
        print(info('6B') + "# Step 6B - Create Availability Zone #")
        print(info('6B') + "######################################")

        url = 'https://' + environment_config["APIC_ADMIN_URL"] + '/api/orgs/' + admin_org_id + '/availability-zones'
        
        data = {}
        data['title'] = gtw_a7s_azs[availability_zone]
        data['name'] = gtw_a7s_azs_formated[availability_zone].lower()
        data['summary'] = ''

        if DEBUG:
            print(info('6B') + "This is the data object:")
            print(info('6B'), data)
            print(info('6B') + "This is the JSON dump:")
            print(info('6B'), json.dumps(data))

        response = api_calls.make_api_call(url, admin_bearer_token, 'post', data)

        if response.status_code != 201:
            raise Exception("Return code for creating the availability zone" + gtw_a7s_azs[availability_zone] + " isn't 201. It is " + str(response.status_code))

    ######################################
    # Step 6C - Register Gateway Service #
    ######################################

        print(info('6C') + "######################################")
        print(info('6C') + "# Step 6C - Register Gateway Service #")
        print(info('6c') + "######################################")


        # REST call to get the Gateway Service registered

        url = 'https://' + environment_config["APIC_ADMIN_URL"] + '/api/orgs/' + admin_org_id + '/availability-zones/' + gtw_a7s_azs_formated[availability_zone].lower() + '/gateway-services'
        
        # Create the data object
        data = {}
        data['name'] = gtw_a7s_azs_formated[availability_zone].lower() + "-gtw-svc"
        data['title'] = gtw_a7s_azs[availability_zone] + " Gateway Service"
        data['summary'] = gtw_a7s_azs[availability_zone] + " Gateway Service"
        data['endpoint'] = 'https://gwmanager.' + gtw_a7s_domains[availability_zone]
        data['api_endpoint_base'] = 'https://gw.' + gtw_a7s_domains[availability_zone]
        data['tls_client_profile_url'] = tls_client_profile_url
        data['gateway_service_type'] = 'datapower-api-gateway'
        visibility = {}
        visibility['type'] = 'public'
        data['visibility'] = visibility
        sni = []
        sni_inner={}
        sni_inner['host'] = '*'
        sni_inner['tls_server_profile_url'] = tls_server_profile_url
        sni.append(sni_inner)
        data['sni'] = sni
        data['integration_url'] = datapower_api_gateway_url

        if DEBUG:
            print(info('6c') + "This is the data object:")
            print(info('6c'), data)
            print(info('6c') + "This is the JSON dump:")
            print(info('6c'), json.dumps(data))

        response = api_calls.make_api_call(url, admin_bearer_token, 'post', data)

        if response.status_code != 201:
            raise Exception("Return code for registering the " + gtw_a7s_azs[availability_zone] + "Gateway Service isn't 201. It is " + str(response.status_code))

        # This will be needed in the last step when we associate this Gateway Service to the Sandbox catalog
        gateway_service_id.append(response.json()['id'])
        if DEBUG:
            print(info('6C') + gtw_a7s_azs[availability_zone] + " Gateway Service ID: " + gateway_service_id[-1])

    ############################################
    # Step 6D - Register the Analytics Service #
    ############################################

        print(info('6D') + "###################################################")
        print(info('6D') + "# Step 6D - Register the Default Analytics Service #")
        print(info('6D') + "###################################################")

        url = 'https://' + environment_config["APIC_ADMIN_URL"] + '/api/orgs/' + admin_org_id + '/availability-zones/' + gtw_a7s_azs_formated[availability_zone].lower() + '/analytics-services'
        
        # Create the data object
        data = {}
        data['name'] = gtw_a7s_azs_formated[availability_zone].lower() + "-a7s-svc"
        data['title'] = gtw_a7s_azs[availability_zone] + " Analytics Service"
        data['summary'] = gtw_a7s_azs[availability_zone] + " Analytics Service"
        data['endpoint'] = 'https://ac.' + gtw_a7s_domains[availability_zone]

        if DEBUG:
            print(info('6D') + "This is the data object:")
            print(info('6D'), data)
            print(info('6D') + "This is the JSON dump:")
            print(info('6D'), json.dumps(data))

        response = api_calls.make_api_call(url, admin_bearer_token, 'post', data)

        if response.status_code != 201:
            raise Exception("Return code for registering the " + gtw_a7s_azs[availability_zone] + " Analytics Service isn't 201. It is " + str(response.status_code))

        analytics_service_url = response.json()['url']
        if DEBUG:
            print(info('6D') + gtw_a7s_azs[availability_zone] + " Analytics Service url: " + analytics_service_url)

    ##############################################################
    # Step 6E - Associate Analytics Service with Gateway Service #
    ##############################################################

        print(info('6E') + "##############################################################")
        print(info('6E') + "# Step 6E - Associate Analytics Service with Gateway Service #")
        print(info('6E') + "##############################################################")

        url = 'https://' + environment_config["APIC_ADMIN_URL"] + '/api/orgs/' + admin_org_id + '/availability-zones/' + gtw_a7s_azs_formated[availability_zone].lower() + '/gateway-services/' + gtw_a7s_azs_formated[availability_zone].lower() + '-gtw-svc'
        
        # Create the data object
        data = {}
        data['analytics_service_url'] = analytics_service_url

        if DEBUG:
            print(info('6E') + "This is the data object:")
            print(info('6E'), data)
            print(info('6E') + "This is the JSON dump:")
            print(info('6E'), json.dumps(data))

        response = api_calls.make_api_call(url, admin_bearer_token, 'patch', data)

        if response.status_code != 200:
            raise Exception("Return code for associating the  " + gtw_a7s_azs[availability_zone] + " Analytics Service with the " + gtw_a7s_azs[availability_zone] + " Gateway Service isn't 200. It is " + str(response.status_code))

################################################
# Step 7 - Register the Default Portal Service #
################################################

    print(info(7) + "################################################")
    print(info(7) + "# Step 7 - Register the Default Portal Service #")
    print(info(7) + "################################################")

    url = 'https://' + environment_config["APIC_ADMIN_URL"] + '/api/orgs/' + admin_org_id + '/availability-zones/availability-zone-default/portal-services'
    
    # Create the data object
    data = {}
    data['title'] = "Default Portal Service"
    data['name'] = "default-portal-service"
    data['summary'] = "Default Portal Service that comes out of the box with API Connect Cluster v10"
    data['endpoint'] = 'https://' + environment_config["APIC_PORTAL_DIRECTOR_URL"]
    data['web_endpoint_base'] = 'https://' + environment_config["APIC_PORTAL_WEB_URL"]
    visibility = {}
    visibility['group_urls'] = None
    visibility['org_urls'] = None
    visibility['type'] = 'public'
    data['visibility'] = visibility

    if DEBUG:
        print(info(7) + "This is the data object:")
        print(info(7), data)
        print(info(7) + "This is the JSON dump:")
        print(info(7), json.dumps(data))

    response = api_calls.make_api_call(url, admin_bearer_token, 'post', data)

    if response.status_code != 201:
          raise Exception("Return code for registering the Default Portal Service isn't 201. It is " + str(response.status_code))

###########################################
# Step 8 - Create a Provider Organization #
###########################################

    print(info(8) + "###########################################")
    print(info(8) + "# Step 8 - Create a Provider Organization #")
    print(info(8) + "###########################################")

    # First, we need to get the user registries so that we can create a new user who will be the Provider Organization Owner

    url = 'https://' + environment_config["APIC_ADMIN_URL"] + '/api/cloud/settings/user-registries'

    response = api_calls.make_api_call(url, admin_bearer_token, 'get')

    if response.status_code != 200:
          raise Exception("Return code for retrieving the user registries isn't 200. It is " + str(response.status_code))
    
    provider_user_registry_default_url = response.json()['provider_user_registry_default_url']
    if DEBUG:
        print(info(8) + "Default Provider User Registry url: " + provider_user_registry_default_url)

    # Then, we need to register the user that will be the Provider Organization owner

    url = provider_user_registry_default_url + '/users'

    # Create the data object
    # Ideally this should be loaded from a sealed secret.
    # Using defaults for now.
    data = {}
    data['username'] = os.environ["PROV_ORG_OWNER_USERNAME"]
    data['email'] = os.environ["PROV_ORG_OWNER_EMAIL"]
    data['first_name'] = os.environ["PROV_ORG_OWNER_FIRST_NAME"]
    data['last_name'] = os.environ["PROV_ORG_OWNER_LAST_NAME"]
    data['password'] = os.environ["PROV_ORG_OWNER_PASSWORD"]

    if DEBUG:
        print(info(8) + "This is the data object:")
        print(info(8), data)
        print(info(8) + "This is the JSON dump:")
        print(info(8), json.dumps(data))

    response = api_calls.make_api_call(url, admin_bearer_token, 'post', data)

    if response.status_code != 201:
          raise Exception("Return code for registering the provider organization owner user isn't 201. It is " + str(response.status_code))
    
    owner_url = response.json()['url']
    if DEBUG:
        print(info(8) + "Provider Organization Owner url: " + owner_url)
    
    # Finally, we can create the Provider Organization with the previous owner

    url = 'https://' + environment_config["APIC_ADMIN_URL"] + '/api/cloud/orgs'

    # Create the data object
    # Ideally this should be loaded from a sealed secret.
    # Using defaults for now.
    data = {}
    data['title'] = os.environ["PROV_ORG_TITLE"]
    data['name'] = os.environ["PROV_ORG_NAME"]
    data['owner_url'] = owner_url

    if DEBUG:
        print(info(8) + "This is the data object:")
        print(info(8), data)
        print(info(8) + "This is the JSON dump:")
        print(info(8), json.dumps(data))

    response = api_calls.make_api_call(url, admin_bearer_token, 'post', data)

    if response.status_code != 201:
          raise Exception("Return code for creating the provider organization isn't 201. It is " + str(response.status_code))

##############################################################
# Step 9 - Get the IBM API Connect Provider API Bearer Token #
##############################################################

    print(info(9) + "##############################################################")
    print(info(9) + "# Step 9 - Get the IBM API Connect Provider API Bearer Token #")
    print(info(9) + "##############################################################")
    
    # Ideally, the username and password for getting the Bearer Token below would come from a sealed secret (that woul also be used
    # in the previous step 10 when registering the new user for the provider organization owner)
    # Using defaults for now.
    admin_bearer_token = api_calls.get_bearer_token(environment_config["APIC_API_MANAGER_URL"],
                                                    "testorgadmin",
                                                    "passw0rd",
                                                    "provider/default-idp-2",
                                                    toolkit_credentials["toolkit"]["client_id"],
                                                    toolkit_credentials["toolkit"]["client_secret"])
    if DEBUG:
        print(info(9) + "This is the Bearer Token to work against the IBM API Connect API Management endpoints")
        print(info(9) + "-------------------------------------------------------------------------------------")
        print(info(9), admin_bearer_token)

#########################################################################
# Step 10 - Associate Default Gateway Services with the Sandbox catalog #
#########################################################################

    print(info(10) + "#########################################################################")
    print(info(10) + "# Step 10 - Associate Default Gateway Services with the Sandbox catalog #")
    print(info(10) + "#########################################################################")

    # First, we need to get the organization ID

    url = 'https://' + environment_config["APIC_API_MANAGER_URL"] + '/api/orgs'

    response = api_calls.make_api_call(url, admin_bearer_token, 'get')
    
    found = False
    provider_org_id = ''
    if response.status_code != 200:
          raise Exception("Return code for getting the Provider Org ID isn't 200. It is " + str(response.status_code))
    for org in response.json()['results']:
        if org['org_type'] == "provider":
            found = True
            provider_org_id = org['id']
    if not found:
        raise Exception("[ERROR] - The Provider Organization was not found in the IBM API Connect Cluster instance")
    if DEBUG:
        print(info(10) + "Provider Org ID: " + provider_org_id)

    # Then, we need to get the Sandbox catalog ID

    url = 'https://' + environment_config["APIC_API_MANAGER_URL"] + '/api/orgs/' + provider_org_id + '/catalogs'

    response = api_calls.make_api_call(url, admin_bearer_token, 'get')
    
    found = False
    catalog_id = ''
    if response.status_code != 200:
          raise Exception("Return code for getting the Sandbox catalog ID isn't 200. It is " + str(response.status_code))
    for catalog in response.json()['results']:
        if catalog['name'] == os.environ["PROV_ORG_CATALOG_NAME"]:
            found = True
            catalog_id = catalog['id']
    if not found:
        raise Exception("[ERROR] - The Sandbox catalog was not found in the IBM API Connect Cluster instance")
    if DEBUG:
        print(info(10) + "Sandbox catalog ID: " + catalog_id)

    # Finally, we can associate the Default Gateway Service to the Sandbox catalog

    url = 'https://' + environment_config["APIC_API_MANAGER_URL"] + '/api/catalogs/' + provider_org_id + '/' + catalog_id + '/configured-gateway-services'

    for gateway_service in gateway_service_id:

        # Create the data object
        gateway_service_url = 'https://' + environment_config["APIC_API_MANAGER_URL"] + '/api/orgs/' + provider_org_id + '/gateway-services/' + gateway_service
        data = {}
        data['gateway_service_url'] = gateway_service_url

        if DEBUG:
            print(info(10) + "This is the data object:")
            print(info(10), data)
            print(info(10) + "This is the JSON dump:")
            print(info(10), json.dumps(data))

        response = api_calls.make_api_call(url, admin_bearer_token, 'post', data)

        if response.status_code != 201:
            raise Exception("Return code for associating the Gateway Service with ID " + gateway_service + " to the Sandbox catalog isn't 201. It is " + str(response.status_code))

#######
# END #
#######

    print("#######")
    print("# END #")
    print("#######")

except Exception as e:
    raise Exception("[ERROR] - Exception in " + FILE_NAME + ": " + repr(e))