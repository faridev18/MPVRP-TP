# MPVRP-CC : Multi-Product Vehicle Routing Problem with Changeover Cost

## 📋 Description du Problème

Le **MPVRP-CC** (Multi-Product Vehicle Routing Problem with Changeover Cost) est un problème d'optimisation logistique qui vise à organiser la distribution efficace de plusieurs types de produits (par exemple, différents carburants) depuis un ensemble de dépôts vers un réseau de stations-service.

### Caractéristiques principales :
- **Multi-produit** : Plusieurs types de produits à distribuer
- **Coût de changement** : Changer le produit transporté par un véhicule nécessite un nettoyage de citerne, ce qui engendre un coût supplémentaire
- **Flotte hétérogène** : Véhicules de capacités différentes, attachés à des garages spécifiques

## 🏗️ Structure du Projet

```
MPVRP-TP/
├── docs/                   # Documentation
│   ├── api.json           # Spécification OpenAPI
│   ├── instance_description.txt
│   ├── problem_definition.txt
│   └── solution_description.txt
├── small/                  # Petites instances (5-50 stations)
├── medium/                 # Moyennes instances (50-100 stations)
├── large/                  # Grandes instances (100-200 stations)
├── solutions/              # Solutions générées
├── src/                    # Code source
│   ├── models.py          # Modèles de données
│   ├── parser.py          # Parsing des fichiers .dat
│   ├── solver.py          # Solveur OR-Tools
│   ├── solution_writer.py # Écriture des solutions
│   ├── api_client.py      # Client API de validation
│   ├── visualizer.py      # Visualisation graphique
│   └── main.py            # Script principal
├── requirements.txt        # Dépendances Python
└── README.md              # Ce fichier
```

## 🚀 Installation

### 1. Créer un environnement virtuel (recommandé)

```bash
python -m venv venv

# Windows
.\venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 2. Installer les dépendances

```bash
pip install -r requirements.txt
```

## 💻 Utilisation

### Résoudre une instance unique

```bash
cd src
python main.py ../small/MPVRP_S_001_s9_d1_p2.dat
```

### Avec options

```bash
# Spécifier le fichier de sortie et la limite de temps
python main.py ../small/MPVRP_S_001_s9_d1_p2.dat -o ../solutions/ma_solution.dat -t 120

# Vérifier via l'API
python main.py ../small/MPVRP_S_001_s9_d1_p2.dat --verify --api-url http://localhost:8000
```

### Résolution en batch

```bash
# Résoudre toutes les instances du dossier small
python main.py --batch ../small --time-limit 60

# Avec dossier de sortie personnalisé
python main.py --batch ../small --output-folder ../solutions/small
```

### Mode démo (sans arguments)

```bash
python main.py
```

## 📊 Visualisation

```python
from parser import parse_instance
from solver import solve_instance
from visualizer import plot_solution

instance = parse_instance("../small/MPVRP_S_001_s9_d1_p2.dat")
solution = solve_instance(instance, time_limit=60)
plot_solution(solution, save_path="solution.png")
```

## 🔧 API de Validation

Si l'API de validation est disponible :

```python
from api_client import verify_solution_file, print_verification_result

result = verify_solution_file(
    "../small/MPVRP_S_001_s9_d1_p2.dat",
    "../solutions/Sol_MPVRP_S_001_s9_d1_p2.dat",
    api_url="http://localhost:8000"
)
print_verification_result(result)
```

## 📐 Format des Fichiers

### Instance (.dat)
```
# UUID
nb_products nb_depots nb_garages nb_stations nb_vehicles
[Matrice de transition nb_products x nb_products]
[Véhicules: id capacité garage produit_initial]
[Dépôts: id x y stock_p1 stock_p2 ...]
[Garages: id x y]
[Stations: id x y demande_p1 demande_p2 ...]
```

### Solution (.dat)
```
vehicle_id:
garage - depot [qty_loaded] - station (qty_delivered) - ... - garage
vehicle_id:
product(cumul_cost) - product(cumul_cost) - ...

[Métriques: nb_vehicles, nb_transitions, total_transition_cost, total_distance, processor, time]
```

## 🧮 Approche de Résolution

Le solveur utilise **Google OR-Tools** avec une approche de décomposition par produit :

1. **Décomposition** : Pour chaque produit, on identifie les stations ayant besoin de ce produit
2. **VRP par produit** : On résout un VRP classique avec contraintes de capacité
3. **Optimisation des transitions** : Les véhicules sont assignés en priorité aux produits correspondant à leur configuration initiale
4. **Agrégation** : Les mini-routes sont agrégées pour former la solution globale

### Stratégies OR-Tools utilisées :
- `PATH_CHEAPEST_ARC` : Construction initiale gloutonne
- `GUIDED_LOCAL_SEARCH` : Amélioration locale guidée

## 📈 Objectifs d'Optimisation

L'objectif est de **minimiser le coût total** composé de :
- **Coût de transport** : Proportionnel à la distance totale parcourue
- **Coût de transition** : Somme des coûts de nettoyage lors des changements de produit

## ⚠️ Contraintes

- ✅ Toutes les demandes doivent être satisfaites
- ✅ La capacité des véhicules ne doit pas être dépassée
- ✅ Chaque véhicule doit partir et revenir à son garage assigné
- ✅ Quantité chargée = Quantité livrée pour chaque mini-route

## 📝 Licence

Ce projet est développé dans le cadre d'un TP universitaire.

## 👥 Auteurs

MPVRP-CC Team - Janvier 2026
