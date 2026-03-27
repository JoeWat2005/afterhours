import pytest
from app.services.emergency_services import (
    haversine_metres,
    list_nearby_services,
)
from app.schemas.services import ServiceCategory

def test_haversine_distance_calculation():
    # Test distance between two known points in Birmingham
    # Point A: Queen Elizabeth Hospital (52.4530, -1.9367)
    # Point B: Birmingham City Hospital (52.4894, -1.9401)
    distance = haversine_metres(52.4530, -1.9367, 52.4894, -1.9401)
    # Expected distance is ~4.06 km
    assert 4000 < distance < 4200

def test_list_nearby_services_sorting_and_filtering():
    # Test nearby services around Birmingham City Centre (52.48, -1.89)
    # Steelhouse lane police station is at (52.4838, -1.8927) ~0.5km away
    # Lloyd house is at (52.4849, -1.8944) ~0.6km away
    
    # Filter by police 
    police_services = list_nearby_services(
        latitude=52.48,
        longitude=-1.89,
        category=ServiceCategory.police,
        radius_metres=1000,
        limit=5
    )
    
    assert len(police_services) >= 2
    assert police_services[0]["id"] == "police-aston" # 52.4838, -1.8927
    assert police_services[1]["id"] == "police-lloyd" # 52.4849, -1.8944
    assert police_services[0]["distance_metres"] < police_services[1]["distance_metres"]

def test_list_nearby_services_radius_limit():
    # Highgate fire station (52.4689, -1.8847) is ~1.2km from (52.48, -1.89)
    # If we set radius to 1000, it should be excluded.
    
    nearby_services = list_nearby_services(
        latitude=52.48,
        longitude=-1.89,
        category=ServiceCategory.fire_station,
        radius_metres=1000,
        limit=10
    )
    
    assert len(nearby_services) == 0

def test_list_nearby_services_limit_cap():
    # Birmingham has many services, limit 1 should return only the closest
    nearby_services = list_nearby_services(
        latitude=52.48,
        longitude=-1.89,
        category=None, # all categories
        radius_metres=5000,
        limit=1
    )
    
    assert len(nearby_services) == 1
    # Steelhouse lane police (police-aston) should be the closest to (52.48, -1.89)
    assert nearby_services[0]["id"] == "police-aston" or nearby_services[0]["id"] == "ambulance-birmingham"
