"""
Visualisation des solutions MPVRP-CC
Génère des graphiques pour visualiser les routes
"""
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.lines import Line2D
from pathlib import Path
from typing import Optional
import numpy as np

from models import Solution, Instance


# Couleurs pour les produits
PRODUCT_COLORS = [
    '#e74c3c',  # Rouge
    '#3498db',  # Bleu
    '#2ecc71',  # Vert
    '#f39c12',  # Orange
    '#9b59b6',  # Violet
    '#1abc9c',  # Turquoise
    '#e91e63',  # Rose
    '#00bcd4',  # Cyan
    '#ff9800',  # Ambre
    '#795548',  # Marron
    '#607d8b',  # Gris-bleu
    '#8bc34a',  # Vert clair
]


def plot_instance(instance: Instance, ax: Optional[plt.Axes] = None, title: str = None):
    """
    Visualise une instance (sans les routes).
    
    Args:
        instance: L'instance à visualiser
        ax: Axes matplotlib (créé si None)
        title: Titre du graphique
    """
    if ax is None:
        fig, ax = plt.subplots(figsize=(12, 10))
    
    # Garages (carrés noirs)
    for garage in instance.garages:
        ax.scatter(garage.x, garage.y, marker='s', s=200, c='black', 
                   zorder=5, edgecolors='white', linewidths=2)
        ax.annotate(f'G{garage.id}', (garage.x, garage.y), 
                    textcoords="offset points", xytext=(0, 10), ha='center', fontsize=9)
    
    # Dépôts (triangles bleus)
    for depot in instance.depots:
        ax.scatter(depot.x, depot.y, marker='^', s=200, c='#3498db', 
                   zorder=5, edgecolors='white', linewidths=2)
        ax.annotate(f'D{depot.id}', (depot.x, depot.y), 
                    textcoords="offset points", xytext=(0, 10), ha='center', fontsize=9)
    
    # Stations (cercles rouges)
    for station in instance.stations:
        total_demand = sum(station.demands)
        size = 50 + total_demand / 100  # Taille proportionnelle à la demande
        ax.scatter(station.x, station.y, marker='o', s=size, c='#e74c3c', 
                   zorder=4, edgecolors='white', linewidths=1, alpha=0.7)
        ax.annotate(f'S{station.id}', (station.x, station.y), 
                    textcoords="offset points", xytext=(0, 8), ha='center', fontsize=7)
    
    # Légende
    legend_elements = [
        Line2D([0], [0], marker='s', color='w', markerfacecolor='black', 
               markersize=12, label='Garages'),
        Line2D([0], [0], marker='^', color='w', markerfacecolor='#3498db', 
               markersize=12, label='Dépôts'),
        Line2D([0], [0], marker='o', color='w', markerfacecolor='#e74c3c', 
               markersize=12, label='Stations'),
    ]
    ax.legend(handles=legend_elements, loc='upper left')
    
    ax.set_xlabel('X')
    ax.set_ylabel('Y')
    ax.set_title(title or f"Instance MPVRP-CC: {instance.nb_stations} stations, {instance.nb_products} produits")
    ax.grid(True, alpha=0.3)
    
    return ax


def plot_solution(solution: Solution, save_path: Optional[Path] = None, show: bool = True):
    """
    Visualise une solution complète.
    
    Args:
        solution: La solution à visualiser
        save_path: Chemin pour sauvegarder l'image (optionnel)
        show: Afficher le graphique
    """
    instance = solution.instance
    
    fig, ax = plt.subplots(figsize=(14, 12))
    
    # D'abord, dessiner l'instance de base
    plot_instance(instance, ax)
    
    # Ensuite, dessiner les routes
    for route in solution.routes:
        if not route.mini_routes:
            continue
        
        vehicle = next(v for v in instance.vehicles if v.id == route.vehicle_id)
        garage = next(g for g in instance.garages if g.id == route.home_garage)
        
        current_x, current_y = garage.x, garage.y
        
        for mini_route in route.mini_routes:
            color = PRODUCT_COLORS[mini_route.product % len(PRODUCT_COLORS)]
            
            # Ligne garage -> dépôt
            depot = next(d for d in instance.depots if d.id == mini_route.depot_id)
            ax.annotate('', xy=(depot.x, depot.y), xytext=(current_x, current_y),
                        arrowprops=dict(arrowstyle='->', color=color, lw=1.5, alpha=0.7))
            current_x, current_y = depot.x, depot.y
            
            # Lignes dépôt -> stations
            for station_id, qty in mini_route.deliveries:
                station = next(s for s in instance.stations if s.id == station_id)
                ax.annotate('', xy=(station.x, station.y), xytext=(current_x, current_y),
                            arrowprops=dict(arrowstyle='->', color=color, lw=1.5, alpha=0.7))
                current_x, current_y = station.x, station.y
        
        # Retour au garage
        ax.annotate('', xy=(garage.x, garage.y), xytext=(current_x, current_y),
                    arrowprops=dict(arrowstyle='->', color='gray', lw=1, alpha=0.5, linestyle='--'))
    
    # Légende des produits
    product_legend = [
        mpatches.Patch(color=PRODUCT_COLORS[p % len(PRODUCT_COLORS)], 
                       label=f'Produit {p+1}')
        for p in range(instance.nb_products)
    ]
    
    # Ajouter la légende des produits
    legend1 = ax.legend(handles=product_legend, loc='upper right', title='Produits')
    ax.add_artist(legend1)
    
    # Informations sur la solution
    info_text = (
        f"Véhicules: {solution.get_nb_vehicles_used()}\n"
        f"Distance: {solution.get_total_distance():.1f}\n"
        f"Transitions: {solution.get_total_transitions()}\n"
        f"Coût total: {solution.get_total_cost():.1f}"
    )
    ax.text(0.02, 0.02, info_text, transform=ax.transAxes, fontsize=10,
            verticalalignment='bottom', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
    
    ax.set_title(f"Solution MPVRP-CC - Coût total: {solution.get_total_cost():.2f}")
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"Graphique sauvegardé: {save_path}")
    
    if show:
        plt.show()
    
    return fig, ax


def plot_vehicle_routes(solution: Solution, vehicle_ids: list = None, 
                        save_path: Optional[Path] = None, show: bool = True):
    """
    Visualise les routes de véhicules spécifiques.
    
    Args:
        solution: La solution
        vehicle_ids: Liste des IDs de véhicules à afficher (tous si None)
        save_path: Chemin pour sauvegarder
        show: Afficher le graphique
    """
    instance = solution.instance
    
    if vehicle_ids is None:
        vehicle_ids = [r.vehicle_id for r in solution.routes if r.mini_routes]
    
    n_vehicles = len(vehicle_ids)
    if n_vehicles == 0:
        print("Aucun véhicule utilisé")
        return
    
    cols = min(3, n_vehicles)
    rows = (n_vehicles + cols - 1) // cols
    
    fig, axes = plt.subplots(rows, cols, figsize=(6*cols, 5*rows))
    if n_vehicles == 1:
        axes = [axes]
    else:
        axes = axes.flatten()
    
    for idx, vehicle_id in enumerate(vehicle_ids):
        ax = axes[idx]
        route = next((r for r in solution.routes if r.vehicle_id == vehicle_id), None)
        
        if route is None or not route.mini_routes:
            ax.set_title(f"Véhicule {vehicle_id} - Non utilisé")
            continue
        
        # Dessiner l'instance
        plot_instance(instance, ax, title=f"Véhicule {vehicle_id}")
        
        vehicle = next(v for v in instance.vehicles if v.id == vehicle_id)
        garage = next(g for g in instance.garages if g.id == route.home_garage)
        
        current_x, current_y = garage.x, garage.y
        
        for mini_route in route.mini_routes:
            color = PRODUCT_COLORS[mini_route.product % len(PRODUCT_COLORS)]
            
            depot = next(d for d in instance.depots if d.id == mini_route.depot_id)
            ax.plot([current_x, depot.x], [current_y, depot.y], 
                    color=color, linewidth=2, alpha=0.7)
            current_x, current_y = depot.x, depot.y
            
            for station_id, _ in mini_route.deliveries:
                station = next(s for s in instance.stations if s.id == station_id)
                ax.plot([current_x, station.x], [current_y, station.y], 
                        color=color, linewidth=2, alpha=0.7)
                current_x, current_y = station.x, station.y
        
        # Retour
        ax.plot([current_x, garage.x], [current_y, garage.y], 
                color='gray', linewidth=1, linestyle='--', alpha=0.5)
        
        ax.set_title(f"Véhicule {vehicle_id} - Distance: {route.total_distance:.1f}")
    
    # Cacher les axes vides
    for idx in range(n_vehicles, len(axes)):
        axes[idx].set_visible(False)
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
    
    if show:
        plt.show()
    
    return fig


if __name__ == "__main__":
    from parser import parse_instance
    from solver import solve_instance
    
    # Test
    instance = parse_instance("../small/MPVRP_S_001_s9_d1_p2.dat")
    solution = solve_instance(instance, time_limit=30)
    
    plot_solution(solution)
