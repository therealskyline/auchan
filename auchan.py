from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime
import json
import os
import argparse
import sys
from pathlib import Path

REDIRECT_TO = "https://www.auchan.fr/catalogue/"
LOG_FILE    = "visits.json"
HF_REPO     = "silyan/helping"

# Variables globales pour HF
HF_TOKEN = None
HF_ENABLED = False

def upload_to_hf():
    """Upload le fichier JSON vers Hugging Face"""
    if not HF_ENABLED or not HF_TOKEN:
        return
    
    try:
        from huggingface_hub import HfApi
        api = HfApi(token=HF_TOKEN)
        
        if os.path.exists(LOG_FILE):
            api.upload_file(
                path_or_fileobj=LOG_FILE,
                path_in_repo="visits.json",
                repo_id=HF_REPO,
                repo_type="dataset"
            )
            print(f"✅ Fichier uploadé vers {HF_REPO}")
    except Exception as e:
        print(f"⚠️  Erreur upload HF: {e}")

def save_visit(entry):
    visits = []
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r") as f:
            try:
                visits = json.load(f)
            except json.JSONDecodeError:
                visits = []
    visits.append(entry)
    with open(LOG_FILE, "w") as f:
        json.dump(visits, f, indent=2, ensure_ascii=False)
    
    # Upload vers HF après chaque sauvegarde
    if HF_ENABLED:
        upload_to_hf()

class RedirectHandler(BaseHTTPRequestHandler):
    def get_client_ip(self):
        """Récupère l'IP réelle du client (même derrière un proxy)"""
        # Proxy headers (Cloudflare, Render, etc.)
        if 'X-Forwarded-For' in self.headers:
            return self.headers['X-Forwarded-For'].split(',')[0].strip()
        if 'CF-Connecting-IP' in self.headers:
            return self.headers['CF-Connecting-IP']
        
        # Fallback: IP directe
        return self.client_address[0]
    
    def do_GET(self):
        entry = {
            "timestamp":  datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "ip":         self.get_client_ip(),
            "path":       self.path,
            "user_agent": self.headers.get("User-Agent", "inconnu"),
            "referer":    self.headers.get("Referer", None),
            "language":   self.headers.get("Accept-Language", None),
        }
        save_visit(entry)
        print(f"✅ [{entry['timestamp']}] {entry['ip']} → sauvegardé dans {LOG_FILE}")

        self.send_response(302)
        self.send_header("Location", REDIRECT_TO)
        self.end_headers()

    def log_message(self, format, *args):
        pass

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Serveur de redirection avec logging HF")
    parser.add_argument(
        "--hf",
        type=str,
        help="Token Hugging Face (ou chemin vers fichier contenant le token)"
    )
    args = parser.parse_args()
    
    # Configuration HF
    if args.hf:
        HF_ENABLED = True
        # Si c'est un chemin, lire le token du fichier
        if os.path.exists(args.hf):
            with open(args.hf, "r") as f:
                HF_TOKEN = f.read().strip()
        else:
            HF_TOKEN = args.hf
        print(f"✅ Token HF chargé")
    
    server = HTTPServer(("0.0.0.0", 8080), RedirectHandler)
    print(f"🚀 Serveur sur port 8080 → {REDIRECT_TO}")
    if HF_ENABLED:
        print(f"📤 Upload HF activé → {HF_REPO}")
    server.serve_forever()
