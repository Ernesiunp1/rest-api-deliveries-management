from schemas.schemas import DeliveryLocations



delivery_fees = {
    DeliveryLocations.MEDELLIN: 10000,
    DeliveryLocations.BELEN: 10000,
    DeliveryLocations.LA_ESTRELLA: 10000,
    DeliveryLocations.ENVIGADO: 10000,
    DeliveryLocations.ITAGUI: 10000,
    DeliveryLocations.CALDAS: 10000,
    DeliveryLocations.SABANETA: 10000,
    DeliveryLocations.SAN_ANTONIO: 10000,
    DeliveryLocations.BELLO: 10000,
    DeliveryLocations.COPACABANA: 10000,
    DeliveryLocations.BARBOSA: 10000,
    DeliveryLocations.GIRARDOTA: 10000,
    DeliveryLocations.SAN_CRISTOBAL: 10000,
    DeliveryLocations.MACHADO: 10000
}


def get_delivery_fee(location: DeliveryLocations):
    return delivery_fees.get(location)