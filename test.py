from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from collections import OrderedDict
import json
import argparse
import asyncio
import httpx
from httpx import RequestError

@dataclass
class Location:
    lat: float = 0.0
    lng: float = 0.0
    address: str = ""
    city: str = ""
    country: str = ""

    def to_dict(self) -> Dict:
        return OrderedDict([
            ('lat', self.lat),
            ('lng', self.lng),
            ('address', self.address),
            ('city', self.city),
            ('country', self.country)
        ])

@dataclass
class Image:
    link: str
    description: str

    def to_dict(self) -> Dict:
        return OrderedDict([
            ('link', self.link),
            ('description', self.description)
        ])

@dataclass
class Amenities:
    general: List[str] = field(default_factory=list)
    room: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return OrderedDict([
            ('general', sorted(list(set(self.general)))),
            ('room', sorted(list(set(self.room))))
        ])

@dataclass
class Images:
    rooms: List[Image] = field(default_factory=list)
    site: List[Image] = field(default_factory=list)
    amenities: List[Image] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return OrderedDict([
            ('rooms', [img.to_dict() for img in self.rooms]),
            ('site', [img.to_dict() for img in self.site]),
            ('amenities', [img.to_dict() for img in self.amenities])
        ])

@dataclass
class Hotel:
    id: str
    destination_id: str
    name: str
    location: Location = field(default_factory=Location)
    description: str = ""
    amenities: Amenities = field(default_factory=Amenities)
    images: Images = field(default_factory=Images)
    booking_conditions: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return OrderedDict([
            ('id', self.id),
            ('destination_id', self.destination_id),
            ('name', self.name),
            ('location', self.location.to_dict()),
            ('description', self.description),
            ('amenities', self.amenities.to_dict()),
            ('images', self.images.to_dict()),
            ('booking_conditions', self.booking_conditions)
        ])

    def merge(self, other: 'Hotel') -> None:
        """Merge data from another hotel"""
        if len(other.description) > len(self.description):
            self.description = other.description
        
        self.amenities.general.extend(other.amenities.general)
        self.amenities.room.extend(other.amenities.room)
        
        self.images.rooms.extend(other.images.rooms)
        self.images.site.extend(other.images.site)
        self.images.amenities.extend(other.images.amenities)
        
        self.booking_conditions.extend(other.booking_conditions)

class BaseSupplier:
    async def fetch(self) -> List[Hotel]:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(self.endpoint(), timeout=10.0)
                response.raise_for_status()
                data = response.json()
                if not isinstance(data, list):
                    print(f"Invalid response format from {self.endpoint()}")
                    return []
                return [hotel for hotel in [self.parse(item) for item in data] if hotel]
        except Exception as e:
            print(f"Error fetching from {self.endpoint()}: {str(e)}")
            return []

    def endpoint(self) -> str:
        raise NotImplementedError

    def parse(self, data: dict) -> Optional[Hotel]:
        raise NotImplementedError

    @staticmethod
    def safe_float(value: Any) -> float:
        if value is None:
            return 0.0
        try:
            return float(value)
        except (ValueError, TypeError):
            return 0.0

class AcmeSupplier(BaseSupplier):
    def endpoint(self) -> str:
        return "https://5f2be0b4ffc88500167b85a0.mockapi.io/suppliers/acme"

    def parse(self, data: dict) -> Optional[Hotel]:
        try:
            return Hotel(
                id=str(data["Id"]),
                destination_id=str(data["DestinationId"]),
                name=str(data["Name"]),
                location=Location(
                    lat=self.safe_float(data.get("Latitude")),
                    lng=self.safe_float(data.get("Longitude")),
                    address=str(data.get("Address", "")),
                    city=str(data.get("City", "")),
                    country=str(data.get("Country", ""))
                ),
                description=str(data.get("Description", "")),
                amenities=Amenities(
                    general=data.get("Facilities", []),
                    room=[]
                ),
                images=Images(),
                booking_conditions=[]
            )
        except Exception as e:
            print(f"Error parsing ACME data: {e}")
            return None

class PaperfliesSupplier(BaseSupplier):
    def endpoint(self) -> str:
        return "https://5f2be0b4ffc88500167b85a0.mockapi.io/suppliers/paperflies"

    def parse(self, data: dict) -> Optional[Hotel]:
        try:
            location_data = data.get("location", {})
            amenities_data = data.get("amenities", {})
            images_data = data.get("images", {})

            return Hotel(
                id=str(data["hotel_id"]),
                destination_id=str(data["destination_id"]),
                name=str(data["hotel_name"]),
                location=Location(
                    address=str(location_data.get("address", "")),
                    city=str(location_data.get("city", "")),
                    country=str(location_data.get("country", ""))
                ),
                description=str(data.get("details", "")),
                amenities=Amenities(
                    general=amenities_data.get("general", []),
                    room=amenities_data.get("room", [])
                ),
                images=Images(
                    rooms=[
                        Image(str(img["link"]), str(img["caption"]))
                        for img in images_data.get("rooms", [])
                        if isinstance(img, dict) and "link" in img and "caption" in img
                    ],
                    site=[
                        Image(str(img["link"]), str(img["caption"]))
                        for img in images_data.get("site", [])
                        if isinstance(img, dict) and "link" in img and "caption" in img
                    ]
                ),
                booking_conditions=data.get("booking_conditions", [])
            )
        except Exception as e:
            print(f"Error parsing Paperflies data: {e}")
            return None

class PatagoniaSupplier(BaseSupplier):
    def endpoint(self) -> str:
        return "https://5f2be0b4ffc88500167b85a0.mockapi.io/suppliers/patagonia"

    def parse(self, data: dict) -> Optional[Hotel]:
        try:
            images_data = data.get("images", {})
            amenities_list = data.get("amenities", [])
            if not isinstance(amenities_list, list):
                amenities_list = []

            return Hotel(
                id=str(data["id"]),
                destination_id=str(data["destination"]),
                name=str(data["name"]),
                location=Location(
                    lat=self.safe_float(data.get("lat")),
                    lng=self.safe_float(data.get("lng")),
                    address=str(data.get("address", ""))
                ),
                description=str(data.get("info", "")),
                amenities=Amenities(
                    room=[str(a).strip() for a in amenities_list if a]
                ),
                images=Images(
                    rooms=[
                        Image(str(img["url"]), str(img["description"]))
                        for img in images_data.get("rooms", [])
                        if isinstance(img, dict) and "url" in img and "description" in img
                    ],
                    amenities=[
                        Image(str(img["url"]), str(img["description"]))
                        for img in images_data.get("amenities", [])
                        if isinstance(img, dict) and "url" in img and "description" in img
                    ]
                )
            )
        except Exception as e:
            print(f"Error parsing Patagonia data: {e}")
            return None

class HotelService:
    def __init__(self):
        self.hotels: Dict[str, Hotel] = {}
        self.suppliers = [
            AcmeSupplier(),
            PaperfliesSupplier(),
            PatagoniaSupplier()
        ]

    async def fetch_all(self) -> None:
        for supplier in self.suppliers:
            hotels = await supplier.fetch()
            self.merge_hotels(hotels)

    def merge_hotels(self, hotels: List[Hotel]) -> None:
        for hotel in hotels:
            if hotel.id in self.hotels:
                self.hotels[hotel.id].merge(hotel)
            else:
                self.hotels[hotel.id] = hotel

    def find(self, hotel_ids: Optional[List[str]] = None, 
             destination_ids: Optional[List[str]] = None) -> List[Hotel]:
        hotels = list(self.hotels.values())
        
        if hotel_ids:
            hotel_ids_set = set(hotel_ids)
            hotels = [h for h in hotels if h.id in hotel_ids_set]
            
        if destination_ids:
            destination_ids_set = set(destination_ids)
            hotels = [h for h in hotels if h.destination_id in destination_ids_set]
            
        return hotels

async def fetch_hotels(hotel_ids: List[str], destination_ids: List[str]) -> str:
    service = HotelService()
    await service.fetch_all()
    
    filtered_hotels = service.find(hotel_ids, destination_ids)
    return json.dumps([hotel.to_dict() for hotel in filtered_hotels], indent=2)

def main():
    parser = argparse.ArgumentParser(description='Hotel data fetcher')
    parser.add_argument('hotel_ids', help='Comma-separated hotel IDs or "none"')
    parser.add_argument('destination_ids', help='Comma-separated destination IDs or "none"')
    
    args = parser.parse_args()
    
    hotel_ids = args.hotel_ids.split(',') if args.hotel_ids.lower() != 'none' else None
    destination_ids = args.destination_ids.split(',') if args.destination_ids.lower() != 'none' else None
    
    result = asyncio.run(fetch_hotels(hotel_ids, destination_ids))
    print(result)

if __name__ == '__main__':
    main()