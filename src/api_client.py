"""
Client API pour la validation des solutions MPVRP-CC
Permet de valider les solutions via l'API fournie
"""
import requests
from pathlib import Path
from typing import Union, Optional, Dict, Any


class MPVRPAPIClient:
    """Client pour l'API MPVRP-CC."""
    
    # URL de l'API de production
    DEFAULT_API_URL = "https://mpvrp-cc.onrender.com"
    
    def __init__(self, base_url: str = None):
        """
        Initialise le client API.
        
        Args:
            base_url: URL de base de l'API (par défaut: https://mpvrp-cc.onrender.com)
        """
        self.base_url = (base_url or self.DEFAULT_API_URL).rstrip('/')
    
    def health_check(self) -> bool:
        """
        Vérifie si l'API est disponible.
        
        Returns:
            bool: True si l'API répond
        """
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            return response.status_code == 200
        except requests.RequestException:
            return False
    
    def verify_solution(
        self,
        instance_file: Union[str, Path],
        solution_file: Union[str, Path]
    ) -> Dict[str, Any]:
        """
        Vérifie une solution via l'API.
        
        Args:
            instance_file: Chemin vers le fichier d'instance
            solution_file: Chemin vers le fichier de solution
            
        Returns:
            dict: Réponse de l'API contenant:
                - feasible: bool
                - errors: list
                - metrics: dict
        """
        instance_file = Path(instance_file)
        solution_file = Path(solution_file)
        
        files = {
            'instance_file': (instance_file.name, open(instance_file, 'rb'), 'application/octet-stream'),
            'solution_file': (solution_file.name, open(solution_file, 'rb'), 'application/octet-stream')
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/model/verify",
                files=files,
                timeout=60
            )
            
            # Fermer les fichiers
            for f in files.values():
                f[1].close()
            
            if response.status_code == 200:
                return response.json()
            else:
                return {
                    'feasible': False,
                    'errors': [f"Erreur HTTP {response.status_code}: {response.text}"],
                    'metrics': {}
                }
                
        except requests.RequestException as e:
            return {
                'feasible': False,
                'errors': [f"Erreur de connexion: {str(e)}"],
                'metrics': {}
            }
    
    def generate_instance(
        self,
        id_instance: str,
        nb_vehicules: int,
        nb_depots: int,
        nb_garages: int,
        nb_stations: int,
        nb_produits: int,
        **kwargs
    ) -> Optional[bytes]:
        """
        Génère une nouvelle instance via l'API.
        
        Args:
            id_instance: Identifiant de l'instance
            nb_vehicules: Nombre de véhicules
            nb_depots: Nombre de dépôts
            nb_garages: Nombre de garages
            nb_stations: Nombre de stations
            nb_produits: Nombre de produits
            **kwargs: Paramètres optionnels (max_coord, min_capacite, etc.)
            
        Returns:
            bytes: Contenu du fichier d'instance ou None en cas d'erreur
        """
        payload = {
            'id_instance': id_instance,
            'nb_vehicules': nb_vehicules,
            'nb_depots': nb_depots,
            'nb_garages': nb_garages,
            'nb_stations': nb_stations,
            'nb_produits': nb_produits,
            **kwargs
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/generator/generate",
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                return response.content
            else:
                print(f"Erreur de génération: {response.status_code} - {response.text}")
                return None
                
        except requests.RequestException as e:
            print(f"Erreur de connexion: {e}")
            return None


def verify_solution_file(
    instance_path: Union[str, Path],
    solution_path: Union[str, Path],
    api_url: str = "https://mpvrp-cc.onrender.com"
) -> Dict[str, Any]:
    """
    Fonction utilitaire pour vérifier une solution.
    
    Args:
        instance_path: Chemin vers l'instance
        solution_path: Chemin vers la solution
        api_url: URL de l'API
        
    Returns:
        dict: Résultat de la vérification
    """
    client = MPVRPAPIClient(api_url)
    
    if not client.health_check():
        return {
            'feasible': False,
            'errors': ["L'API n'est pas disponible"],
            'metrics': {}
        }
    
    return client.verify_solution(instance_path, solution_path)


def print_verification_result(result: Dict[str, Any]):
    """Affiche le résultat de vérification de manière formatée."""
    import json
    
    print("\n" + "=" * 50)
    print("RÉPONSE DE L'API")
    print("=" * 50)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    
    print("\n" + "=" * 50)
    print("RÉSULTAT DE VÉRIFICATION")
    print("=" * 50)
    
    if result['feasible']:
        print("[OK] Solution VALIDE")
    else:
        print("[ERREUR] Solution INVALIDE")
    
    if result['errors']:
        print("\nErreurs:")
        for error in result['errors']:
            print(f"  - {error}")
    
    if result['metrics']:
        print("\nMétriques:")
        for key, value in result['metrics'].items():
            print(f"  {key}: {value}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) >= 3:
        instance_path = sys.argv[1]
        solution_path = sys.argv[2]
        api_url = sys.argv[3] if len(sys.argv) > 3 else "http://localhost:8000"
        
        result = verify_solution_file(instance_path, solution_path, api_url)
        print_verification_result(result)
    else:
        print("Usage: python api_client.py <instance_file> <solution_file> [api_url]")
