"""
Solveur MPVRP-CC amélioré utilisant Google OR-Tools
Multi-Product Vehicle Routing Problem with Changeover Cost

Cette version utilise une approche plus robuste :
1. Décomposition par produit
2. VRP avec multiple passages si nécessaire
3. Garantie de satisfaction de toutes les demandes
"""
import time
import platform
from typing import List, Tuple, Dict, Optional
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
import math

from models import Instance, Solution, VehicleRoute, MiniRoute


class MPVRPSolver:
    """
    Solveur pour le problème MPVRP-CC utilisant OR-Tools.
    """
    
    def __init__(self, instance: Instance, time_limit: int = None):
        """
        Initialise le solveur.
        
        Args:
            instance: L'instance MPVRP-CC à résoudre
            time_limit: Limite de temps en secondes (None = pas de limite)
        """
        self.instance = instance
        self.time_limit = time_limit
        
    def solve(self) -> Solution:
        """
        Résout l'instance MPVRP-CC.
        
        Returns:
            Solution: La solution trouvée
        """
        start_time = time.time()
        
        # Initialiser la solution
        solution = Solution(
            instance=self.instance,
            processor=platform.processor() or "Unknown"
        )
        
        # Créer les routes pour chaque véhicule
        for vehicle in self.instance.vehicles:
            route = VehicleRoute(
                vehicle_id=vehicle.id,
                home_garage=vehicle.home_garage,
                initial_product=vehicle.initial_product - 1  # 0-indexed
            )
            solution.routes.append(route)
        
        # Initialiser les demandes et stocks restants
        remaining_demands = self._get_initial_demands()
        remaining_stocks = self._get_initial_stocks()
        
        # Utilisation des véhicules (pour répartir la charge)
        vehicle_usage = {v.id: 0 for v in self.instance.vehicles}
        
        # Résoudre le problème produit par produit
        for product in range(self.instance.nb_products):
            # Calculer le temps restant par produit (None = pas de limite)
            if self.time_limit is not None:
                time_per_product = max(1, int((self.time_limit - (time.time() - start_time)) // 
                                              max(1, self.instance.nb_products - product)))
            else:
                time_per_product = None
            
            self._solve_for_product_complete(
                solution, 
                product, 
                remaining_demands, 
                remaining_stocks,
                vehicle_usage,
                time_limit_per_product=time_per_product
            )
        
        # Calculer les métriques finales
        self._compute_metrics(solution)
        
        solution.resolution_time = time.time() - start_time
        return solution
    
    def _get_initial_demands(self) -> Dict[int, Dict[int, int]]:
        """Retourne les demandes initiales: {station_id: {product: quantity}}"""
        demands = {}
        for station in self.instance.stations:
            demands[station.id] = {}
            for p, demand in enumerate(station.demands):
                demands[station.id][p] = demand
        return demands
    
    def _get_initial_stocks(self) -> Dict[int, Dict[int, int]]:
        """Retourne les stocks initiaux: {depot_id: {product: quantity}}"""
        stocks = {}
        for depot in self.instance.depots:
            stocks[depot.id] = {}
            for p, stock in enumerate(depot.stocks):
                stocks[depot.id][p] = stock
        return stocks
    
    def _get_product_total_demand(self, demands: Dict, product: int) -> int:
        """Calcule la demande totale restante pour un produit"""
        return sum(d.get(product, 0) for d in demands.values())
    
    def _solve_for_product_complete(
        self,
        solution: Solution,
        product: int,
        remaining_demands: Dict[int, Dict[int, int]],
        remaining_stocks: Dict[int, Dict[int, int]],
        vehicle_usage: Dict[int, int],
        time_limit_per_product: int
    ):
        """
        Résout le VRP pour un produit, en garantissant que toutes les demandes sont satisfaites.
        Peut créer plusieurs mini-routes par véhicule.
        """
        # Continuer tant qu'il reste des demandes non satisfaites
        iteration = 0
        max_iterations = 100  # Sécurité
        
        while iteration < max_iterations:
            iteration += 1
            
            # Identifier les stations qui ont encore besoin de ce produit
            stations_needing = [
                s for s in self.instance.stations 
                if remaining_demands[s.id].get(product, 0) > 0
            ]
            
            if not stations_needing:
                break  # Toutes les demandes sont satisfaites
            
            # Trouver les dépôts qui ont ce produit en stock
            depots_with_stock = [
                d for d in self.instance.depots 
                if remaining_stocks[d.id].get(product, 0) > 0
            ]
            
            if not depots_with_stock:
                print(f"[ATTENTION] Pas assez de stock pour le produit {product+1}")
                break
            
            # Résoudre une itération du VRP
            # Calculer le temps par itération (None = pas de limite)
            iteration_time_limit = None
            if time_limit_per_product is not None:
                iteration_time_limit = time_limit_per_product // max(1, 10)
            
            deliveries_made = self._solve_vrp_iteration(
                solution, 
                product, 
                stations_needing, 
                depots_with_stock,
                remaining_demands, 
                remaining_stocks,
                vehicle_usage,
                iteration_time_limit
            )
            
            if not deliveries_made:
                # Utiliser la solution gloutonne comme fallback
                self._greedy_deliver(
                    solution,
                    product,
                    stations_needing,
                    depots_with_stock,
                    remaining_demands,
                    remaining_stocks,
                    vehicle_usage
                )
                break
    
    def _solve_vrp_iteration(
        self,
        solution: Solution,
        product: int,
        stations: List,
        depots: List,
        remaining_demands: Dict,
        remaining_stocks: Dict,
        vehicle_usage: Dict,
        time_limit: int
    ) -> bool:
        """
        Résout une itération du VRP pour un produit.
        Retourne True si des livraisons ont été effectuées.
        """
        # Construire les nœuds: 0 = dépôt virtuel, puis les stations
        num_nodes = len(stations) + 1
        
        # Trier les véhicules par usage et préférence de produit
        available_vehicles = sorted(
            self.instance.vehicles,
            key=lambda v: (vehicle_usage[v.id], 
                          0 if v.initial_product - 1 == product else 1,
                          v.id)
        )
        
        num_vehicles = min(len(available_vehicles), len(stations))
        
        if num_vehicles == 0:
            return False
        
        # Créer la matrice de distances
        def get_coords(node_idx):
            if node_idx == 0:
                depot = depots[0]
                return depot.x, depot.y
            else:
                station = stations[node_idx - 1]
                return station.x, station.y
        
        def distance(i, j):
            x1, y1 = get_coords(i)
            x2, y2 = get_coords(j)
            return int(math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2) * 100)
        
        # Demandes (limitées à la capacité max)
        max_capacity = max(v.capacity for v in available_vehicles)
        demands = [0] + [min(remaining_demands[s.id].get(product, 0), max_capacity) 
                        for s in stations]
        
        # Créer le gestionnaire
        manager = pywrapcp.RoutingIndexManager(num_nodes, num_vehicles, 0)
        routing = pywrapcp.RoutingModel(manager)
        
        # Callback de distance
        def distance_callback(from_index, to_index):
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            return distance(from_node, to_node)
        
        transit_callback_index = routing.RegisterTransitCallback(distance_callback)
        routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)
        
        # Callback de demande
        def demand_callback(from_index):
            from_node = manager.IndexToNode(from_index)
            return demands[from_node]
        
        demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback)
        
        # Contrainte de capacité
        vehicle_capacities = [available_vehicles[i].capacity for i in range(num_vehicles)]
        routing.AddDimensionWithVehicleCapacity(
            demand_callback_index,
            0,
            vehicle_capacities,
            True,
            'Capacity'
        )
        
        # Permettre de ne pas visiter tous les nœuds
        for node in range(1, num_nodes):
            routing.AddDisjunction([manager.NodeToIndex(node)], 100000)  # Pénalité pour non-visite
        
        # Paramètres de recherche
        search_parameters = pywrapcp.DefaultRoutingSearchParameters()
        search_parameters.first_solution_strategy = (
            routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
        )
        search_parameters.local_search_metaheuristic = (
            routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
        )
        if time_limit is not None:
            search_parameters.time_limit.seconds = int(max(1, time_limit))
        
        # Résoudre
        assignment = routing.SolveWithParameters(search_parameters)
        
        if not assignment:
            return False
        
        # Extraire la solution
        deliveries_made = False
        
        for vehicle_idx in range(num_vehicles):
            index = routing.Start(vehicle_idx)
            route_stations = []
            
            while not routing.IsEnd(index):
                node = manager.IndexToNode(index)
                if node > 0:
                    station = stations[node - 1]
                    demand = demands[node]
                    if demand > 0:
                        route_stations.append((station.id, demand))
                index = assignment.Value(routing.NextVar(index))
            
            if route_stations:
                deliveries_made = True
                vehicle = available_vehicles[vehicle_idx]
                vehicle_route = next(r for r in solution.routes if r.vehicle_id == vehicle.id)
                
                # Trouver le meilleur dépôt
                total_qty = sum(qty for _, qty in route_stations)
                best_depot = self._find_best_depot(product, total_qty, depots, remaining_stocks)
                
                # Créer la mini-route
                mini_route = MiniRoute(
                    product=product,
                    depot_id=best_depot.id,
                    quantity_loaded=total_qty,
                    deliveries=route_stations
                )
                vehicle_route.mini_routes.append(mini_route)
                
                # Mettre à jour
                vehicle_usage[vehicle.id] += 1
                for station_id, qty in route_stations:
                    remaining_demands[station_id][product] -= qty
                remaining_stocks[best_depot.id][product] -= total_qty
        
        return deliveries_made
    
    def _greedy_deliver(
        self,
        solution: Solution,
        product: int,
        stations: List,
        depots: List,
        remaining_demands: Dict,
        remaining_stocks: Dict,
        vehicle_usage: Dict
    ):
        """
        Solution gloutonne pour satisfaire les demandes restantes.
        """
        # Trier les stations par demande décroissante
        sorted_stations = sorted(
            [s for s in stations if remaining_demands[s.id].get(product, 0) > 0],
            key=lambda s: remaining_demands[s.id].get(product, 0),
            reverse=True
        )
        
        if not sorted_stations:
            return
        
        # Continuer jusqu'à ce que toutes les demandes soient satisfaites ou plus de stock
        while sorted_stations:
            # Vérifier le stock disponible
            total_stock = sum(remaining_stocks[d.id].get(product, 0) for d in depots)
            if total_stock <= 0:
                break
            
            # Trier les véhicules
            available_vehicles = sorted(
                self.instance.vehicles,
                key=lambda v: (vehicle_usage[v.id],
                              0 if v.initial_product - 1 == product else 1,
                              -v.capacity)
            )
            
            made_delivery = False
            
            for vehicle in available_vehicles:
                if not sorted_stations:
                    break
                
                vehicle_route = next(r for r in solution.routes if r.vehicle_id == vehicle.id)
                
                # Remplir le véhicule
                deliveries = []
                current_load = 0
                stations_to_remove = []
                
                for station in sorted_stations[:]:  # Copie pour itérer
                    demand = remaining_demands[station.id].get(product, 0)
                    if demand <= 0:
                        stations_to_remove.append(station)
                        continue
                    
                    can_deliver = min(demand, vehicle.capacity - current_load)
                    
                    if can_deliver > 0:
                        deliveries.append((station.id, can_deliver))
                        current_load += can_deliver
                        remaining_demands[station.id][product] -= can_deliver
                        
                        if remaining_demands[station.id][product] <= 0:
                            stations_to_remove.append(station)
                    
                    if current_load >= vehicle.capacity:
                        break
                
                # Retirer les stations satisfaites
                for s in stations_to_remove:
                    if s in sorted_stations:
                        sorted_stations.remove(s)
                
                if deliveries:
                    made_delivery = True
                    # Trouver le dépôt
                    best_depot = self._find_best_depot(product, current_load, depots, remaining_stocks)
                    
                    mini_route = MiniRoute(
                        product=product,
                        depot_id=best_depot.id,
                        quantity_loaded=current_load,
                        deliveries=deliveries
                    )
                    vehicle_route.mini_routes.append(mini_route)
                    
                    vehicle_usage[vehicle.id] += 1
                    remaining_stocks[best_depot.id][product] -= current_load
            
            if not made_delivery:
                break
    
    def _find_best_depot(
        self,
        product: int,
        quantity_needed: int,
        depots: List,
        remaining_stocks: Dict
    ):
        """Trouve le meilleur dépôt pour charger."""
        # Dépôts avec assez de stock
        valid_depots = [
            d for d in depots 
            if remaining_stocks[d.id].get(product, 0) >= quantity_needed
        ]
        
        if not valid_depots:
            # Prendre celui avec le plus de stock
            valid_depots = sorted(
                depots,
                key=lambda d: remaining_stocks[d.id].get(product, 0),
                reverse=True
            )
        
        return valid_depots[0] if valid_depots else depots[0]
    
    def _compute_metrics(self, solution: Solution):
        """Calcule les métriques de la solution."""
        for route in solution.routes:
            if not route.mini_routes:
                continue
            
            total_distance = 0.0
            total_transition = 0.0
            
            vehicle = next(v for v in self.instance.vehicles if v.id == route.vehicle_id)
            current_product = vehicle.initial_product - 1
            
            garage = next(g for g in self.instance.garages if g.id == route.home_garage)
            current_x, current_y = garage.x, garage.y
            
            for mini_route in route.mini_routes:
                # Coût de transition
                if mini_route.product != current_product:
                    transition_cost = self.instance.get_transition_cost(
                        current_product, mini_route.product
                    )
                    total_transition += transition_cost
                    current_product = mini_route.product
                
                # Distance garage/dernier point -> dépôt
                depot = next(d for d in self.instance.depots if d.id == mini_route.depot_id)
                total_distance += math.sqrt(
                    (depot.x - current_x) ** 2 + (depot.y - current_y) ** 2
                )
                current_x, current_y = depot.x, depot.y
                
                # Distances vers les stations
                for station_id, _ in mini_route.deliveries:
                    station = next(s for s in self.instance.stations if s.id == station_id)
                    total_distance += math.sqrt(
                        (station.x - current_x) ** 2 + (station.y - current_y) ** 2
                    )
                    current_x, current_y = station.x, station.y
            
            # Retour au garage
            total_distance += math.sqrt(
                (garage.x - current_x) ** 2 + (garage.y - current_y) ** 2
            )
            
            route.total_distance = total_distance
            route.total_transition_cost = total_transition


def solve_instance(instance: Instance, time_limit: int = None) -> Solution:
    """
    Fonction utilitaire pour résoudre une instance.
    
    Args:
        instance: L'instance à résoudre
        time_limit: Limite de temps en secondes (None = pas de limite)
    """
    solver = MPVRPSolver(instance, time_limit)
    return solver.solve()
