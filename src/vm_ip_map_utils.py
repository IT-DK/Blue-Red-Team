from typing import Dict, Iterable, List, Optional, Union

import src.config as config
from src.config import (
    CUSTOM_MACHINE_IP_SUFFIX,
    DAY1_IP_SUFFIXES,
    DAY2_IP_SUFFIXES,
    OUR_TEAM_ID,
    TEAMS_IDS,
    VM_INFRASTRUCTURE,
    VMNode,
)


def _public_ip(team: Union[str, int], suffix: int) -> str:
    return f"10.10.{team}.{suffix}"


def _internal_ip(suffix: int) -> str:
    return f"172.28.0.{suffix}"



def _format_team(team: Union[str, int]) -> str:
    team_str = str(team)
    return team_str.zfill(2) if team_str.isdigit() else team_str


def service_ips(node: VMNode, team: Union[str, int]) -> Dict[str, str]:
    return {
        "public": _public_ip(team, node.ip_suffix),
        "internal": _internal_ip(node.ip_suffix),
    }


def get_by_service(service_key: str, team: Union[str, int]) -> Optional[Dict[str, object]]:
    node = VM_INFRASTRUCTURE.get(service_key)
    if not node:
        return None
    return {
        "name": node.name,
        "description": node.description,
        "area": node.area,
        "hostname": f"{node.domain_prefix}.{_format_team(team)}.*.*",
        "ips": service_ips(node, team),
        "ports": node.ports,
    }


def get_by_ip_suffix(suffix: int, team: Optional[Union[str, int]] = None) -> Optional[Dict[str, object]]:
    for node in VM_INFRASTRUCTURE.values():
        if node.ip_suffix == suffix:
            info = {
                "name": node.name,
                "description": node.description,
                "area": node.area,
                "ips": {
                    "internal": _internal_ip(node.ip_suffix),
                },
                "ports": node.ports,
            }
            if team:
                info["ips"]["public"] = _public_ip(team, node.ip_suffix)
            return info
    return None


def list_all_services() -> Dict[str, Dict[str, object]]:
    return {
        key: {
            "name": node.name,
            "description": node.description,
            "area": node.area,
            "ports": node.ports,
        }
        for key, node in VM_INFRASTRUCTURE.items()
    }


def _suffixes_for_day(day: int) -> Iterable[int]:
    if day == 1:
        return DAY1_IP_SUFFIXES
    if day == 2:
        return DAY2_IP_SUFFIXES
    raise ValueError("Day must be 1 or 2")


def services_for_day(day: int) -> List[VMNode]:
    suffixes = set(_suffixes_for_day(day))
    return [node for node in VM_INFRASTRUCTURE.values() if node.ip_suffix in suffixes]


def day1_services() -> List[VMNode]:
    return services_for_day(1)


def day2_services() -> List[VMNode]:
    return services_for_day(2)


def get_our_internal_ips(day: Optional[int] = None) -> List[str]:
    """Get list of internal IPs for our team's VMs for a specific day.
    
    Args:
        day: Day number (1 or 2). If None, uses config.DAY
        
    Returns:
        List of internal IP addresses (e.g., ['172.28.0.101', '172.28.0.102', ...])
    """
    if day is None:
        day = config.DAY
    nodes = services_for_day(day)
    return [_internal_ip(node.ip_suffix) for node in nodes]


def get_all_other_teams_vm_ips() -> Dict[str, Dict[int, str]]:
    targets = services_for_day(config.DAY)
    other_teams = [team for team in TEAMS_IDS if team != OUR_TEAM_ID]
    result: Dict[str, Dict[int, str]] = {}
    for node in targets:
        team_ips: Dict[int, str] = {}
        for team in other_teams:
            ips = service_ips(node, team)
            team_ips[team] = ips["public"]
        result[node.name] = team_ips
    return result


def get_custom_machine_ips() -> Dict[str, str]:
    """Get IP addresses for our team's custom machine.
    
    Returns:
        Dictionary with external and internal IP addresses:
        {"ext": "10.10.X.Y", "int": "172.28.0.Y"}
        where X is OUR_TEAM_ID and Y is CUSTOM_MACHINE_IP_SUFFIX
    """
    return {
        "ext": _public_ip(OUR_TEAM_ID, CUSTOM_MACHINE_IP_SUFFIX),
        "int": _internal_ip(CUSTOM_MACHINE_IP_SUFFIX),
    }
