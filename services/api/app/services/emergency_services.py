from __future__ import annotations

from dataclasses import dataclass
from math import asin, cos, radians, sin, sqrt

from app.schemas.services import ServiceCategory


@dataclass(frozen=True)
class ServiceSeed:
    id: str
    name: str
    category: ServiceCategory
    address: str
    latitude: float
    longitude: float


BIRMINGHAM_SERVICE_SEEDS: tuple[ServiceSeed, ...] = (
    ServiceSeed(
        id="hospital-qe",
        name="Queen Elizabeth Hospital Birmingham",
        category=ServiceCategory.hospital,
        address="Mindelsohn Way, Birmingham B15 2GW",
        latitude=52.4530,
        longitude=-1.9367,
    ),
    ServiceSeed(
        id="hospital-city",
        name="Birmingham City Hospital",
        category=ServiceCategory.hospital,
        address="Dudley Road, Birmingham B18 7QH",
        latitude=52.4894,
        longitude=-1.9401,
    ),
    ServiceSeed(
        id="hospital-heartlands",
        name="Heartlands Hospital",
        category=ServiceCategory.hospital,
        address="Bordesley Green East, Birmingham B9 5SS",
        latitude=52.4786,
        longitude=-1.8278,
    ),
    ServiceSeed(
        id="police-aston",
        name="Birmingham West & Central Police Station",
        category=ServiceCategory.police,
        address="Steelhouse Lane, Birmingham B4 6NH",
        latitude=52.4838,
        longitude=-1.8927,
    ),
    ServiceSeed(
        id="police-lloyd",
        name="Lloyd House Police Headquarters",
        category=ServiceCategory.police,
        address="Colmore Circus Queensway, Birmingham B4 6NQ",
        latitude=52.4849,
        longitude=-1.8944,
    ),
    ServiceSeed(
        id="police-bournville",
        name="Bournville Lane Police Station",
        category=ServiceCategory.police,
        address="Bournville Lane, Birmingham B30 2JY",
        latitude=52.4318,
        longitude=-1.9419,
    ),
    ServiceSeed(
        id="fire-highgate",
        name="Highgate Fire Station",
        category=ServiceCategory.fire_station,
        address="Highgate Street, Birmingham B12 0XR",
        latitude=52.4689,
        longitude=-1.8847,
    ),
    ServiceSeed(
        id="fire-haden",
        name="Birmingham Haden Circus Fire Station",
        category=ServiceCategory.fire_station,
        address="Haden Circus, Birmingham B12 8EB",
        latitude=52.4488,
        longitude=-1.8864,
    ),
    ServiceSeed(
        id="fire-northfield",
        name="Northfield Fire Station",
        category=ServiceCategory.fire_station,
        address="Frankley Beeches Road, Birmingham B31 5PR",
        latitude=52.4071,
        longitude=-1.9675,
    ),
    ServiceSeed(
        id="ambulance-birmingham",
        name="West Midlands Ambulance Service (Birmingham Hub)",
        category=ServiceCategory.ambulance,
        address="Millennium Point, Curzon Street, Birmingham B4 7XG",
        latitude=52.4818,
        longitude=-1.8853,
    ),
    ServiceSeed(
        id="ambulance-aston",
        name="Aston Ambulance Station",
        category=ServiceCategory.ambulance,
        address="Aston, Birmingham",
        latitude=52.5010,
        longitude=-1.8855,
    ),
    ServiceSeed(
        id="ambulance-sellyoak",
        name="Selly Oak Ambulance Point",
        category=ServiceCategory.ambulance,
        address="Selly Oak, Birmingham",
        latitude=52.4420,
        longitude=-1.9360,
    ),
)


def haversine_metres(
    latitude_a: float,
    longitude_a: float,
    latitude_b: float,
    longitude_b: float,
) -> float:
    earth_radius_metres = 6_371_000.0

    latitude_delta = radians(latitude_b - latitude_a)
    longitude_delta = radians(longitude_b - longitude_a)

    latitude_a_radians = radians(latitude_a)
    latitude_b_radians = radians(latitude_b)

    haversine_value = (
        sin(latitude_delta / 2) ** 2
        + cos(latitude_a_radians)
        * cos(latitude_b_radians)
        * sin(longitude_delta / 2) ** 2
    )
    return 2 * earth_radius_metres * asin(sqrt(haversine_value))


def list_nearby_services(
    *,
    latitude: float,
    longitude: float,
    category: ServiceCategory | None,
    radius_metres: int,
    limit: int,
) -> list[dict]:
    filtered_services: list[dict] = []

    for seed in BIRMINGHAM_SERVICE_SEEDS:
        if category is not None and seed.category != category:
            continue

        distance_metres = haversine_metres(
            latitude,
            longitude,
            seed.latitude,
            seed.longitude,
        )
        if distance_metres > radius_metres:
            continue

        filtered_services.append(
            {
                "id": seed.id,
                "name": seed.name,
                "category": seed.category,
                "address": seed.address,
                "latitude": seed.latitude,
                "longitude": seed.longitude,
                "distance_metres": int(round(distance_metres)),
                "source": "seed",
            }
        )

    filtered_services.sort(key=lambda item: (item["distance_metres"], item["name"]))
    return filtered_services[:limit]
