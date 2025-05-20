#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Audio Combiner GUI - Application pour combiner deux sorties audio
Compatible avec PulseAudio et PipeWire
"""

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib, Gdk, Pango
import subprocess
import time
import threading
import re
import sys
import signal
import os

class AudioCombiner:
    def __init__(self):
        # État de l'application
        self.combined_sink_active = False
        self.module_id = None
        self.combined_name = None
        self.running = True

        # Configurer le gestionnaire de signaux pour un arrêt propre
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

        # Créer la fenêtre principale
        self.window = Gtk.Window(title="Audio Combinator")
        self.window.set_border_width(10)
        self.window.set_default_size(500, 400)
        self.window.connect("destroy", self.on_window_destroy)
        
        # Ajouter un peu de style (CSS)
        self.setup_css()
        
        # Créer la grille principale
        main_grid = Gtk.Grid()
        main_grid.set_column_spacing(10)
        main_grid.set_row_spacing(10)
        self.window.add(main_grid)
        
        # Titre
        title_label = Gtk.Label(label="Combinaison de sorties audio")
        title_label.set_hexpand(True)
        title_label.get_style_context().add_class("title")
        main_grid.attach(title_label, 0, 0, 2, 1)
        
        # Premier périphérique
        device1_label = Gtk.Label(label="Premier périphérique:")
        device1_label.set_halign(Gtk.Align.START)
        main_grid.attach(device1_label, 0, 1, 1, 1)
        
        self.device1_combo = Gtk.ComboBox()
        renderer_text = Gtk.CellRendererText()
        self.device1_combo.pack_start(renderer_text, True)
        self.device1_combo.add_attribute(renderer_text, "text", 1)
        self.device1_combo.set_hexpand(True)
        main_grid.attach(self.device1_combo, 1, 1, 1, 1)
        
        # Deuxième périphérique
        device2_label = Gtk.Label(label="Deuxième périphérique:")
        device2_label.set_halign(Gtk.Align.START)
        main_grid.attach(device2_label, 0, 2, 1, 1)
        
        self.device2_combo = Gtk.ComboBox()
        renderer_text = Gtk.CellRendererText()
        self.device2_combo.pack_start(renderer_text, True)
        self.device2_combo.add_attribute(renderer_text, "text", 1)
        self.device2_combo.set_hexpand(True)
        main_grid.attach(self.device2_combo, 1, 2, 1, 1)
        
        # Option périphérique par défaut
        self.default_check = Gtk.CheckButton(label="Définir comme périphérique par défaut")
        self.default_check.set_active(True)
        main_grid.attach(self.default_check, 0, 3, 2, 1)
        
        # Boutons
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        button_box.set_hexpand(True)
        main_grid.attach(button_box, 0, 4, 2, 1)
        
        self.refresh_button = Gtk.Button(label="Actualiser")
        self.refresh_button.connect("clicked", self.on_refresh_clicked)
        button_box.pack_start(self.refresh_button, True, True, 0)
        
        self.start_button = Gtk.Button(label="Démarrer")
        self.start_button.connect("clicked", self.on_start_clicked)
        self.start_button.get_style_context().add_class("suggested-action")
        button_box.pack_start(self.start_button, True, True, 0)
        
        self.stop_button = Gtk.Button(label="Arrêter")
        self.stop_button.connect("clicked", self.on_stop_clicked)
        self.stop_button.get_style_context().add_class("destructive-action")
        self.stop_button.set_sensitive(False)
        button_box.pack_start(self.stop_button, True, True, 0)
        
        # Zone de statut
        frame = Gtk.Frame(label="Statut")
        frame.set_hexpand(True)
        frame.set_vexpand(True)
        main_grid.attach(frame, 0, 5, 2, 1)
        
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_hexpand(True)
        scrolled.set_vexpand(True)
        frame.add(scrolled)
        
        self.status_buffer = Gtk.TextBuffer()
        self.status_view = Gtk.TextView(buffer=self.status_buffer)
        self.status_view.set_editable(False)
        self.status_view.set_cursor_visible(False)
        self.status_view.set_wrap_mode(Gtk.WrapMode.WORD)
        scrolled.add(self.status_view)
        
        # Tags pour colorer le texte
        self.setup_text_tags()
        
        # Charger les périphériques
        self.update_device_list()
        
        # Démarrer le thread de surveillance
        monitor_thread = threading.Thread(target=self.monitor_combined_sink)
        monitor_thread.daemon = True
        monitor_thread.start()
    
    def setup_css(self):
        """Configure le CSS pour l'interface"""
        css_provider = Gtk.CssProvider()
        css = """
        .title {
            font-size: 18px;
            font-weight: bold;
            margin-bottom: 10px;
        }
        """
        css_provider.load_from_data(css.encode())
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
    
    def setup_text_tags(self):
        """Configure les tags pour formater le texte dans la zone de statut"""
        self.status_buffer.create_tag("info", foreground="#0066cc")
        self.status_buffer.create_tag("success", foreground="#009900")
        self.status_buffer.create_tag("error", foreground="#cc0000")
        self.status_buffer.create_tag("warning", foreground="#cc6600")
        self.status_buffer.create_tag("bold", weight=Pango.Weight.BOLD)
    
    def run_command(self, command):
        """Exécute une commande shell et retourne la sortie"""
        try:
            process = subprocess.Popen(
                command, 
                shell=True, 
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            stdout, stderr = process.communicate()
            
            if process.returncode != 0 and stderr:
                self.append_status(f"Erreur: {stderr}", "error")
                return stderr
            
            return stdout
        except Exception as e:
            self.append_status(f"Exception: {str(e)}", "error")
            return str(e)
    
    def append_status(self, message, tag=None):
        """Ajoute un message à la zone de statut"""
        def _append():
            end_iter = self.status_buffer.get_end_iter()
            if tag:
                self.status_buffer.insert_with_tags_by_name(end_iter, message + "\n", tag)
            else:
                self.status_buffer.insert(end_iter, message + "\n")
            
            # Faire défiler jusqu'au bas
            mark = self.status_buffer.create_mark(None, end_iter, False)
            self.status_view.scroll_to_mark(mark, 0.0, False, 0.0, 0.0)
            self.status_buffer.delete_mark(mark)
        
        GLib.idle_add(_append)
    
    def update_device_list(self):
        """Met à jour la liste des périphériques audio"""
        self.append_status("Recherche des périphériques audio...", "info")
        
        # Créer un modèle de données pour les périphériques
        # Colonnes: id, description, nom_technique
        store = Gtk.ListStore(str, str, str)
        
        # Obtenir les infos complètes sur les périphériques
        sink_info = self.run_command("pactl list sinks")
        
        # Analyser chaque périphérique
        sink_sections = re.split(r'Sink #', sink_info)[1:]  # Diviser par sections de sink
        
        for section in sink_sections:
            # Extraire l'ID du sink
            sink_id = section.strip().split('\n')[0].strip()
            
            # Extraire le nom du sink depuis pactl list short sinks
            short_info = self.run_command(f"pactl list short sinks | grep '^{sink_id}'")
            if not short_info:
                continue
                
            name = short_info.split()[1]
            
            # Ignorer les sorties combinées existantes
            if "combined" in name:
                continue
            
            # Essayer différentes méthodes pour extraire la description conviviale
            desc = None
            
            # Méthode 1: Ligne Description directe
            match = re.search(r'Description: (.*)', section)
            if match:
                desc = match.group(1).strip()
            
            # Méthode 2: Propriété node.description (pour PipeWire)
            if not desc or desc == "PipeWire":
                match = re.search(r'node\.description = "(.*)"', section)
                if match:
                    desc = match.group(1).strip()
            
            # Méthode 3: Propriété device.description
            if not desc or desc == "PipeWire":
                match = re.search(r'device\.description = "(.*)"', section)
                if match:
                    desc = match.group(1).strip()
            
            # Méthode 4: Nom de la carte ALSA
            if not desc or desc == "PipeWire":
                match = re.search(r'alsa\.card_name = "(.*)"', section)
                if match:
                    desc = match.group(1).strip()
            
            # Méthode 5: Nom du produit
            if not desc or desc == "PipeWire":
                match = re.search(r'device\.product\.name = "(.*)"', section)
                if match:
                    desc = match.group(1).strip()
            
            # Si on n'a toujours pas de description utile, utiliser le nom technique
            if not desc or desc == "PipeWire":
                desc = name
            
            # Ajouter au modèle
            store.append([sink_id, desc, name])
        
        # Définir le modèle pour les combobox
        self.device1_combo.set_model(store)
        self.device2_combo.set_model(Gtk.ListStore())  # Vider temporairement
        self.device2_combo.set_model(store)
        
        # Sélectionner le premier élément par défaut s'il y en a
        if len(store) > 0:
            self.device1_combo.set_active(0)
            if len(store) > 1:
                self.device2_combo.set_active(1)
            else:
                self.device2_combo.set_active(0)
        
        self.append_status(f"Trouvé {len(store)} périphériques audio.", "success")
    
    def create_combined_sink(self):
        """Crée une sortie audio combinée"""
        # Obtenir les périphériques sélectionnés
        device1_iter = self.device1_combo.get_active_iter()
        device2_iter = self.device2_combo.get_active_iter()
        
        if not device1_iter or not device2_iter:
            self.append_status("Veuillez sélectionner deux périphériques.", "error")
            return False
        
        model = self.device1_combo.get_model()
        sink1_name = model[device1_iter][2]  # Nom technique du premier périphérique
        sink1_desc = model[device1_iter][1]  # Description du premier périphérique
        
        model = self.device2_combo.get_model()
        sink2_name = model[device2_iter][2]  # Nom technique du deuxième périphérique
        sink2_desc = model[device2_iter][1]  # Description du deuxième périphérique
        
        # Vérifier que ce sont des périphériques différents
        if sink1_name == sink2_name:
            self.append_status("Veuillez sélectionner deux périphériques différents.", "error")
            return False
        
        # Générer un nom pour la sortie combinée
        self.combined_name = f"combined-output-{int(time.time())}"
        
        # Créer la sortie combinée
        self.append_status(f"Création de la sortie combinée '{self.combined_name}'...", "info")
        output = self.run_command(f"pactl load-module module-combine-sink sink_name=\"{self.combined_name}\" slaves=\"{sink1_name},{sink2_name}\"")
        
        if output.strip().isdigit():
            self.module_id = output.strip()
            self.combined_sink_active = True
            self.append_status("Sortie combinée créée avec succès!", "success")
            self.append_status(f"Combinaison de '{sink1_desc}' et '{sink2_desc}'", "info")
            
            # Définir comme périphérique par défaut si demandé
            if self.default_check.get_active():
                self.run_command(f"pactl set-default-sink {self.combined_name}")
                self.append_status("Défini comme périphérique par défaut.", "success")
            
            return True
        else:
            self.append_status("Erreur lors de la création de la sortie combinée.", "error")
            return False
    
    def remove_combined_sink(self):
        """Supprime la sortie audio combinée"""
        if self.module_id:
            self.append_status(f"Suppression de la sortie combinée (module {self.module_id})...", "info")
            self.run_command(f"pactl unload-module {self.module_id}")
            self.combined_sink_active = False
            self.module_id = None
            self.combined_name = None
            self.append_status("Sortie combinée supprimée.", "success")
            return True
        else:
            # Essayer de trouver et supprimer toutes les sorties combinées
            output = self.run_command("pactl list short modules | grep module-combine-sink")
            if output.strip():
                for line in output.strip().split('\n'):
                    if line:
                        module_id = line.split()[0]
                        self.run_command(f"pactl unload-module {module_id}")
                self.append_status("Toutes les sorties combinées ont été supprimées.", "success")
                return True
            else:
                self.append_status("Aucune sortie combinée active trouvée.", "warning")
                return False
    
    def monitor_combined_sink(self):
        """Thread qui surveille l'état de la sortie combinée"""
        while self.running:
            if self.combined_sink_active and self.module_id:
                # Vérifier si le module existe toujours
                output = self.run_command(f"pactl list short modules | grep '^{self.module_id}'")
                if not output.strip() and self.module_id:
                    self.append_status("Le module de sortie combinée a été supprimé de façon inattendue.", "warning")
                    self.combined_sink_active = False
                    
                    # Mettre à jour l'interface
                    GLib.idle_add(self.update_ui_state)
            
            # Pause pour éviter trop de vérifications
            time.sleep(5)
    
    def update_ui_state(self):
        """Met à jour l'état de l'interface en fonction de l'état de la sortie combinée"""
        if self.combined_sink_active:
            self.start_button.set_sensitive(False)
            self.stop_button.set_sensitive(True)
            self.device1_combo.set_sensitive(False)
            self.device2_combo.set_sensitive(False)
            self.default_check.set_sensitive(False)
        else:
            self.start_button.set_sensitive(True)
            self.stop_button.set_sensitive(False)
            self.device1_combo.set_sensitive(True)
            self.device2_combo.set_sensitive(True)
            self.default_check.set_sensitive(True)
    
    def on_refresh_clicked(self, button):
        """Gestionnaire d'événement pour le bouton Actualiser"""
        self.update_device_list()
    
    def on_start_clicked(self, button):
        """Gestionnaire d'événement pour le bouton Démarrer"""
        # D'abord supprimer toute sortie combinée existante
        self.remove_combined_sink()
        
        # Puis créer la nouvelle sortie combinée
        if self.create_combined_sink():
            self.update_ui_state()
            self.append_status("La sortie combinée est active. L'audio est maintenant redirigé vers les deux périphériques.", "success")
    
    def on_stop_clicked(self, button):
        """Gestionnaire d'événement pour le bouton Arrêter"""
        if self.remove_combined_sink():
            self.update_ui_state()
    
    def on_window_destroy(self, window):
        """Gestionnaire d'événement pour la fermeture de la fenêtre"""
        self.cleanup()
        Gtk.main_quit()
    
    def signal_handler(self, signum, frame):
        """Gestionnaire pour les signaux d'arrêt"""
        self.cleanup()
        sys.exit(0)
    
    def cleanup(self):
        """Nettoie les ressources avant de quitter"""
        self.running = False
        if self.combined_sink_active:
            self.remove_combined_sink()

def main():
    app = AudioCombiner()
    app.window.show_all()
    Gtk.main()

if __name__ == "__main__":
    main()