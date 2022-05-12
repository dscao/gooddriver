'''
Support for gooddriver.cn 优驾联网版
Author        : dscao
Github        : https://github.com/dscao
Description   : 
Date          : 2022-05-11
LastEditors   : dscao
LastEditTime  : 2022-05-12
'''
"""
name: 'gooddriver'
id: '123456'
api_key: '6928FAA6-B970-F5A5-85F0-XXXXXXXXXXXX'
    
Component to integrate with 优驾联网版.

For more details about this component, please refer to
https://github.com/dscao/gooddriver
"""
import logging
import asyncio
import json
import time, datetime
import requests
import re

from aiohttp.client_exceptions import ClientConnectorError
from async_timeout import timeout

from dateutil.relativedelta import relativedelta 
import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.components.sensor import PLATFORM_SCHEMA
#from bs4 import BeautifulSoup

from requests import ReadTimeout, ConnectTimeout, HTTPError, Timeout, ConnectionError
from datetime import timedelta
import homeassistant.util.dt as dt_util
from homeassistant.components import zone
from homeassistant.components.device_tracker import PLATFORM_SCHEMA
from homeassistant.components.device_tracker.const import CONF_SCAN_INTERVAL
from homeassistant.components.device_tracker.legacy import DeviceScanner

from homeassistant.core import Config, HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from homeassistant.helpers.event import async_track_time_interval
from homeassistant.util import slugify
from homeassistant.helpers.event import track_utc_time_change
from homeassistant.util import slugify
from homeassistant.util.location import distance

from homeassistant.const import (
    CONF_NAME,
    CONF_API_KEY,
    ATTR_GPS_ACCURACY,
    ATTR_LATITUDE,
    ATTR_LONGITUDE,
    STATE_HOME,
    STATE_NOT_HOME,
    MAJOR_VERSION, 
    MINOR_VERSION,
)

from .const import (
    CONF_USER_ID,
    COORDINATOR,
    DOMAIN,
    UNDO_UPDATE_LISTENER,
    CONF_ATTR_SHOW,
    CONF_UPDATE_INTERVAL,
)

TYPE_GEOFENCE = "Geofence"
__version__ = '2022.5.12'

_LOGGER = logging.getLogger(__name__)   
    
PLATFORMS = ["device_tracker"]

USER_AGENT = 'gooddriver/7.8.0 CFNetwork/1220.1 Darwin/20.3.0'
API_URL = "http://restcore.gooddriver.cn/API/Values/HudDeviceDetail/" 
          
async def async_setup(hass: HomeAssistant, config: Config) -> bool:
    """Set up configured gooddriver."""
    # if (MAJOR_VERSION, MINOR_VERSION) < (2022, 4):
        # _LOGGER.error("Minimum supported Hass version 2022.4")
        # return False
    hass.data.setdefault(DOMAIN, {})
    return True

async def async_setup_entry(hass, config_entry) -> bool:
    """Set up gooddriver as config entry."""
    user_id = config_entry.data[CONF_USER_ID]
    api_key = config_entry.data[CONF_API_KEY]
    update_interval_seconds = config_entry.options.get(CONF_UPDATE_INTERVAL, 90)
    attr_show = config_entry.options.get(CONF_ATTR_SHOW, True)
    location_key = config_entry.unique_id

    _LOGGER.debug("Using location_key: %s, user_id: %s, update_interval_seconds: %s", location_key, user_id, update_interval_seconds)

    websession = async_get_clientsession(hass)

    coordinator = gooddriverDataUpdateCoordinator(
        hass, websession, api_key, user_id, location_key, update_interval_seconds
    )
    await coordinator.async_refresh()

    if not coordinator.last_update_success:
        raise ConfigEntryNotReady

    undo_listener = config_entry.add_update_listener(update_listener)

    hass.data[DOMAIN][config_entry.entry_id] = {
        COORDINATOR: coordinator,
        UNDO_UPDATE_LISTENER: undo_listener,
    }

    for component in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(config_entry, component)
        )

    return True

async def async_unload_entry(hass, config_entry):
    """Unload a config entry."""
    unload_ok = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(config_entry, component)
                for component in PLATFORMS
            ]
        )
    )

    hass.data[DOMAIN][config_entry.entry_id][UNDO_UPDATE_LISTENER]()

    if unload_ok:
        hass.data[DOMAIN].pop(config_entry.entry_id)

    return unload_ok


async def update_listener(hass, config_entry):
    """Update listener."""
    await hass.config_entries.async_reload(config_entry.entry_id)


class gooddriverDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching gooddriver data API."""

    def __init__(self, hass, session, api_key, user_id, location_key, update_interval_seconds):
        """Initialize."""
        self.location_key = location_key
        self.user_id = user_id
        self.api_key = api_key

        
        update_interval = (
            datetime.timedelta(seconds=int(update_interval_seconds))
        )
        _LOGGER.debug("Data will be update every %s", update_interval)

        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=update_interval)

    # @asyncio.coroutine
    def get_data(self, url, headerstr):
        json_text = requests.get(url, headers=headerstr).content
        json_text = json_text.decode('utf-8')
        json_text = re.sub(r'\\','',json_text)
        json_text = re.sub(r'"{','{',json_text)
        json_text = re.sub(r'}"','}',json_text)
        resdata = json.loads(json_text)
        return resdata
        
    def post_data(self, url, headerstr, datastr):
        json_text = requests.post(url, headers=headerstr, data = datastr).content
        json_text = json_text.decode('utf-8')
        json_text = re.sub(r'\\','',json_text)
        json_text = re.sub(r'"{','{',json_text)
        json_text = re.sub(r'}"','}',json_text)
        resdata = json.loads(json_text)
        return resdata
        

    async def _async_update_data(self):
        """Update data via library."""
        try:
            async with timeout(10): 
                headers = {
                            'Host': 'restcore.gooddriver.cn',
                            'SDF': self.api_key,
                            'Accept': '\*/\*',
                            'User-Agent': USER_AGENT,
                            'Accept-Language': 'zh-cn',
                            'Accept-Encoding': 'gzip, deflate',
                            'Connection': 'keep-alive'
                            }
                url = str.format(API_URL + self.user_id)
                # json_text = requests.get(url,).content
                resdata =  await self.hass.async_add_executor_job(self.get_data, url, headers)
        except (
            ClientConnectorError
        ) as error:
            raise UpdateFailed(error)
        _LOGGER.debug("Requests remaining: %s", url)
        return {**resdata,"location_key":self.location_key}

