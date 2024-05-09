from enum import Enum


class OpticalDiscType(str, Enum):
    CD = "cd"
    DVD = "dvd"
    BLU_RAY = "blu_ray"


class AutomatedRippingMachine:
    pass


# class OpticalDrive:
#     __slots__ = (
#         "path",
#         "is_mounted",
#         "mount_location",
#         "disc_type",
#     )

#     device_name: str
#     device_path: Path
#     is_mounted: bool
#     mount_path: Path
#     disc_type: OpticalDiscType

#     def __init__(
#         self,
#         path: str,
#         is_mounted: bool,
#         mount_location: str,
#         disc_type: OpticalDiscType,
#     ) -> None:
#         pass

#     @classmethod
#     def fetch_drives(cls) -> List["OpticalDrive"]:
#         pass


#     {
#     "mode": "search",
#     "results": {
#         "0": {
#             "crc_id": "d0d1bcba30e2dfc6",
#             "date_added": "2023-06-12 04:29:43.740132",
#             "disctype": "None",
#             "hasnicetitle": "True",
#             "imdb_id": "tt0120201",
#             "label": "STARSHIP_TROOPERS",
#             "no_of_titles": "None",
#             "poster_img": "None",
#             "title": "Starship-Troopers",
#             "tmdb_id": "None",
#             "validated": "False",
#             "video_type": "movie",
#             "year": "1997"
#         }
#     },
#     "success": true
# }
