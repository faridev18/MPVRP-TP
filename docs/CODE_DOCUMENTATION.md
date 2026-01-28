# Documentation Technique du Code MPVRP-CC

Ce document explique en détail le fonctionnement de chaque module du projet MPVRP-CC.

---

## 📁 Structure des Modules

```
src/
├── models.py          # Modèles de données (classes)
├── parser.py          # Lecture des fichiers d'instance
├── solver.py          # Algorithme de résolution OR-Tools
├── solution_writer.py # Écriture des fichiers de solution
├── api_client.py      # Communication avec l'API de validation
├── visualizer.py      # Génération des graphiques
└── main.py            # Point d'entrée CLI
```

---

## 1. `models.py` - Modèles de Données

Ce module définit toutes les structures de données utilisées dans le projet via des **dataclasses** Python.

### 1.1 Classe `Vehicle` (Véhicule)

```python
@dataclass
class Vehicle:
    id: int              # Identifiant unique
    capacity: int        # Capacité de chargement (en unités)
    home_garage: int     # ID du garage d'attache
    initial_product: int # Produit initial dans la citerne (1-indexed)
```

**Rôle** : Représente un camion-citerne de la flotte. Le `initial_product` détermine le produit que transporte le véhicule au départ. Un changement de produit nécessite un nettoyage coûteux.

---

### 1.2 Classe `Depot` (Dépôt)

```python
@dataclass
class Depot:
    id: int
    x: float            # Coordonnée X
    y: float            # Coordonnée Y
    stocks: List[int]   # Stock disponible par produit [produit0, produit1, ...]
```

**Rôle** : Point de chargement où les véhicules viennent remplir leur citerne. Chaque dépôt a un stock limité par produit.

---

### 1.3 Classe `Garage`

```python
@dataclass
class Garage:
    id: int
    x: float
    y: float
```

**Rôle** : Point de départ et d'arrivée des véhicules. Chaque véhicule est rattaché à un garage spécifique.

---

### 1.4 Classe `Station` (Station-service)

```python
@dataclass
class Station:
    id: int
    x: float
    y: float
    demands: List[int]  # Demande par produit [demande_p0, demande_p1, ...]
```

**Rôle** : Client à livrer. Chaque station peut avoir des demandes pour plusieurs produits différents.

---

### 1.5 Classe `Instance` (Instance du problème)

```python
@dataclass
class Instance:
    uuid: str                           # Identifiant unique
    nb_products: int                    # Nombre de produits différents
    nb_depots: int                      # Nombre de dépôts
    nb_garages: int                     # Nombre de garages
    nb_stations: int                    # Nombre de stations
    nb_vehicles: int                    # Nombre de véhicules
    transition_costs: List[List[float]] # Matrice de coûts de transition
    vehicles: List[Vehicle]
    depots: List[Depot]
    garages: List[Garage]
    stations: List[Station]
```

**Méthodes importantes** :

| Méthode | Description |
|---------|-------------|
| `get_distance(type1, id1, type2, id2)` | Calcule la distance euclidienne entre deux nœuds |
| `get_transition_cost(from_product, to_product)` | Retourne le coût de changement de produit |
| `get_total_demand(product)` | Somme des demandes pour un produit |
| `get_total_stock(product)` | Somme des stocks pour un produit |

**Formule de distance** :
$$d = \sqrt{(x_2 - x_1)^2 + (y_2 - y_1)^2}$$

---

### 1.6 Classe `MiniRoute` (Mini-tournée)

```python
@dataclass
class MiniRoute:
    product: int                      # Produit transporté (0-indexed)
    depot_id: int                     # Dépôt de chargement
    quantity_loaded: int              # Quantité chargée
    deliveries: List[Tuple[int, int]] # [(station_id, quantité), ...]
```

**Rôle** : Représente un cycle de livraison pour **un seul produit**. Un véhicule peut faire plusieurs mini-routes dans son trajet.

**Exemple** :
```
Véhicule part du garage → va au dépôt charger 5000L de produit 1 
→ livre station A (2000L) → livre station B (3000L) → retourne au dépôt
```

---

### 1.7 Classe `VehicleRoute` (Route complète d'un véhicule)

```python
@dataclass
class VehicleRoute:
    vehicle_id: int
    home_garage: int
    mini_routes: List[MiniRoute]
    total_distance: float
    total_transition_cost: float
    initial_product: int  # Produit initial du véhicule (0-indexed)
```

**Méthode clé** : `get_nb_transitions()`

```python
def get_nb_transitions(self) -> int:
    """Compte le nombre de changements de produit."""
    if len(self.mini_routes) == 0:
        return 0
    
    transitions = 0
    current_product = self.initial_product
    
    for mini_route in self.mini_routes:
        if mini_route.product != current_product:
            transitions += 1
            current_product = mini_route.product
    
    return transitions
```

**Logique** : Parcourt les mini-routes et compte chaque fois que le produit change par rapport au produit courant (en commençant par le produit initial du véhicule).

---

### 1.8 Classe `Solution`

```python
@dataclass
class Solution:
    instance: Instance
    routes: List[VehicleRoute]
    resolution_time: float
    processor: str
```

**Méthodes de calcul des métriques** :

| Méthode | Formule |
|---------|---------|
| `get_total_distance()` | $\sum_{r \in routes} r.total\_distance$ |
| `get_total_transition_cost()` | $\sum_{r \in routes} r.total\_transition\_cost$ |
| `get_total_cost()` | $distance + transition\_cost$ |
| `get_nb_vehicles_used()` | Nombre de routes avec au moins 1 mini-route |

---

## 2. `parser.py` - Lecture des Instances

### 2.1 Fonction `parse_instance(filepath)`

**Entrée** : Chemin vers un fichier `.dat`

**Sortie** : Objet `Instance`

**Algorithme** :

```
1. Lire toutes les lignes non vides du fichier
2. Ligne 1: Extraire l'UUID (format: #uuid)
3. Ligne 2: Lire les paramètres (nb_products, nb_depots, nb_garages, nb_stations, nb_vehicles)
4. Lignes suivantes: Lire la matrice de transition (nb_products × nb_products)
5. Lire les nb_vehicles véhicules
6. Lire les nb_depots dépôts
7. Lire les nb_garages garages
8. Lire les nb_stations stations
9. Construire et retourner l'objet Instance
```

**Format d'un fichier d'instance** :
```
#UUID-12345
2 1 1 9 3                     ← 2 produits, 1 dépôt, 1 garage, 9 stations, 3 véhicules
0.0 15.6                      ← Matrice transition: P1→P1=0, P1→P2=15.6
22.0 0.0                      ← P2→P1=22, P2→P2=0
1 5000 1 1                    ← Véhicule 1: capacité=5000, garage=1, produit_initial=1
2 4500 1 2                    ← Véhicule 2: capacité=4500, garage=1, produit_initial=2
...
1 50.0 30.0 10000 8000        ← Dépôt 1: x=50, y=30, stock_P1=10000, stock_P2=8000
1 25.0 25.0                   ← Garage 1: x=25, y=25
1 10.0 20.0 500 300           ← Station 1: x=10, y=20, demande_P1=500, demande_P2=300
```

---

### 2.2 Fonction `validate_instance(instance)`

**Validations effectuées** :

1. **Stock suffisant** : Pour chaque produit, vérifie que `stock_total ≥ demande_totale`
2. **Garages valides** : Chaque véhicule est assigné à un garage existant
3. **Produits initiaux valides** : Chaque véhicule a un produit initial dans `[1, nb_products]`

---

## 3. `solver.py` - Algorithme de Résolution

### 3.1 Vue d'ensemble

Le solveur utilise **Google OR-Tools** avec une approche de **décomposition par produit**.

```
┌─────────────────────────────────────────────────┐
│                ALGORITHME PRINCIPAL              │
├─────────────────────────────────────────────────┤
│ 1. Initialiser la solution (routes vides)        │
│ 2. Pour chaque produit p:                        │
│    ├─ Identifier stations ayant besoin de p     │
│    ├─ Résoudre VRP avec OR-Tools                │
│    └─ Si échec: utiliser solution gloutonne     │
│ 3. Calculer les métriques finales               │
└─────────────────────────────────────────────────┘
```

---

### 3.2 Classe `MPVRPSolver`

#### Constructeur

```python
def __init__(self, instance: Instance, time_limit: int = 60):
    self.instance = instance
    self.time_limit = time_limit
```

---

#### Méthode `solve()`

```python
def solve(self) -> Solution:
    # 1. Créer une route vide pour chaque véhicule
    for vehicle in self.instance.vehicles:
        route = VehicleRoute(
            vehicle_id=vehicle.id,
            home_garage=vehicle.home_garage,
            initial_product=vehicle.initial_product - 1  # Convertir en 0-indexed
        )
        solution.routes.append(route)
    
    # 2. Initialiser les demandes et stocks restants
    remaining_demands = self._get_initial_demands()  # {station_id: {product: qty}}
    remaining_stocks = self._get_initial_stocks()    # {depot_id: {product: qty}}
    
    # 3. Résoudre produit par produit
    for product in range(self.instance.nb_products):
        self._solve_for_product_complete(...)
    
    # 4. Calculer les métriques
    self._compute_metrics(solution)
    
    return solution
```

---

#### Méthode `_solve_for_product_complete()`

Résout le VRP pour un produit donné en **plusieurs itérations** si nécessaire.

```
BOUCLE (max 100 itérations):
    1. Identifier les stations qui ont encore besoin de ce produit
    2. Si aucune → STOP (toutes les demandes sont satisfaites)
    3. Identifier les dépôts ayant du stock
    4. Si aucun → STOP (plus de stock)
    5. Appeler _solve_vrp_iteration() avec OR-Tools
    6. Si échec → Appeler _greedy_deliver() comme fallback
```

---

#### Méthode `_solve_vrp_iteration()` - Cœur de l'algorithme

Cette méthode utilise OR-Tools pour résoudre un **VRP classique avec contraintes de capacité**.

**Étape 1 : Construire le graphe**
```
Nœuds = [Dépôt virtuel (0)] + [Stations ayant besoin du produit]
Véhicules = Flotte triée par usage et préférence de produit
```

**Étape 2 : Créer les callbacks**

```python
# Callback de distance
def distance_callback(from_index, to_index):
    from_node = manager.IndexToNode(from_index)
    to_node = manager.IndexToNode(to_index)
    return distance(from_node, to_node)

# Callback de demande
def demand_callback(from_index):
    from_node = manager.IndexToNode(from_index)
    return demands[from_node]
```

**Étape 3 : Ajouter les contraintes**

```python
# Contrainte de capacité
routing.AddDimensionWithVehicleCapacity(
    demand_callback_index,
    0,                    # Pas de slack
    vehicle_capacities,   # Capacités des véhicules
    True,                 # Cumul commence à 0
    'Capacity'
)

# Permettre de ne pas visiter tous les nœuds (disjunction)
for node in range(1, num_nodes):
    routing.AddDisjunction([manager.NodeToIndex(node)], 100000)  # Pénalité
```

**Étape 4 : Configurer la recherche**

```python
search_parameters.first_solution_strategy = FirstSolutionStrategy.PATH_CHEAPEST_ARC
search_parameters.local_search_metaheuristic = LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
search_parameters.time_limit.seconds = time_limit
```

| Stratégie | Description |
|-----------|-------------|
| `PATH_CHEAPEST_ARC` | Construction gloutonne : ajoute l'arc le moins coûteux à chaque étape |
| `GUIDED_LOCAL_SEARCH` | Amélioration locale guidée par des pénalités sur les arcs fréquemment utilisés |

**Étape 5 : Extraire la solution**

```python
for vehicle_idx in range(num_vehicles):
    index = routing.Start(vehicle_idx)
    route_stations = []
    
    while not routing.IsEnd(index):
        node = manager.IndexToNode(index)
        if node > 0:  # Pas le dépôt
            station = stations[node - 1]
            route_stations.append((station.id, demand))
        index = assignment.Value(routing.NextVar(index))
    
    # Créer la mini-route si des livraisons ont été faites
    if route_stations:
        mini_route = MiniRoute(product=product, depot_id=..., deliveries=route_stations)
        vehicle_route.mini_routes.append(mini_route)
```

---

#### Méthode `_greedy_deliver()` - Fallback glouton

Si OR-Tools échoue, cette méthode garantit que toutes les demandes sont satisfaites.

```
1. Trier les stations par demande décroissante
2. Pour chaque véhicule (trié par usage):
   a. Remplir le véhicule jusqu'à sa capacité
   b. Créer une mini-route avec les livraisons
   c. Mettre à jour les demandes et stocks restants
3. Répéter jusqu'à ce que toutes les demandes soient satisfaites
```

---

#### Méthode `_compute_metrics()`

Calcule la distance totale et le coût de transition pour chaque route.

```python
for route in solution.routes:
    total_distance = 0.0
    total_transition = 0.0
    current_product = vehicle.initial_product - 1
    current_x, current_y = garage.x, garage.y
    
    for mini_route in route.mini_routes:
        # Coût de transition si changement de produit
        if mini_route.product != current_product:
            transition_cost = instance.get_transition_cost(current_product, mini_route.product)
            total_transition += transition_cost
            current_product = mini_route.product
        
        # Distance vers le dépôt
        total_distance += distance(current, depot)
        
        # Distances vers les stations
        for station_id, _ in mini_route.deliveries:
            total_distance += distance(current, station)
        
    # Retour au garage
    total_distance += distance(current, garage)
```

---

## 4. `solution_writer.py` - Écriture des Solutions

### 4.1 Fonction `write_solution()`

**Format de sortie** (conforme à l'API) :

```
id: garage - depot [qty] - station (qty) - ... - garage
id: product(cost) - product(cost) - ...

[ligne vide entre véhicules]

nb_vehicles_used
nb_transitions
total_transition_cost
total_distance
processor
resolution_time
```

**Exemple** :
```
1: 1 - 1 [3355] - 2 (3355) - 1
1: 0(0.0) - 0(0.0) - 0(0.0) - 0(0.0)

2: 1 - 1 [2500] - 3 (2500) - 1
2: 1(0.0) - 1(0.0) - 1(0.0) - 1(0.0)

2
1
15.6
450.5
Intel Core i7
2.35
```

---

### 4.2 Fonction `validate_solution_locally()`

**Validations** :

1. **Demandes satisfaites** : Chaque station reçoit au moins sa demande pour chaque produit
2. **Capacité respectée** : Aucune mini-route ne dépasse la capacité du véhicule
3. **Équilibre chargé/livré** : Quantité chargée = quantité livrée pour chaque mini-route

---

## 5. `api_client.py` - Client API

### 5.1 Classe `MPVRPAPIClient`

**URL par défaut** : `https://mpvrp-cc.onrender.com`

**Méthodes** :

| Méthode | Description |
|---------|-------------|
| `health_check()` | Vérifie si l'API est disponible |
| `verify_solution(instance_file, solution_file)` | Envoie les fichiers pour validation |
| `generate_instance(...)` | Génère une nouvelle instance via l'API |

---

### 5.2 Requête de vérification

```python
files = {
    'instance_file': (nom, contenu, 'application/octet-stream'),
    'solution_file': (nom, contenu, 'application/octet-stream')
}

response = requests.post(f"{base_url}/model/verify", files=files)
```

**Réponse** :
```json
{
    "feasible": true,
    "errors": [],
    "metrics": {
        "total_distance": 888.14,
        "total_transition_cost": 90.8,
        "nb_vehicles": 3,
        "nb_transitions": 5
    }
}
```

---

## 6. `visualizer.py` - Visualisation

### 6.1 Fonction `plot_instance()`

Dessine l'instance (sans les routes) :
- **Garages** : Carrés noirs
- **Dépôts** : Triangles bleus
- **Stations** : Cercles rouges (taille proportionnelle à la demande)

---

### 6.2 Fonction `plot_solution()`

Dessine la solution complète avec les routes colorées par produit.

```python
# Couleurs par produit
PRODUCT_COLORS = ['#e74c3c', '#3498db', '#2ecc71', '#f39c12', ...]

# Pour chaque mini-route
color = PRODUCT_COLORS[mini_route.product % len(PRODUCT_COLORS)]
ax.annotate('', xy=(dest), xytext=(origin), arrowprops=dict(color=color))
```

---

## 7. `main.py` - Point d'Entrée

### 7.1 Arguments CLI

| Argument | Description |
|----------|-------------|
| `instance` | Chemin vers le fichier d'instance |
| `-o, --output` | Chemin du fichier de sortie |
| `-t, --time-limit` | Limite de temps (défaut: 60s) |
| `-v, --verify` | Activer la vérification API |
| `--api-url` | URL de l'API |
| `-b, --batch` | Mode batch (résoudre un dossier) |
| `--output-folder` | Dossier de sortie pour le batch |

### 7.2 Exemples d'utilisation

```bash
# Résoudre une instance
python main.py ../small/MPVRP_S_001.dat -t 60

# Résoudre et vérifier via l'API
python main.py ../small/MPVRP_S_001.dat --verify

# Mode batch
python main.py --batch ../small --output-folder ../solutions
```

---

## 8. Flux de Données Complet

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  Fichier     │ ──► │   parser.py  │ ──► │   Instance   │
│  .dat        │     │              │     │   (models)   │
└──────────────┘     └──────────────┘     └──────┬───────┘
                                                  │
                                                  ▼
                                          ┌──────────────┐
                                          │  solver.py   │
                                          │  (OR-Tools)  │
                                          └──────┬───────┘
                                                  │
                                                  ▼
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  Fichier     │ ◄── │ solution_    │ ◄── │   Solution   │
│  Sol_*.dat   │     │ writer.py    │     │   (models)   │
└──────────────┘     └──────────────┘     └──────┬───────┘
                                                  │
                     ┌──────────────┐             │
                     │ visualizer.py│ ◄───────────┤
                     └──────────────┘             │
                                                  ▼
                     ┌──────────────┐     ┌──────────────┐
                     │ API externe  │ ◄── │ api_client.py│
                     └──────────────┘     └──────────────┘
```

---

## 9. Formules Mathématiques

### Coût Total
$$C_{total} = D_{total} + T_{total}$$

Où :
- $D_{total}$ = distance totale parcourue
- $T_{total}$ = somme des coûts de transition

### Distance Euclidienne
$$d(A, B) = \sqrt{(x_B - x_A)^2 + (y_B - y_A)^2}$$

### Nombre de Transitions
$$N_{transitions} = \sum_{v \in Véhicules} \sum_{i=1}^{|R_v|} \mathbb{1}[p_{i} \neq p_{i-1}]$$

Où $p_0$ = produit initial du véhicule.

---

## 10. Conseils de Débogage

| Symptôme | Cause probable | Solution |
|----------|----------------|----------|
| Demandes non satisfaites | Capacité insuffisante | Augmenter `time_limit` ou vérifier les capacités |
| Erreur API 400 | Format de solution incorrect | Vérifier le format des lignes (préfixe `id:`) |
| Transitions incorrectes | Oubli du produit initial | Vérifier `initial_product` dans `VehicleRoute` |
| Solution vide | Pas de véhicules assignés | Vérifier le parsing des véhicules |

---

*Documentation générée pour le projet MPVRP-CC - Janvier 2026*
