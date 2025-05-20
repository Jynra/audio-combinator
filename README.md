# Audio Combinator

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
![Platform](https://img.shields.io/badge/platform-Linux-green.svg)

Une application graphique permettant de combiner plusieurs sorties audio sous Linux. Idéale pour diffuser le son simultanément sur plusieurs périphériques audio, comme par exemple deux casques.

![Screenshot](https://github.com/yourusername/audio-combinator/raw/main/screenshots/main.png)

## Fonctionnalités

- Interface graphique intuitive en GTK
- Détection automatique des périphériques audio
- Combine deux sorties audio en une seule
- Compatible avec PulseAudio et PipeWire
- Option pour définir la sortie combinée comme périphérique par défaut
- Surveillance en temps réel de l'état de la sortie combinée

## Cas d'utilisation

- Partager l'audio avec une autre personne (deux casques en même temps)
- Diffuser le son simultanément sur des haut-parleurs et un casque
- Créer des configurations audio personnalisées pour différents usages

## Prérequis

- Python 3.6 ou supérieur
- PulseAudio ou PipeWire
- GTK 3.0
- Bibliothèques Python : PyGObject, GLib

## Installation

### Sur Ubuntu/Debian/Linux Mint
```bash
# Installer les dépendances
sudo apt install python3 python3-gi python3-gi-cairo gir1.2-gtk-3.0 pulseaudio

# Cloner le dépôt
git clone https://github.com/yourusername/audio-combinator.git
cd audio-combinator

# Rendre le script exécutable
chmod +x audio_combinator.py
```

### Sur Fedora
```bash
# Installer les dépendances
sudo dnf install python3 python3-gobject gtk3 pulseaudio

# Cloner le dépôt
git clone https://github.com/yourusername/audio-combinator.git
cd audio-combinator

# Rendre le script exécutable
chmod +x audio_combinator.py
```

### Sur Arch Linux
```bash
# Installer les dépendances
sudo pacman -S python python-gobject gtk3 pulseaudio

# Cloner le dépôt
git clone https://github.com/yourusername/audio-combinator.git
cd audio-combinator

# Rendre le script exécutable
chmod +x audio_combinator.py
```

## Utilisation

1. Lancez l'application :
   ```bash
   ./audio_combinator.py
   ```

2. Sélectionnez les deux périphériques audio que vous souhaitez combiner
3. Cochez l'option "Définir comme périphérique par défaut" si vous le souhaitez
4. Cliquez sur "Démarrer" pour créer la sortie combinée
5. Pour arrêter, cliquez simplement sur "Arrêter"

## Fonctionnement technique

L'application utilise le module PulseAudio `module-combine-sink` pour créer une sortie virtuelle qui redirige l'audio vers plusieurs périphériques physiques. L'interface graphique est construite avec GTK via PyGObject.

## Création d'un lanceur d'application

Pour faciliter l'accès à l'application, vous pouvez créer un lanceur dans votre menu d'applications :

```bash
# Créer un fichier .desktop
cat > ~/.local/share/applications/audio-combinator.desktop << EOL
[Desktop Entry]
Type=Application
Name=Audio Combinator
Comment=Combiner plusieurs sorties audio
Exec=/chemin/complet/vers/audio_combinator.py
Terminal=false
Categories=AudioVideo;Audio;
Keywords=audio;sound;mixer;combine;
Icon=audio-card
EOL
```

Remplacez `/chemin/complet/vers/audio_combinator.py` par le chemin réel vers le script.

## Dépannage

### Aucun périphérique n'est détecté
- Vérifiez que PulseAudio est en cours d'exécution : `pulseaudio --check`
- Redémarrez PulseAudio : `pulseaudio -k && pulseaudio --start`

### Le son ne fonctionne pas sur les deux périphériques
- Vérifiez que les deux périphériques sont bien connectés et non mis en sourdine
- Consultez les journaux système pour voir si des erreurs sont signalées

### Erreur de création de sortie combinée
- Vérifiez que vous avez les permissions nécessaires pour utiliser PulseAudio
- Assurez-vous que les noms des périphériques sont corrects

## Perspectives d'évolution

- Ajout de la prise en charge de plus de deux périphériques de sortie
- Contrôle du volume individuel pour chaque périphérique
- Mode serveur pour une utilisation à distance
- Préréglages sauvegardables
- Interface améliorée avec visualisation audio

## Contribuer

Les contributions sont les bienvenues ! N'hésitez pas à :
- Signaler des bugs
- Proposer des fonctionnalités
- Soumettre des pull requests

## Licence

Ce projet est sous licence MIT. Voir le fichier [LICENSE](LICENSE) pour plus de détails.

## Crédits

Développé par [Votre Nom]

Merci à tous les contributeurs et à la communauté PulseAudio pour leur excellent travail.