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
from aiohttp.client_exceptions import ClientConnectorError
from async_timeout import timeout
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

__version__ = '0.1.1'
_Log=logging.getLogger(__name__)

COMPONENT_REPO = 'https://github.com/dscao/gooddriver/'
DEFAULT_SCAN_INTERVAL = timedelta(seconds=30)
ICON = 'mdi:car'

DEFAULT_NAME = 'gooddriver'
ID = 'id'
KEY = 'key'

laststoptime = "未知"
lastlat = "未知"
lastlon = "未知"
runorstop = "未知"

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
    
    def get_data(self, url, headerstr):
        json_text = requests.get(url, headers=headerstr).content
        json_text = json_text.decode('utf-8')
        json_text = re.sub(r'\\','',json_text)
        json_text = re.sub(r'"{','{',json_text)
        json_text = re.sub(r'}"','}',json_text)
        resdata = json.loads(json_text)
        return resdata    
    
    async def async_start(self, hass, interval):
        """Perform a first update and start polling at the given interval."""
        await self.async_update_info()
        interval = max(interval, DEFAULT_SCAN_INTERVAL)
        async_track_time_interval(hass, self.async_update_info, interval)             
            
    
    async def async_update_info(self, now=None):
        """Get the gps info."""
        global laststoptime
        global lastlat
        global lastlon
        global runorstop
        HEADERS = {
            'Host': 'restcore.gooddriver.cn',
            'SDF': self._key,
            'Accept': '\*/\*',
            'User-Agent': 'gooddriver/7.8.0 CFNetwork/1220.1 Darwin/20.3.0',
            'Accept-Language': 'zh-cn',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive'
            }
        
        try:
            async with timeout(10):                
                ret =  await self.hass.async_add_executor_job(self.get_data, self._url, HEADERS)
                _Log.debug("请求结果: %s", ret)
        except (
            ClientConnectorError
        ) as error:
            raise UpdateFailed(error)
        _Log.debug("Requests remaining: %s", self._url)
        
        if ret['ERROR_CODE'] == 0:
            _Log.info("请求服务器信息成功.....") 
            
            if ret['MESSAGE']['HD_STATE'] == 1:
                status = "车辆点火"
            elif ret['MESSAGE']['HD_STATE'] == 2:
                status = "车辆熄火"
            else:
                status = "未知"
                
            if ret['MESSAGE']['HD_RECENT_LOCATION']['Lat'] == lastlat and ret['MESSAGE']['HD_RECENT_LOCATION']['Lng'] == lastlon and runorstop == "运动":
                laststoptime = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                runorstop = "静止"
            elif ret['MESSAGE']['HD_RECENT_LOCATION']['Lat'] != lastlat or ret['MESSAGE']['HD_RECENT_LOCATION']['Lng'] != lastlon:
                lastlat = ret['MESSAGE']['HD_RECENT_LOCATION']['Lat']
                lastlon = ret['MESSAGE']['HD_RECENT_LOCATION']['Lng']
                runorstop = "运动"
                
            def time_diff (timestamp):
                result = datetime.datetime.now() - datetime.datetime.fromtimestamp(timestamp)
                hours = int(result.seconds / 3600)
                minutes = int(result.seconds % 3600 / 60)
                seconds = result.seconds%3600%60
                if result.days > 0:
                    return("{0}天{1}小时{2}分钟".format(result.days,hours,minutes))
                elif hours > 0:
                    return("{0}小时{1}分钟".format(hours,minutes))
                elif minutes > 0:
                    return("{0}分钟{1}秒".format(minutes,seconds))
                else:
                    return("{0}秒".format(seconds))
            
                
            kwargs = {
                "dev_id": slugify("gddr_{}".format(self._name)),
                "host_name": self._name,                
                "attributes": {
                    "icon": ICON,
                    "status": status,
                    "querytime": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "laststoptime": laststoptime,
                    "statustime": ret['MESSAGE']['HD_STATE_TIME'], 
                    "time": ret['MESSAGE']['HD_RECENT_LOCATION']['Time'],
                    "speed": ret['MESSAGE']['HD_RECENT_LOCATION']['Speed'],
                    "course": ret['MESSAGE']['HD_RECENT_LOCATION']['Course'],
                    "runorstop": runorstop,
                    "Parking_time": time_diff (int(time.mktime(time.strptime(ret['MESSAGE']['HD_RECENT_LOCATION']['Time'], "%Y-%m-%d %H:%M:%S")))),
                    },
                }
            kwargs["gps"] = [
                    ret['MESSAGE']['HD_RECENT_LOCATION']['Lat'] + 0.00240,
                    ret['MESSAGE']['HD_RECENT_LOCATION']['Lng'] - 0.00540,
                ]
            if status == "车辆点火":
                interval = 10
            else:
                interval = 60
       
        else:
            _Log.error("send request error....")
            

        result = await self.async_see(**kwargs)
        return result
