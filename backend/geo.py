"""Koordinat kota untuk peta lokasi proyek (lat, lng)."""

CITY_COORDS = {
    "bekasi": (-6.2383, 106.9756),
    "depok": (-6.4025, 106.7942),
    "bogor": (-6.5971, 106.8060),
    "tangerang selatan": (-6.2889, 106.7180),
    "tangerang": (-6.1783, 106.6319),
    "jakarta": (-6.2088, 106.8456),
    "bandung": (-6.9175, 107.6191),
    "sleman": (-7.7167, 110.3556),
    "bantul": (-7.8887, 110.3300),
    "yogyakarta": (-7.7956, 110.3695),
    "semarang": (-6.9932, 110.4203),
    "malang": (-7.9666, 112.6326),
    "surabaya": (-7.2575, 112.7521),
    "palangka raya": (-2.2100, 113.9200),
    "bandar lampung": (-5.3971, 105.2668),
    "lampung": (-5.3971, 105.2668),
    "medan": (3.5952, 98.6722),
}


def coords_for_location(location: str):
    """Cari (lat, lng) dari nama kota di dalam string lokasi. None jika tak ketemu."""
    if not location:
        return None, None
    city = location.split(",")[0].strip().lower()
    if city in CITY_COORDS:
        return CITY_COORDS[city]
    for name, coord in CITY_COORDS.items():
        if name in city or city in name:
            return coord
    return None, None
