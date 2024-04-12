"""
Copyright start
MIT License
Copyright (c) 2024 Fortinet Inc
Copyright end
"""

import requests
from time import time, ctime
from datetime import datetime
from connectors.core.connector import get_logger, ConnectorError
from connectors.core.utils import update_connnector_config

logger = get_logger('polar-security')

CONFIG_SUPPORTS_TOKEN = True


class PolarSecurityAuth:

    def __init__(self, config):
        self.username = config.get("username")
        self.password = config.get("password")
        self.verify_ssl = config.get('verify_ssl')
        self.host = config.get("url").strip('/')
        if self.host[:7] == "http://":
            self.host = "https://{0}".format(self.host)
        elif self.host[:8] == "https://":
            self.host = "{0}".format(self.host)
        else:
            self.host = "https://{0}".format(self.host)
        

    def convert_ts_epoch(self, ts):
        datetime_object = datetime.strptime(ctime(ts), "%a %b %d %H:%M:%S %Y")
        return datetime_object.timestamp()

    def generate_token(self):
        try:
            token_resp = acquire_token(self)
            ts_now = time()
            token_resp['expiresOn'] = (ts_now + token_resp['expires_in']) if token_resp.get("expires_in") else None
            token_resp['accessToken'] = token_resp.get("access_token")
            token_resp.pop("access_token")
            return token_resp
        except Exception as err:
            logger.error("{0}".format(err))
            raise ConnectorError("{0}".format(err))

    def validate_token(self, connector_config, connector_info):
        try:
            ts_now = time()
            if not connector_config.get('accessToken'):
                logger.error('Error occurred while connecting server: Unauthorized')
                raise ConnectorError('Error occurred while connecting server: Unauthorized')
            expires = connector_config['expiresOn']
            expires_ts = self.convert_ts_epoch(expires)
            if ts_now > float(expires_ts):

                logger.info("Token expired at {0}".format(expires))

                token_resp = self.generate_token()
                connector_config['accessToken'] = token_resp['accessToken']
                connector_config['expiresOn'] = token_resp['expiresOn']
                update_connnector_config(connector_info['connector_name'], connector_info['connector_version'],
                                         connector_config,
                                         connector_config['config_id'])

                return "Bearer {0}".format(connector_config.get('accessToken'))
            else:
                logger.info("Token is valid till {0}".format(expires))
                return "Bearer {0}".format(connector_config.get('accessToken'))
        except Exception as err:
            logger.error("{0}".format(str(err)))
            raise ConnectorError("{0}".format(str(err)))


def acquire_token(self):
    try:
        data = {
            'username': self.username,
            'password': self.password
        }

        response = requests.post('{url}/auth'.format(url=self.host), data=data)
        if response.status_code in [200, 204, 201]:
            return response.json()

        else:
            if response.text != "":
                error_msg = ''
                err_resp = response.json()
                if err_resp and 'error' in err_resp:
                    failure_msg = err_resp.get('error_description')
                    error_msg = 'Response {0}: {1} \n Error Message: {2}'.format(response.status_code,
                                                                                 response.reason,
                                                                                 failure_msg if failure_msg else '')
                else:
                    err_resp = response.text
            else:
                error_msg = '{0}:{1}'.format(response.status_code, response.reason)
            raise ConnectorError(error_msg)

    except Exception as err:
        logger.error("{0}".format(str(err)))
        raise ConnectorError(error_msg)


def check(config, connector_info):
    try:
        polar_security_obj = PolarSecurityAuth(config)
        if CONFIG_SUPPORTS_TOKEN:
            if not 'accessToken' in config:
                token_resp = polar_security_obj.generate_token()
                config['accessToken'] = token_resp.get('accessToken')
                config['expiresOn'] = token_resp.get('expiresOn')
                update_connnector_config(connector_info['connector_name'], connector_info['connector_version'], config,
                                         config['config_id'])
                return True
            else:
                token_resp = polar_security_obj.validate_token(config, connector_info)
                return True
    except Exception as err:
        raise ConnectorError(str(err))
