import sys
sys.path.insert(0, '..')

from argparse import ArgumentParser

from src.vm_ip_map_utils import get_by_service


# Run:  
# py vm_ip_map.py 5 chat 
# (available services: chat, docclassifier, gitspace, docs, secrets, milnet, szyszka, tak)

def main() -> None:
    parser = ArgumentParser(description="Mapa maszyn z cyberlegionowej sieci")
    parser.add_argument("team", help="Identyfikator drużyny (np. 23)")
    parser.add_argument("service", help="Nazwą serwisu (np. chat)")
    args = parser.parse_args()

    data = get_by_service(args.service, args.team)
    if not data:
        parser.error(f"Nie mam danych dla usługi {args.service}")
    print(data)


if __name__ == "__main__":
    main()
