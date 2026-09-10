"""KontAKT: spejl F2's afdelinger, så et team kan vælge sin.

Kører én gang i døgnet. Går enhedstræet igennem fra en rod - Teknik og Miljø -
og sender listen til KontAKT, som gemmer den i ``f2_units``.

HVORFOR DEN FINDES
    F2-afdelingen bliver **ansvarlig** på journaliseringssagen og på hver akt,
    journaliseringsrobotten lægger på. Og adgangen til en akt på
    ``AccessLevel=Unit`` rækker KUN til den ansvarliges egen enhed - det er målt,
    og cBrain har bekræftet det.

    Står alle sager derfor på roden "Teknik og Miljø", er de i bedste fald
    synlige for de få, der er direkte i roden, og usynlige for Byggeri, som
    sagen hører til. Afdelingen skal vælges pr. aktindsigtsteam, og så skal
    listen være der at vælge fra.

    Indtil et team har valgt, bruger journaliseringsrobotten OO-constanten
    ``F2AfdelingStandard``. Den er reserven, ikke reglen.

HVAD DEN IKKE GØR
    Den sletter ikke. En afdeling, der forsvinder ud af F2, markeres inaktiv af
    KontAKT - så beholder et team, der peger på den, sin henvisning og kan vise
    hvad der stod, i stedet for et tal uden navn.

    Den opretter heller ikke noget i F2. F2 ejer listen; det her er en kopi.

MÅLT 2026-09-10
    138 enheder under Teknik og Miljø (partyNo 38) på ~35 sekunder, fire
    niveauer dybt. Byggeri er 450 med stien
    "Teknik og Miljø / By og Natur / Byggeri".

    ``rel/down`` giver enheder OG mennesker blandet, så der filtreres på
    ``Type == "Unit"``. Og ``PartyNumber`` er ikke ``Id``: "By og Natur" har
    PartyNumber 134 og Id 634480. Det er partynummeret, en ``PartyReference``
    vil have. Se ``oomtm.f2.unit_tree``.

OO config:
    Constant   F2Miljoe        "test" eller "prod"
    Constant   F2RestTestURL   F2's vaert (med eller uden https://)
    Constant   F2RestProdURL   ditto
    Credential F2TESTRestAkt   F2REST-klientens id + hemmelighed
    Credential F2PRODRestAkt   ditto
    Constant   F2AfdelingRod   partynummer paa roden der gaas ud fra.
                               Mangler den: 38 (Teknik og Miljoe)
    Credential KontAKTAPI      username = base URL, password = X-API-Key
"""
from OpenOrchestrator.orchestrator_connection.connection import OrchestratorConnection

import requests

from robot_framework import reset

# Teknik og Miljoe. Maalt: partyNo 38, synknoegle 1007. Staar som standard og
# ikke som en haardkodet vaerdi - en anden magistrat skal kunne bruge robotten
# ved at saette constanten.
STANDARD_ROD = 38

# Fire niveauer naaede hele Teknik og Miljoe (138 enheder). Spaerren er mod en
# cyklus i organisationen, ikke en indstilling - klienten har ogsaa sin egen
# besoegt-maengde.
MAX_DYBDE = 6


def process(
    orchestrator_connection: OrchestratorConnection,
    queue_element=None,          # ubrugt: robotten er lineaer
    client: "reset.Client | None" = None,
) -> None:
    orchestrator_connection.log_trace("Running process.")
    if client is None:
        client = reset.open_all(orchestrator_connection)

    rod = _rod(orchestrator_connection)
    orchestrator_connection.log_info(f"Henter F2-afdelinger under partyNo {rod}.")

    enheder = client.f2.unit_tree(rod, max_depth=MAX_DYBDE)
    if not enheder:
        # Ikke en tom liste, der skrives videre: en fejl. Sendte vi den tomme
        # liste til KontAKT, ville HVER afdeling blive markeret inaktiv, og
        # hvert teams valg ville se ud som om det pegede paa noget nedlagt.
        raise RuntimeError(
            f"F2 gav ingen enheder under partyNo {rod}. Roden findes ikke, "
            f"eller API-brugeren kan ikke se den. Listen skrives IKKE videre - "
            f"en tom liste ville markere alle kendte afdelinger som inaktive.")

    orchestrator_connection.log_info(
        f"{len(enheder)} afdelinger hentet. Sender til KontAKT.")
    r = requests.post(
        f"{client.kontakt_base}/api/v1/f2-units",
        headers={"X-API-Key": client.kontakt_key,
                 "Content-Type": "application/json"},
        json={"root_party_no": rod, "units": enheder},
        timeout=120,
    )
    if r.status_code not in (200, 201):
        raise RuntimeError(f"KontAKT afviste afdelingslisten: HTTP "
                           f"{r.status_code} {r.text[:300]!r}")
    orchestrator_connection.log_info(f"Færdig. {r.json()}")


def _rod(orchestrator_connection) -> int:
    """Roden, træet gås ud fra. OO-constanten, ellers Teknik og Miljø."""
    try:
        raw = (orchestrator_connection.get_constant("F2AfdelingRod").value or "").strip()
    except Exception:  # pylint: disable=broad-except
        return STANDARD_ROD
    if not raw:
        return STANDARD_ROD
    if not raw.isdigit():
        raise RuntimeError(
            f"F2AfdelingRod er {raw!r} og ikke et partynummer. Den skal være "
            f"tallet fra F2 - fx {STANDARD_ROD} for Teknik og Miljø.")
    return int(raw)
