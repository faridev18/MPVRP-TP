"""
Générateur de fichiers de solution MPVRP-CC
Formate et écrit les solutions au format .dat attendu
"""
from pathlib import Path
from typing import Union
from models import Solution, Instance


def write_solution(solution: Solution, filepath: Union[str, Path]):
    """
    Écrit une solution dans un fichier .dat au format attendu.
    
    Format selon la documentation:
    - Pour chaque véhicule utilisé: bloc de 2 lignes préfixées
        - Ligne 1: "id:" puis séquence (garage - depot[qty] - station(qty) - ... - garage)
        - Ligne 2: "id:" puis produits (product(cost) - product(cost) - ...)
    - Ligne vide entre les véhicules
    - Puis les métriques globales (6 lignes)
    
    Note: Chaque mini-route est représentée dans une seule séquence continue.
    
    Args:
        solution: La solution à écrire
        filepath: Chemin du fichier de sortie
    """
    filepath = Path(filepath)
    lines = []
    
    for route in solution.routes:
        if not route.mini_routes:
            continue
        
        # Construire la ligne de séquence de visites - UNE SEULE route par véhicule
        sequence_parts = []
        product_parts = []
        
        # Garage de départ
        sequence_parts.append(str(route.home_garage))
        
        # Produit initial du véhicule
        vehicle = next(v for v in solution.instance.vehicles if v.id == route.vehicle_id)
        current_product = vehicle.initial_product - 1  # 0-indexed
        cumulative_cost = 0.0
        
        # Premier produit (au garage de départ)
        product_parts.append(f"{current_product}({cumulative_cost:.1f})")
        
        for mini_route in route.mini_routes:
            # Coût de transition si changement de produit
            if mini_route.product != current_product:
                transition_cost = solution.instance.get_transition_cost(
                    current_product, mini_route.product
                )
                cumulative_cost += transition_cost
                current_product = mini_route.product
            
            # Dépôt avec quantité chargée
            sequence_parts.append(f"{mini_route.depot_id} [{mini_route.quantity_loaded}]")
            product_parts.append(f"{current_product}({cumulative_cost:.1f})")
            
            # Stations avec quantités livrées
            for station_id, qty in mini_route.deliveries:
                sequence_parts.append(f"{station_id} ({qty})")
                product_parts.append(f"{current_product}({cumulative_cost:.1f})")
        
        # Garage d'arrivée
        sequence_parts.append(str(route.home_garage))
        product_parts.append(f"{current_product}({cumulative_cost:.1f})")
        
        # Écrire les lignes pour ce véhicule
        # Format: "id: sequence" puis "id: products"
        lines.append(f"{route.vehicle_id}: " + " - ".join(sequence_parts))
        lines.append(f"{route.vehicle_id}: " + " - ".join(product_parts))
        lines.append("")  # Ligne vide entre les véhicules
    
    # Métriques globales (6 lignes)
    lines.append(str(solution.get_nb_vehicles_used()))
    lines.append(str(solution.get_total_transitions()))
    lines.append(f"{solution.get_total_transition_cost():.1f}")
    lines.append(f"{solution.get_total_distance():.1f}")
    lines.append(solution.processor)
    lines.append(f"{solution.resolution_time:.2f}")
    
    # Écrire le fichier
    with open(filepath, 'w') as f:
        f.write('\n'.join(lines))


def format_solution_for_display(solution: Solution) -> str:
    """
    Formate une solution pour affichage console.
    
    Args:
        solution: La solution à afficher
        
    Returns:
        str: Représentation textuelle de la solution
    """
    lines = []
    lines.append("=" * 60)
    lines.append("SOLUTION MPVRP-CC")
    lines.append("=" * 60)
    
    for route in solution.routes:
        if not route.mini_routes:
            continue
        
        lines.append(f"\nVéhicule {route.vehicle_id} (Garage {route.home_garage}):")
        lines.append("-" * 40)
        
        for i, mini_route in enumerate(route.mini_routes, 1):
            lines.append(f"  Mini-route {i}:")
            lines.append(f"    Produit: {mini_route.product + 1}")
            lines.append(f"    Dépôt: {mini_route.depot_id} (chargé: {mini_route.quantity_loaded})")
            lines.append(f"    Livraisons:")
            for station_id, qty in mini_route.deliveries:
                lines.append(f"      - Station {station_id}: {qty} unités")
        
        lines.append(f"  Distance: {route.total_distance:.2f}")
        lines.append(f"  Coût transition: {route.total_transition_cost:.2f}")
    
    lines.append("\n" + "=" * 60)
    lines.append("MÉTRIQUES GLOBALES")
    lines.append("=" * 60)
    lines.append(f"Véhicules utilisés: {solution.get_nb_vehicles_used()}")
    lines.append(f"Nombre de transitions: {solution.get_total_transitions()}")
    lines.append(f"Coût total de transition: {solution.get_total_transition_cost():.2f}")
    lines.append(f"Distance totale: {solution.get_total_distance():.2f}")
    lines.append(f"Coût total: {solution.get_total_cost():.2f}")
    lines.append(f"Temps de résolution: {solution.resolution_time:.2f}s")
    lines.append(f"Processeur: {solution.processor}")
    
    return '\n'.join(lines)


def validate_solution_locally(solution: Solution) -> tuple:
    """
    Validation locale de la solution avant envoi à l'API.
    
    Args:
        solution: La solution à valider
        
    Returns:
        tuple: (is_valid, errors)
    """
    errors = []
    instance = solution.instance
    
    # Vérifier que toutes les demandes sont satisfaites
    delivered = {}  # {station_id: {product: quantity}}
    for station in instance.stations:
        delivered[station.id] = {p: 0 for p in range(instance.nb_products)}
    
    for route in solution.routes:
        for mini_route in route.mini_routes:
            for station_id, qty in mini_route.deliveries:
                delivered[station_id][mini_route.product] += qty
    
    for station in instance.stations:
        for p, demand in enumerate(station.demands):
            if delivered[station.id][p] < demand:
                errors.append(
                    f"Station {station.id}: Demande non satisfaite pour produit {p+1} "
                    f"(livré: {delivered[station.id][p]}, demandé: {demand})"
                )
    
    # Vérifier les capacités des véhicules
    for route in solution.routes:
        vehicle = next(v for v in instance.vehicles if v.id == route.vehicle_id)
        for mini_route in route.mini_routes:
            if mini_route.quantity_loaded > vehicle.capacity:
                errors.append(
                    f"Véhicule {route.vehicle_id}: Capacité dépassée "
                    f"(chargé: {mini_route.quantity_loaded}, capacité: {vehicle.capacity})"
                )
    
    # Vérifier que quantité chargée = quantité livrée pour chaque mini-route
    for route in solution.routes:
        for i, mini_route in enumerate(route.mini_routes):
            total_delivered = sum(qty for _, qty in mini_route.deliveries)
            if mini_route.quantity_loaded != total_delivered:
                errors.append(
                    f"Véhicule {route.vehicle_id}, Mini-route {i+1}: "
                    f"Déséquilibre (chargé: {mini_route.quantity_loaded}, livré: {total_delivered})"
                )
    
    return len(errors) == 0, errors


if __name__ == "__main__":
    # Test
    from parser import parse_instance
    from solver import solve_instance
    
    instance = parse_instance("../small/MPVRP_S_001_s9_d1_p2.dat")
    solution = solve_instance(instance, time_limit=30)
    
    print(format_solution_for_display(solution))
    
    is_valid, errors = validate_solution_locally(solution)
    print(f"\nValidation locale: {'OK' if is_valid else 'ERREUR'}")
    if errors:
        for e in errors:
            print(f"  - {e}")
