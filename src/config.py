from dataclasses import dataclass
from typing import Dict


CUSTOM_MACHINE_IP_SUFFIX = 200  # Dedicated IP suffix for custom machine


DAY1_IP_SUFFIXES = [103, 105, 107, 112]
DAY2_IP_SUFFIXES = [101, 102, 103, 105, 106, 109, 110, 112]
TEAMS_IDS = [1, 2, 3, 4, 5, 6, 7, 8, 10]
OUR_TEAM_ID = 9
DAY = 2  # Change to 2 on day 2


@dataclass(frozen=True)
class VMNode:
    name: str
    description: str
    domain_prefix: str
    ip_suffix: int
    ports: Dict[str, int]
    area: str  # e.g. "Systems" vs "Infrastructure"


VM_INFRASTRUCTURE: Dict[str, VMNode] = {
    "tak": VMNode(
        name="tak",
        description="Autonomiczny dron zwiadowczy",
        domain_prefix="tak",
        ip_suffix=102,
        ports={"https": 443, "ssh": 22},
        area="Systemy Operacyjne i Wsparcia Pola Walki",
    ),
    "comms": VMNode(
        name="comms",
        description="Komunikator drużynowy",
        domain_prefix="comms",
        ip_suffix=101,
        ports={"https": 443, "ssh": 22},
        area="Systemy Operacyjne i Wsparcia Pola Walki",
    ),
    "classified": VMNode(
        name="classified",
        description="Analiza dokumentów tajnych",
        domain_prefix="classified",
        ip_suffix=105,
        ports={"https": 443, "ssh": 22},
        area="Infrastruktura IT i Bezpieczeństwo Informacji",
    ),
    "gitspace": VMNode(
        name="gitspace",
        description="Host repozytoriów i CI",
        domain_prefix="gitspace",
        ip_suffix=112,
        ports={"https": 443, "ssh": 2222},
        area="Infrastruktura IT i Bezpieczeństwo Informacji",
    ),
    "docs": VMNode(
        name="docs",
        description="Platforma dokumentacyjna",
        domain_prefix="docs",
        ip_suffix=103,
        ports={"https": 443, "ssh": 22},
        area="Infrastruktura IT i Bezpieczeństwo Informacji",
    ),
    "secrets": VMNode(
        name="secrets",
        description="Repozytorium tajnych danych",
        domain_prefix="secrets",
        ip_suffix=110,
        ports={"https": 443, "ssh": 22},
        area="Infrastruktura IT i Bezpieczeństwo Informacji",
    ),
    "milstorage": VMNode(
        name="milstorage",
        description="Sieć operacyjna milstorage",
        domain_prefix="milstorage",
        ip_suffix=107,
        ports={"https": 443, "ssh": 22},
        area="Infrastruktura IT i Bezpieczeństwo Informacji",
    ),
    "milnet": VMNode(
        name="milnet",
        description="Sieć operacyjna milnet",
        domain_prefix="milnet",
        ip_suffix=106,
        ports={"https": 443, "ssh": 22},
        area="Infrastruktura IT i Bezpieczeństwo Informacji",
    ),
}
