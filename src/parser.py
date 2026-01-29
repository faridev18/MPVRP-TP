
from pathlib import Path
from typing import Union
from models import Instance, Vehicle, Depot, Garage, Station


def parse_instance(filepath: Union[str, Path]) -> Instance:
    """
    Parse un fichier d'instance MPVRP-CC et retourne un objet Instance.
    
    Args:
        filepath: Chemin vers le fichier .dat
        
    Returns:
        Instance: L'instance parsée
    """
    filepath = Path(filepath)
    
    with open(filepath, 'r') as f:
        lines = [line.strip() for line in f.readlines() if line.strip()]
    
    line_idx = 0
    
    # Ligne 1: UUID
    uuid = lines[line_idx].replace('#', '').strip()
    line_idx += 1
    
    # Ligne 2: Paramètres globaux
    # Format: nb_products nb_depots nb_garages nb_stations nb_vehicles
    params = lines[line_idx].split()
    nb_products = int(params[0])
    nb_depots = int(params[1])
    nb_garages = int(params[2])
    nb_stations = int(params[3])
    nb_vehicles = int(params[4])
    line_idx += 1
    
    # Matrice de coûts de transition (nb_products x nb_products)
    transition_costs = []
    for i in range(nb_products):
        row = [float(x) for x in lines[line_idx].split()]
        transition_costs.append(row)
        line_idx += 1
    
    # Véhicules
    vehicles = []
    for i in range(nb_vehicles):
        parts = lines[line_idx].split()
        vehicle = Vehicle(
            id=int(parts[0]),
            capacity=int(parts[1]),
            home_garage=int(parts[2]),
            initial_product=int(parts[3])  # 1-indexed dans le fichier
        )
        vehicles.append(vehicle)
        line_idx += 1
    
    # Dépôts
    depots = []
    for i in range(nb_depots):
        parts = lines[line_idx].split()
        depot = Depot(
            id=int(parts[0]),
            x=float(parts[1]),
            y=float(parts[2]),
            stocks=[int(parts[3 + p]) for p in range(nb_products)]
        )
        depots.append(depot)
        line_idx += 1
    
    # Garages
    garages = []
    for i in range(nb_garages):
        parts = lines[line_idx].split()
        garage = Garage(
            id=int(parts[0]),
            x=float(parts[1]),
            y=float(parts[2])
        )
        garages.append(garage)
        line_idx += 1
    
    # Stations
    stations = []
    for i in range(nb_stations):
        parts = lines[line_idx].split()
        station = Station(
            id=int(parts[0]),
            x=float(parts[1]),
            y=float(parts[2]),
            demands=[int(parts[3 + p]) for p in range(nb_products)]
        )
        stations.append(station)
        line_idx += 1
    
    return Instance(
        uuid=uuid,
        nb_products=nb_products,
        nb_depots=nb_depots,
        nb_garages=nb_garages,
        nb_stations=nb_stations,
        nb_vehicles=nb_vehicles,
        transition_costs=transition_costs,
        vehicles=vehicles,
        depots=depots,
        garages=garages,
        stations=stations
    )


def validate_instance(instance: Instance) -> bool:
    """
    Valide la cohérence d'une instance.
    
    Args:
        instance: L'instance à valider
        
    Returns:
        bool: True si l'instance est valide
    """
    errors = []
    
    # Vérifier que chaque produit a assez de stock pour satisfaire la demande
    for p in range(instance.nb_products):
        total_demand = instance.get_total_demand(p)
        total_stock = instance.get_total_stock(p)
        if total_stock < total_demand:
            errors.append(f"Produit {p+1}: Stock insuffisant ({total_stock} < {total_demand})")
    
    # Vérifier que les véhicules sont assignés à des garages existants
    garage_ids = {g.id for g in instance.garages}
    for v in instance.vehicles:
        if v.home_garage not in garage_ids:
            errors.append(f"Véhicule {v.id}: Garage {v.home_garage} inexistant")
    
    # Vérifier que les produits initiaux sont valides
    for v in instance.vehicles:
        if v.initial_product < 1 or v.initial_product > instance.nb_products:
            errors.append(f"Véhicule {v.id}: Produit initial {v.initial_product} invalide")
    
    if errors:
        print("Erreurs de validation:")
        for e in errors:
            print(f"  - {e}")
        return False
    
    return True


if __name__ == "__main__":
    # Test du parser
    import sys
    
    if len(sys.argv) > 1:
        instance_file = sys.argv[1]
    else:
        # Fichier de test par défaut
        instance_file = "../small/MPVRP_S_001_s9_d1_p2.dat"
    
    instance = parse_instance(instance_file)
    print(instance)
    print(f"\nValidation: {'OK' if validate_instance(instance) else 'ERREUR'}")
    
    # Afficher quelques détails
    print(f"\nMatrice de transition:")
    for row in instance.transition_costs:
        print(f"  {row}")
    
    print(f"\nVéhicules:")
    for v in instance.vehicles:
        print(f"  V{v.id}: capacité={v.capacity}, garage={v.home_garage}, produit_initial={v.initial_product}")
    
    print(f"\nDemandes par produit:")
    for p in range(instance.nb_products):
        total = instance.get_total_demand(p)
        stock = instance.get_total_stock(p)
        print(f"  Produit {p+1}: demande={total}, stock={stock}")
