# Gérer les ressources en Python

## Pourquoi un context manager ?

Un context manager organise l’acquisition et la libération d’une ressource. Le bloc `with` appelle la méthode `__enter__` à l’entrée et `__exit__` à la sortie, y compris si une exception survient dans le bloc.

## Lire un fichier

```python
with open("notes.txt", encoding="utf-8") as fichier:
    contenu = fichier.read()
```

Le fichier est fermé lorsque l’exécution quitte le bloc `with`. Il n’est pas nécessaire d’appeler `close()` manuellement dans cet exemple.

## Créer un context manager

Le décorateur `contextlib.contextmanager` permet d’écrire un context manager à partir d’une fonction génératrice. Le code avant `yield` prépare la ressource ; un bloc `finally` permet de la libérer, même en cas d’erreur.

```python
from contextlib import contextmanager

@contextmanager
def ouvrir_notes(chemin):
    fichier = open(chemin, encoding="utf-8")
    try:
        yield fichier
    finally:
        fichier.close()
```

## À propos de cet exemple

Ce document pédagogique a été rédigé pour la démonstration d’Atelier. Il ne constitue pas une copie de la documentation officielle et n’a pas vocation à couvrir toutes les subtilités des context managers. Technologie suggérée : Python. Version suggérée : 3.14.
