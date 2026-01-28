"""
Modèles de données pour le problème MPVRP-CC
Multi-Product Vehicle Routing Problem with Changeover Cost
"""
from dataclasses import dataclass, field
from typing import List, Dict, Tuple
import math


@dataclass
class Vehicle:
    """Représente un véhicule de la flotte"""
    id: int
    capacity: int
    home_garage: int
    initial_product: int  # Produit initial (1-indexed dans le fichier)


@dataclass
class Depot:
    """Représente un dépôt (point de chargement)"""
    id: int
    x: float
    y: float
    stocks: List[int]  # Stock disponible par produit


@dataclass
class Garage:
    """Représente un garage (point de départ/arrivée des véhicules)"""
    id: int
    x: float
    y: float


@dataclass
class Station:
    """Représente une station-service (client)"""
    id: int
    x: float
    y: float
    demands: List[int]  # Demande par produit


@dataclass
class Instance:
    """Représente une instance complète du problème MPVRP-CC"""
    uuid: str
    nb_products: int
    nb_depots: int
    nb_garages: int
    nb_stations: int
    nb_vehicles: int
    
    # Matrice de coût de transition entre produits
    transition_costs: List[List[float]]
    
    # Entités
    vehicles: List[Vehicle] = field(default_factory=list)
    depots: List[Depot] = field(default_factory=list)
    garages: List[Garage] = field(default_factory=list)
    stations: List[Station] = field(default_factory=list)
    
    def get_distance(self, node1_type: str, node1_id: int, 
                     node2_type: str, node2_id: int) -> float:
        """Calcule la distance euclidienne entre deux nœuds"""
        x1, y1 = self._get_coordinates(node1_type, node1_id)
        x2, y2 = self._get_coordinates(node2_type, node2_id)
        return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
    
    def _get_coordinates(self, node_type: str, node_id: int) -> Tuple[float, float]:
        """Retourne les coordonnées d'un nœud"""
        if node_type == 'garage':
            garage = next(g for g in self.garages if g.id == node_id)
            return garage.x, garage.y
        elif node_type == 'depot':
            depot = next(d for d in self.depots if d.id == node_id)
            return depot.x, depot.y
        elif node_type == 'station':
            station = next(s for s in self.stations if s.id == node_id)
            return station.x, station.y
        else:
            raise ValueError(f"Type de nœud inconnu: {node_type}")
    
    def get_transition_cost(self, from_product: int, to_product: int) -> float:
        """Retourne le coût de transition entre deux produits (0-indexed)"""
        return self.transition_costs[from_product][to_product]
    
    def get_total_demand(self, product: int) -> int:
        """Retourne la demande totale pour un produit (0-indexed)"""
        return sum(s.demands[product] for s in self.stations)
    
    def get_total_stock(self, product: int) -> int:
        """Retourne le stock total disponible pour un produit (0-indexed)"""
        return sum(d.stocks[product] for d in self.depots)
    
    def __str__(self) -> str:
        return (f"Instance MPVRP-CC:\n"
                f"  - {self.nb_products} produits\n"
                f"  - {self.nb_depots} dépôts\n"
                f"  - {self.nb_garages} garages\n"
                f"  - {self.nb_stations} stations\n"
                f"  - {self.nb_vehicles} véhicules")


@dataclass
class MiniRoute:
    """Représente une mini-route (un cycle de livraison pour un produit)"""
    product: int  # Produit transporté (0-indexed)
    depot_id: int  # Dépôt de chargement
    quantity_loaded: int  # Quantité chargée
    deliveries: List[Tuple[int, int]] = field(default_factory=list)  # [(station_id, quantity), ...]


@dataclass
class VehicleRoute:
    """Représente la route complète d'un véhicule"""
    vehicle_id: int
    home_garage: int
    mini_routes: List[MiniRoute] = field(default_factory=list)
    total_distance: float = 0.0
    total_transition_cost: float = 0.0
    initial_product: int = 0  # Produit initial du véhicule (0-indexed)
    
    def get_nb_transitions(self) -> int:
        """
        Compte le nombre de changements de produit.
        Inclut la transition du produit initial vers le premier produit transporté.
        """
        if len(self.mini_routes) == 0:
            return 0
        
        transitions = 0
        current_product = self.initial_product
        
        for mini_route in self.mini_routes:
            if mini_route.product != current_product:
                transitions += 1
                current_product = mini_route.product
        
        return transitions


@dataclass
class Solution:
    """Représente une solution complète au problème MPVRP-CC"""
    instance: Instance
    routes: List[VehicleRoute] = field(default_factory=list)
    resolution_time: float = 0.0
    processor: str = "Unknown"
    
    def get_total_distance(self) -> float:
        """Retourne la distance totale parcourue"""
        return sum(r.total_distance for r in self.routes)
    
    def get_total_transition_cost(self) -> float:
        """Retourne le coût total de transition"""
        return sum(r.total_transition_cost for r in self.routes)
    
    def get_nb_vehicles_used(self) -> int:
        """Retourne le nombre de véhicules utilisés"""
        return sum(1 for r in self.routes if len(r.mini_routes) > 0)
    
    def get_total_transitions(self) -> int:
        """Retourne le nombre total de transitions"""
        return sum(r.get_nb_transitions() for r in self.routes)
    
    def get_total_cost(self) -> float:
        """Retourne le coût total (distance + transitions)"""
        return self.get_total_distance() + self.get_total_transition_cost()
    
    def __str__(self) -> str:
        return (f"Solution MPVRP-CC:\n"
                f"  - Véhicules utilisés: {self.get_nb_vehicles_used()}\n"
                f"  - Distance totale: {self.get_total_distance():.2f}\n"
                f"  - Coût de transition: {self.get_total_transition_cost():.2f}\n"
                f"  - Coût total: {self.get_total_cost():.2f}\n"
                f"  - Temps de résolution: {self.resolution_time:.2f}s")
