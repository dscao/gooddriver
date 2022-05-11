"""Support for the gooddriver service."""
import logging
import time, datetime
from datetime import datetime, timedelta

from homeassistant.components.device_tracker.config_entry import TrackerEntity

#from homeassistant.helpers.entity import Entity

from homeassistant.const import (
    CONF_NAME,
    CONF_API_KEY,
    ATTR_GPS_ACCURACY,
    ATTR_LATITUDE,
    ATTR_LONGITUDE,
    STATE_HOME,
    STATE_NOT_HOME,    
)

from .const import (
    CONF_USER_ID,
    COORDINATOR,
    DOMAIN,
    UNDO_UPDATE_LISTENER,
    CONF_ATTR_SHOW,
    MANUFACTURER,
)




PARALLEL_UPDATES = 1
_LOGGER = logging.getLogger(__name__)

laststoptime = "未知"
lastlat = "未知"
lastlon = "未知"
runorstop = "未知"

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Add gooddriver entities from a config_entry."""
    name = config_entry.data[CONF_NAME]
     
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]
    _LOGGER.debug("user_id: %s ,coordinator 0 is ok: %s", name, coordinator.data["ERROR_CODE"])

    async_add_entities([gooddriverEntity(name, coordinator)], False)


class gooddriverEntity(TrackerEntity):
    """Representation of a tracker condition."""
    
    def __init__(self, name, coordinator):
        
        self.coordinator = coordinator
        _LOGGER.debug("coordinator HD_STATE_TIME: %s", coordinator.data["MESSAGE"]["HD_STATE_TIME"])
        self._name = name
        self._attrs = {}
        
     
        

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

    @property
    def available(self):
        """Return True if entity is available."""
        return self.coordinator.last_update_success 

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
        return (float(self.coordinator.data["MESSAGE"]["HD_RECENT_LOCATION"]["Lat"]) + 0.00240)

    @property
    def longitude(self):
        return (float(self.coordinator.data["MESSAGE"]["HD_RECENT_LOCATION"]["Lng"]) - 0.00540) 
        
    @property
    def location_accuracy(self):
        return 10
        
    @property
    def battery_level(self):
        return 100
        
    @property
    def updatetime(self):
        """实时获取时间."""
        return self.coordinator.data["MESSAGE"]["HD_RECENT_LOCATION"]["Time"] 
    
    @property
    def querytime(self):
        """实时查询时间."""
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    
        
    @property
    def speed(self):
        return self.coordinator.data["MESSAGE"]["HD_RECENT_LOCATION"]["Speed"]
        
    @property
    def course(self):
        return self.coordinator.data["MESSAGE"]["HD_RECENT_LOCATION"]["Course"]
        
    @property
    def parking_time(self):
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
        pktime=int(time.mktime(time.strptime(self.coordinator.data["MESSAGE"]["HD_RECENT_LOCATION"]["Time"], "%Y-%m-%d %H:%M:%S")))
        return time_diff(pktime)
    
    @property
    def state_attributes(self):
    
        global laststoptime
        global lastlat
        global lastlon
        global runorstop
        
        if self.coordinator.data["MESSAGE"]["HD_STATE"] == 1:
            status = "车辆点火"
        elif self.coordinator.data["MESSAGE"]["HD_STATE"] == 2:
            status = "车辆熄火"
        else:
            status = "未知"
            
        if self.coordinator.data["MESSAGE"]["HD_RECENT_LOCATION"]["Lat"] == lastlat and self.coordinator.data["MESSAGE"]["HD_RECENT_LOCATION"]["Lng"] == lastlon and runorstop == "运动":
            laststoptime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            runorstop = "静止"
        elif self.coordinator.data["MESSAGE"]["HD_RECENT_LOCATION"]["Lat"] != lastlat or self.coordinator.data["MESSAGE"]["HD_RECENT_LOCATION"]["Lng"] != lastlon:
            lastlat = self.coordinator.data["MESSAGE"]["HD_RECENT_LOCATION"]["Lat"]
            lastlon = self.coordinator.data["MESSAGE"]["HD_RECENT_LOCATION"]["Lng"]
            runorstop = "运动"  
            
        data = super(gooddriverEntity, self).state_attributes

        data['speed'] = self.speed
        data['course'] = self.course        
        data['status'] = status
        data['runorstop'] = runorstop        
        data['laststoptime'] = laststoptime
        data['update_time'] = self.updatetime        
        data['querytime'] = self.querytime
        data['parking_time'] = self.parking_time
                   
        return data  

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
