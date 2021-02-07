"""
Support for gooddriver.cn 优驾联网版
# Author:
    dscao
# Created:
    2021/1/28
device_tracker:    
  - platform: gddr
    name: 'gooddriver'
    id: '123456'
    api_key: '6928FAA6-B970-F5A5-85F0-XXXXXXXXXXXX'
"""
import logging
import asyncio
import json
import time, datetime
import requests
import re
from dateutil.relativedelta import relativedelta 
import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.components.sensor import PLATFORM_SCHEMA
from bs4 import BeautifulSoup
from requests import ReadTimeout, ConnectTimeout, HTTPError, Timeout, ConnectionError
from datetime import timedelta
import homeassistant.util.dt as dt_util
from homeassistant.components import zone
from homeassistant.components.device_tracker import PLATFORM_SCHEMA
from homeassistant.components.device_tracker.const import CONF_SCAN_INTERVAL
from homeassistant.components.device_tracker.legacy import DeviceScanner
from homeassistant.const import (
    CONF_NAME,
    ATTR_GPS_ACCURACY,
    ATTR_LATITUDE,
    ATTR_LONGITUDE,
    STATE_HOME,
    STATE_NOT_HOME,
)
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.util import slugify
from homeassistant.helpers.event import track_utc_time_change
from homeassistant.util import slugify
from homeassistant.util.location import distance


TYPE_GEOFENCE = "Geofence"

__version__ = '0.1.0'
_Log=logging.getLogger(__name__)

COMPONENT_REPO = 'https://github.com/dscao/gooddriver/'
DEFAULT_SCAN_INTERVAL = timedelta(seconds=30)
ICON = 'mdi:car'

DEFAULT_NAME = 'gooddriver'
ID = 'id'
KEY = 'key'

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
	vol.Required(ID): cv.string,
    vol.Required(KEY): cv.string,
    vol.Optional(CONF_NAME, default= DEFAULT_NAME): cv.string,
})


API_URL = "http://restcore.gooddriver.cn/API/Values/HudDeviceDetail/"


async def async_setup_scanner(hass, config, async_see, discovery_info=None):
    interval = config.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    sensor_name = config.get(CONF_NAME)
    id = config.get(ID)
    key = config.get(KEY)
    url = API_URL + id
    _Log.info("url:" + url + ";KEY:" + key )
    scanner = GddrDeviceScanner(hass, async_see, sensor_name, url, key)
    await scanner.async_start(hass, interval)
    return True


class GddrDeviceScanner(DeviceScanner):
    def __init__(self, hass, async_see, sensor_name: str, url: str, key: str):
        """Initialize the scanner."""
        self.hass = hass
        self.async_see = async_see
        self._name = sensor_name
        self._url = url
        self._key = key
        self._state = None
        self.attributes = {}
    
        
    
    async def async_start(self, hass, interval):
        """Perform a first update and start polling at the given interval."""
        await self.async_update_info()
        interval = max(interval, DEFAULT_SCAN_INTERVAL)
        async_track_time_interval(hass, self.async_update_info, interval)             
            
    
    async def async_update_info(self, now=None):
        """Get the gps info."""
        HEADERS = {
            'Host': 'restcore.gooddriver.cn',
            'SDF': self._key,
            'Accept': '\*/\*',
            'User-Agent': 'gooddriver/.7.1 CFNetwork/1209 Darwin/20.2.0',
            'Accept-Language': 'zh-cn',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive'
            }
        try:
            response = requests.get(self._url, headers = HEADERS)
        except ReadTimeout:
            _Log.error("Connection timeout....")
        except ConnectionError:
            _Log.error("Connection Error....")
        except RequestException:
            _Log.error("Unknown Error")
        '''_Log.info( response ) '''
        res = response.content.decode('utf-8')
        res = re.sub(r'\\','',res)
        res = re.sub(r'"{','{',res)
        res = re.sub(r'}"','}',res)
        _Log.debug(res)
        ret = json.loads(res, strict=False)
        
        if ret['ERROR_CODE'] == 0:
            _Log.info("请求服务器信息成功.....") 
            if ret['MESSAGE']['HD_STATE'] == 1:
                status = "车辆点火"
            elif ret['MESSAGE']['HD_STATE'] == 2:
                status = "车辆熄火"
            else:
                status = "未知"                          
            kwargs = {
                "dev_id": slugify("gddr_{}".format(self._name)),
                "host_name": self._name,                
                "attributes": {
                    "icon": ICON,
                    "status": status,
                    "statustime": ret['MESSAGE']['HD_STATE_TIME'],
                    "querytime": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "time": ret['MESSAGE']['HD_RECENT_LOCATION']['Time'],
                    "speed": ret['MESSAGE']['HD_RECENT_LOCATION']['Speed'],
                    "course": ret['MESSAGE']['HD_RECENT_LOCATION']['Course'],
                    },
                }
            kwargs["gps"] = [
                    ret['MESSAGE']['HD_RECENT_LOCATION']['Lat'] + 0.00240,
                    ret['MESSAGE']['HD_RECENT_LOCATION']['Lng'] - 0.00540,
                ]
       
        else:
            _Log.error("send request error....")
            

        result = await self.async_see(**kwargs)
        return result
