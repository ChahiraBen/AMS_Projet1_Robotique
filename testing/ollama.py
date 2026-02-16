import requests
import json

def ask_ollama(prompt, model="llama3.2:1b"):
    """Communique avec Ollama via son API HTTP"""
    url = "http://localhost:11434/api/generate"
    
    data = {
        "model": model,
        "prompt": prompt,
        "stream": False
    }
    
    try:
        response = requests.post(url, json=data)
        if response.status_code == 200:
            return response.json()['response']
        else:
            return f"Erreur: {response.status_code}"
    except requests.exceptions.ConnectionError:
        return "Erreur: Ollama n'est pas démarré. Lancez 'ollama serve' dans un autre terminal."
    except Exception as e:
        return f"Erreur: {e}"

# Test
if __name__ == "__main__":
    reponse = ask_ollama("Dis 'hello' en français que le mot 'hello'")
    print(reponse)