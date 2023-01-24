"""Support for the gooddriver service."""
import logging
import time, datetime

from homeassistant.components.device_tracker.config_entry import TrackerEntity
from homeassistant.helpers.device_registry import DeviceEntryType

#from homeassistant.helpers.entity import Entity
from .helper import gcj02towgs84

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
    CONF_GPS_CONVER,
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



async def async_setup_entry(hass, config_entry, async_add_entities):
    """Add gooddriver entities from a config_entry."""
    name = config_entry.data[CONF_NAME]
    gps_conver = config_entry.options.get(CONF_GPS_CONVER, True)
    attr_show = config_entry.options.get(CONF_ATTR_SHOW, True)
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]
    _LOGGER.debug("user_id: %s ,coordinator result: %s", name, coordinator.data)

    async_add_entities([gooddriverEntity(name, gps_conver, attr_show, coordinator)], False)


class gooddriverEntity(TrackerEntity):
    """Representation of a tracker condition."""
    _attr_has_entity_name = True
    _attr_name = None
    def __init__(self, name, gps_conver, attr_show, coordinator):
        
        self.coordinator = coordinator
        _LOGGER.debug("coordinator: %s", coordinator.data)
        self._name = name
        self._gps_conver = gps_conver
        self._attrs = {}
        self._attr_show = attr_show
        self._coords = []
        if self._gps_conver == True:
            self._coords = gcj02towgs84(self.coordinator.data["thislon"], self.coordinator.data["thislat"])
        else:
            self._coords = [self.coordinator.data["thislon"], self.coordinator.data["thislat"]]

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
            "model": self.coordinator.data["device_model"],
            "sw_version": self.coordinator.data["sw_version"],
        }
    @property
    def should_poll(self):
        """Return the polling requirement of the entity."""
        return True

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
        return "gps"

    @property
    def latitude(self):                
        return self._coords[1]

    @property
    def longitude(self):
        return self._coords[0]
        
    @property
    def location_accuracy(self):
        return 10        

    @property
    def state_attributes(self): 
        attrs = super(gooddriverEntity, self).state_attributes
        #data = self.coordinator.data.get("result")
        data = self.coordinator.data
        if data:             
            attrs["speed"] = data["speed"]
            attrs["speed"] = data["speed"]
            attrs[ATTR_STATUS] = data["status"]
            attrs["updatetime"] = data["updatetime"]        
            attrs[ATTR_QUERYTIME] = data["querytime"]
            if self._attr_show == True:
                attrs[ATTR_RUNORSTOP] = data["runorstop"]
                attrs[ATTR_LASTSTOPTIME] = data["laststoptime"]
                attrs[ATTR_PARKING_TIME] = data["parkingtime"]  
        return attrs 

    async def async_added_to_hass(self):
        """Connect to dispatcher listening for entity data notifications."""
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )

    async def async_update(self):
        """Update gooddriver entity."""
        _LOGGER.debug(datetime.datetime.now(datetime.timezone.utc).astimezone().tzinfo)
        await self.coordinator.async_request_refresh()
        if self._gps_conver == True:
            self._coords = gcj02towgs84(self.coordinator.data["thislon"], self.coordinator.data["thislat"])
        else:
            self._coords = [self.coordinator.data["thislon"], self.coordinator.data["thislat"]]
