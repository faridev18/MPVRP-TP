#!/usr/bin/env python3
"""
Script principal pour résoudre les instances MPVRP-CC
Multi-Product Vehicle Routing Problem with Changeover Cost

Usage:
    python main.py <instance_file> [--output <output_file>] [--time-limit <seconds>] [--verify]
    python main.py --batch <folder> [--output-folder <folder>] [--time-limit <seconds>]
"""
import argparse
import sys
from pathlib import Path

# Ajouter le répertoire src au path
sys.path.insert(0, str(Path(__file__).parent))

from parser import parse_instance, validate_instance
from solver import solve_instance
from solution_writer import write_solution, format_solution_for_display, validate_solution_locally
from api_client import verify_solution_file, print_verification_result


def solve_single_instance(
    instance_path: Path,
    output_path: Path = None,
    time_limit: int = None,
    verify: bool = False,
    api_url: str = "http://localhost:8000"
):
    """Résout une seule instance."""
    print(f"\n{'='*60}")
    print(f"Résolution de: {instance_path.name}")
    print(f"{'='*60}")
    
    # Parser l'instance
    print("\n1. Parsing de l'instance...")
    instance = parse_instance(instance_path)
    print(instance)
    
    # Valider l'instance
    print("\n2. Validation de l'instance...")
    if not validate_instance(instance):
        print("[ATTENTION] Instance invalide, tentative de resolution quand meme...")
    else:
        print("[OK] Instance valide")
    
    # Résoudre
    if time_limit:
        print(f"\n3. Résolution (limite: {time_limit}s)...")
    else:
        print("\n3. Résolution (sans limite de temps)...")
    solution = solve_instance(instance, time_limit)
    
    # Afficher la solution
    print(format_solution_for_display(solution))
    
    # Validation locale
    print("\n4. Validation locale...")
    is_valid, errors = validate_solution_locally(solution)
    if is_valid:
        print("[OK] Solution localement valide")
    else:
        print("[ERREUR] Solution localement invalide:")
        for e in errors:
            print(f"  - {e}")
    
    # Écrire la solution
    if output_path is None:
        output_path = instance_path.parent.parent / "solutions" / f"Sol_{instance_path.name}"
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    write_solution(solution, output_path)
    print(f"\n5. Solution écrite dans: {output_path}")
    
    # Vérification via API
    if verify:
        print("\n6. Vérification via API...")
        result = verify_solution_file(instance_path, output_path, api_url)
        print_verification_result(result)
    
    return solution


def solve_batch(
    input_folder: Path,
    output_folder: Path = None,
    time_limit: int = None,
    verify: bool = False,
    api_url: str = "https://mpvrp-cc.onrender.com"
):
    """Résout toutes les instances d'un dossier."""
    if output_folder is None:
        output_folder = input_folder.parent / "solutions"
    
    output_folder.mkdir(parents=True, exist_ok=True)
    
    instance_files = sorted(input_folder.glob("*.dat"))
    print(f"Trouvé {len(instance_files)} instances dans {input_folder}")
    if verify:
        print(f"Vérification API activée: {api_url}")
    
    results = []
    
    for i, instance_path in enumerate(instance_files, 1):
        print(f"\n[{i}/{len(instance_files)}] ", end="")
        
        output_path = output_folder / f"Sol_{instance_path.name}"
        
        try:
            solution = solve_single_instance(
                instance_path,
                output_path,
                time_limit,
                verify=verify,
                api_url=api_url
            )
            results.append({
                'instance': instance_path.name,
                'status': 'OK',
                'cost': solution.get_total_cost(),
                'distance': solution.get_total_distance(),
                'transitions': solution.get_total_transitions(),
                'time': solution.resolution_time
            })
        except Exception as e:
            print(f"[ERREUR] {e}")
            results.append({
                'instance': instance_path.name,
                'status': 'ERREUR',
                'error': str(e)
            })
    
    # Résumé
    print("\n" + "="*80)
    print("RÉSUMÉ DU BATCH")
    print("="*80)
    print(f"{'Instance':<40} {'Status':<10} {'Coût':>12} {'Distance':>12} {'Temps':>8}")
    print("-"*80)
    
    for r in results:
        if r['status'] == 'OK':
            print(f"{r['instance']:<40} {'OK':<10} {r['cost']:>12.2f} {r['distance']:>12.2f} {r['time']:>7.2f}s")
        else:
            print(f"{r['instance']:<40} {'ERREUR':<10} {r.get('error', 'Unknown error')}")
    
    success = sum(1 for r in results if r['status'] == 'OK')
    print("-"*80)
    print(f"Succès: {success}/{len(results)}")


def main():
    parser = argparse.ArgumentParser(
        description="Solveur MPVRP-CC - Multi-Product Vehicle Routing Problem with Changeover Cost"
    )
    
    parser.add_argument(
        'instance',
        nargs='?',
        help="Chemin vers le fichier d'instance (.dat)"
    )
    
    parser.add_argument(
        '--output', '-o',
        help="Chemin vers le fichier de sortie"
    )
    
    parser.add_argument(
        '--time-limit', '-t',
        type=int,
        default=None,
        help="Limite de temps en secondes (par défaut: sans limite)"
    )
    
    parser.add_argument(
        '--verify', '-v',
        action='store_true',
        help="Vérifier la solution via l'API"
    )
    
    parser.add_argument(
        '--api-url',
        default="https://mpvrp-cc.onrender.com",
        help="URL de l'API de vérification"
    )
    
    parser.add_argument(
        '--batch', '-b',
        help="Résoudre toutes les instances d'un dossier"
    )
    
    parser.add_argument(
        '--output-folder',
        help="Dossier de sortie pour le mode batch"
    )
    
    args = parser.parse_args()
    
    if args.batch:
        # Mode batch
        input_folder = Path(args.batch)
        output_folder = Path(args.output_folder) if args.output_folder else None
        solve_batch(input_folder, output_folder, args.time_limit, args.verify, args.api_url)
    
    elif args.instance:
        # Mode simple
        instance_path = Path(args.instance)
        output_path = Path(args.output) if args.output else None
        solve_single_instance(
            instance_path,
            output_path,
            args.time_limit,
            args.verify,
            args.api_url
        )
    
    else:
        # Mode interactif - résoudre une petite instance par défaut
        print("MPVRP-CC Solver - Mode démo")
        print("-" * 40)
        
        # Chercher une instance small
        small_folder = Path(__file__).parent.parent / "small"
        if small_folder.exists():
            instance_files = list(small_folder.glob("*.dat"))
            if instance_files:
                print(f"Résolution de l'instance de démo: {instance_files[0].name}")
                solve_single_instance(instance_files[0], time_limit=30)
            else:
                print("Aucune instance trouvée dans le dossier 'small'")
                parser.print_help()
        else:
            print("Dossier 'small' non trouvé")
            parser.print_help()


if __name__ == "__main__":
    main()
