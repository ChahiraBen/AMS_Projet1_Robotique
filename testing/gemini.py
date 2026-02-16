import requests
import json

# Remplacez par votre clé
API_KEY = "AIzaSyAYwOwah1W9KRJmQO0Sh2TvUJMKM7Dz7o8" 

def ask_gemini(prompt):
    # Changement : on utilise 'v1' au lieu de 'v1beta'
    # Et on s'assure que le nom du modèle est exact
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={API_KEY}"

    headers = {
        "Content-Type": "application/json"
    }

    data = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ]
    }

    try:
        response = requests.post(url, headers=headers, json=data)
        
        if response.status_code != 200:
            print(f"Détails de l'erreur : {response.text}")
            return f"Erreur {response.status_code}"

        response_json = response.json()
        
        # Extraction sécurisée du texte
        return response_json["candidates"][0]["content"]["parts"][0]["text"]

    except Exception as e:
        return f"Erreur de connexion : {e}"

if __name__ == "__main__":
    print("Envoi de la requête...")
    # Test avec un prompt simple
    resultat = ask_gemini("Dis bonjour sans utiliser le mot bonjour")
    print("-" * 20)
    print(resultat)