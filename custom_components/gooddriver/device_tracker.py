"""Support for the gooddriver service."""
import logging
import time, datetime
from datetime import datetime, timedelta

from homeassistant.components.device_tracker.config_entry import TrackerEntity
from homeassistant.helpers.device_registry import DeviceEntryType

#from homeassistant.helpers.entity import Entity

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
    MANUFACTURER,
    ATTR_SPEED,
    ATTR_COURSE,
    ATTR_STATUS,
    ATTR_RUNORSTOP,
    ATTR_LASTSTOPTIME,
    ATTR_UPDATE_TIME,
    ATTR_QUERYTIME,
    ATTR_PARKING_TIME,
)




PARALLEL_UPDATES = 1
_LOGGER = logging.getLogger(__name__)

laststoptime = "未知"
lastlat = "未知"
lastlon = "未知"
runorstop = "未知"
thislat = "未知"
thislon = "未知"

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Add gooddriver entities from a config_entry."""
    name = config_entry.data[CONF_NAME]    
    attr_show = config_entry.options.get(CONF_ATTR_SHOW, True)
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]
    _LOGGER.debug("user_id: %s ,coordinator 0 is ok: %s", name, coordinator.data["ERROR_CODE"])

    async_add_entities([gooddriverEntity(name, attr_show, coordinator)], False)


class gooddriverEntity(TrackerEntity):
    """Representation of a tracker condition."""
    
    def __init__(self, name, attr_show, coordinator):
        
        self.coordinator = coordinator
        _LOGGER.debug("coordinator HD_STATE_TIME: %s", coordinator.data["MESSAGE"]["HD_STATE_TIME"])
        self._name = name
        self._attrs = {}
        self._attr_show = attr_show
        
        

    @property
    def name(self):            
        return self._name
        
     
    @property
    def unique_id(self):
        """Return a unique_id for this entity."""
        _LOGGER.debug("device_tracker_unique_id: %s", self.coordinator.data["location_key"])
        return self.coordinator.data["location_key"]

    @property
    def device_info(self):
        """Return the device info."""
        return {
            "identifiers": {(DOMAIN, self.coordinator.data["location_key"])},
            "name": self._name,
            "manufacturer": MANUFACTURER,
            "entry_type": DeviceEntryType.SERVICE,
        }
    @property
    def should_poll(self):
        """Return the polling requirement of the entity."""
        return False

    # @property
    # def available(self):
        # """Return True if entity is available."""
        # return self.coordinator.last_update_success 

    @property
    def icon(self):
        """Return the icon."""
        return "mdi:car"
        
    @property
    def source_type(self):
        return "GPS"

    # @property
    # def is_connected(self):
        # return True if self.coordinator.data["ERROR_CODE"]==0 else False

    @property
    def latitude(self):
        
        global laststoptime
        global lastlat
        global lastlon
        global thislat
        global thislon
        global runorstop

        data = self.coordinator.data.get("MESSAGE")
        _LOGGER.debug("latitude result data: %s", data)
        if data:            
            self._querytime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self._updatetime = data["HD_RECENT_LOCATION"]["Time"]
            self._speed = data["HD_RECENT_LOCATION"]["Speed"]
            self._course = data["HD_RECENT_LOCATION"]["Course"]
            thislat = data["HD_RECENT_LOCATION"]["Lat"]
            thislon = data["HD_RECENT_LOCATION"]["Lng"]
            if data["HD_STATE"] == 1:
                self._status = "车辆点火"
            elif data["HD_STATE"] == 2:
                self._status = "车辆熄火"
            else:
                self._status = "未知"
                
            if thislat == lastlat and thislon == lastlon and runorstop == "运动":
                laststoptime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                runorstop = "静止"
            elif thislat != lastlat or thislon != lastlon:
                lastlat = data["HD_RECENT_LOCATION"]["Lat"]
                lastlon = data["HD_RECENT_LOCATION"]["Lng"]
                runorstop = "运动"  
                
            def time_diff (timestamp):
                result = datetime.now() - datetime.fromtimestamp(timestamp)
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
            self._parking_time=time_diff(int(time.mktime(time.strptime(data["HD_RECENT_LOCATION"]["Time"], "%Y-%m-%d %H:%M:%S")))) 
            
        return (float(thislat) + 0.00240)

    @property
    def longitude(self):
        return (float(thislon) - 0.00540)
        
    @property
    def location_accuracy(self):
        return 10
        
    # @property
    # def battery_level(self):
        # return 100
    #if (MAJOR_VERSION, MINOR_VERSION) < (2022, 4):
    @property
    def state_attributes(self): 
        attrs = super(gooddriverEntity, self).state_attributes
        data = self.coordinator.data.get("MESSAGE")
        if data:
            attrs[ATTR_SPEED] = self._speed
            attrs[ATTR_COURSE] = self._course
            
            if self._attr_show == True:
                attrs[ATTR_STATUS] = self._status
                attrs[ATTR_RUNORSTOP] = runorstop        
                attrs[ATTR_LASTSTOPTIME] = laststoptime
                attrs[ATTR_UPDATE_TIME] = self._updatetime        
                attrs[ATTR_QUERYTIME] = self._querytime
                attrs[ATTR_PARKING_TIME] = self._parking_time
            
        return attrs
    # else:
        # @property
        # def extra_state_attributes(self):
            # """Return the state attributes."""
            # attrs = super().extra_state_attributes
            # _LOGGER.debug("2022.4 later attrs: %s", attrs)            
            
            # data = self.coordinator.data.get("MESSAGE")
            # if data:
                # attrs[ATTR_SPEED] = self._speed
                # attrs[ATTR_COURSE] = self._course
                
                # if self._attr_show == True:
                    # attrs[ATTR_STATUS] = self._status
                    # attrs[ATTR_RUNORSTOP] = runorstop        
                    # attrs[ATTR_LASTSTOPTIME] = laststoptime
                    # attrs[ATTR_UPDATE_TIME] = self._updatetime        
                    # attrs[ATTR_QUERYTIME] = self._querytime
                    # attrs[ATTR_PARKING_TIME] = self._parking_time
                
            # return attrs


    async def async_added_to_hass(self):
        """Connect to dispatcher listening for entity data notifications."""
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )

    async def async_update(self):
        """Update gooddriver entity."""
        _LOGGER.debug("device tracker_update: %s", self.coordinator.data["MESSAGE"]["HD_STATE_TIME"])
        _LOGGER.debug(datetime.datetime.now(datetime.timezone.utc).astimezone().tzinfo)
        await self.coordinator.async_request_refresh()
