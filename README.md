# Dolcèra — Application de gestion (version Flask)

Application de gestion des ventes (Magasin + Glovo), des charges, et dashboard,
pour la pâtisserie Dolcèra. Écrite en Python (Flask) + SQLite — aucune base de
données externe à installer.

## 1. Installation

Il te faut Python 3.9+ installé sur ton PC.

```bash
cd dolcera_flask
python -m venv venv
source venv/bin/activate        # sur Windows : venv\Scripts\activate
pip install -r requirements.txt
```

## 2. Lancer l'application

```bash
python app.py
```

La console affiche quelque chose comme :
```
* Running on http://127.0.0.1:5000
* Running on http://192.168.1.24:5000
```

- Sur ce même PC : ouvre **http://localhost:5000**
- Sur ton iPhone (ou tout autre appareil) : connecte-le au **même réseau Wi-Fi**
  que le PC, puis ouvre l'adresse du type **http://192.168.1.24:5000** (celle
  affichée dans ta console, pas celle-ci). Tu peux l'ajouter à l'écran
  d'accueil depuis Safari (Partager → Sur l'écran d'accueil).

⚠️ Important : contrairement à l'appli web que je t'ai donnée en premier,
cette version Flask ne fonctionne que **pendant que ton PC est allumé et que
`python app.py` tourne**. Si tu veux y accéder depuis n'importe où (pas
seulement à la maison sur le même Wi-Fi), il faut l'héberger sur un serveur —
voir la section 4 ci-dessous.

## 3. Les données

Toutes tes ventes, charges et produits sont stockées dans un seul fichier :
**`dolcera.db`** (créé automatiquement au premier lancement, dans le même
dossier que `app.py`). Le catalogue des 39 produits Dolcèra est pré-rempli
automatiquement au premier démarrage.

**Sauvegarde** : pense à copier régulièrement le fichier `dolcera.db` ailleurs
(clé USB, Google Drive…) pour ne pas perdre tes données. Tu peux aussi
exporter chaque tableau (ventes, charges) en CSV depuis l'appli (bouton
"Exporter CSV").

## 4. Héberger l'appli en ligne (accès depuis n'importe où, gratuit)

Si tu veux que l'appli soit accessible sans que ton PC reste allumé, plusieurs
plateformes offrent un hébergement gratuit pour de petites applications Flask :

- **Render.com** (plan gratuit) — le plus simple, connecte ton code à un dépôt
  GitHub et Render s'occupe du reste.
- **PythonAnywhere** (plan gratuit) — pensé spécifiquement pour Flask/Django.
- **Railway.app** (crédit gratuit limité).

⚠️ Ces plans gratuits mettent parfois l'appli "en veille" après une période
d'inactivité (le premier chargement peut alors prendre 10-30 secondes), et le
stockage SQLite sur ces plateformes gratuites n'est pas toujours persistant
d'un déploiement à l'autre — vérifie les conditions de la plateforme choisie.
Si tu veux, je peux t'accompagner pas à pas pour le déploiement sur l'une
d'elles.

## 5. Fonctionnement métier (résumé)

- **Magasin** : chaque vente est saisie manuellement (produit, quantité, prix).
- **Glovo** : le prix Glovo = prix magasin **+ 20 % HT**, calculé
  automatiquement (modifiable). Glovo prélève **23,8 %** de commission sur le
  montant brut ; le "Net" affiché est ce qui te sera réellement viré.
  - Statut **Livrée** → comptée normalement.
  - Statut **Annulée — sortie du magasin** → comptée comme une vente payée
    (le produit a quitté le magasin, donc tu dois être payé), avec un badge
    doré pour la repérer facilement lors de la vérification du virement Glovo.
  - Statut **Annulée — non sortie** → exclue du chiffre d'affaires (aucun
    gain, le produit n'a jamais quitté le magasin).
- **Charges** : à catégoriser (matières premières, loyer, salaires…).
- **Dashboard** : vue d'ensemble combinant Magasin + Glovo (net) + charges,
  avec un filtre de période (aujourd'hui / 7 jours / mois / année / tout /
  personnalisé) commun à tous les onglets.

## 6. Structure du projet

```
dolcera_flask/
├── app.py                 # Toute la logique (routes, calculs, base SQLite)
├── requirements.txt
├── dolcera.db              # créé automatiquement
├── static/
│   ├── style.css          # thème bleu/jaune Dolcèra
│   ├── logo.png
│   ├── tile_frame.svg      # motif faïence (cadres des cartes)
│   └── tile_header.svg     # motif faïence (en-tête, en blanc/or)
└── templates/
    ├── base.html
    ├── _period.html
    ├── dashboard.html
    ├── magasin.html
    ├── glovo.html
    ├── charges.html
    └── produits.html
```

Bon courage avec Dolcèra ! 🍰
