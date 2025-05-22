#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Audio Combiner GUI - Application pour combiner plusieurs sorties audio
Compatible avec PulseAudio et PipeWire
Support pour 2+ périphériques de sortie avec contrôle de volume individuel
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
        self.device_combos = []  # Liste pour stocker toutes les combobox
        self.device_rows = []    # Liste pour stocker toutes les lignes de périphériques
        self.volume_scales = []  # Liste pour stocker tous les contrôles de volume
        self.mute_buttons = []   # Liste pour stocker tous les boutons de sourdine
        self.volume_labels = []  # Liste pour stocker tous les labels de volume
        self.device_sink_inputs = []  # Liste pour stocker les IDs des sink-inputs

        # Configurer le gestionnaire de signaux pour un arrêt propre
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

        # Créer la fenêtre principale
        self.window = Gtk.Window(title="Audio Combinator Pro")
        self.window.set_border_width(10)
        self.window.set_default_size(700, 600)
        self.window.connect("destroy", self.on_window_destroy)
        
        # Ajouter un peu de style (CSS)
        self.setup_css()
        
        # Créer le conteneur principal avec défilement
        self.main_scrolled = Gtk.ScrolledWindow()
        self.main_scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.window.add(self.main_scrolled)
        
        # Créer la grille principale
        self.main_grid = Gtk.Grid()
        self.main_grid.set_column_spacing(10)
        self.main_grid.set_row_spacing(10)
        self.main_grid.set_margin_left(10)
        self.main_grid.set_margin_right(10)
        self.main_grid.set_margin_top(10)
        self.main_grid.set_margin_bottom(10)
        self.main_scrolled.add(self.main_grid)
        
        self.current_row = 0
        
        # Titre
        title_label = Gtk.Label(label="Combinaison de sorties audio avec contrôle de volume")
        title_label.set_hexpand(True)
        title_label.get_style_context().add_class("title")
        self.main_grid.attach(title_label, 0, self.current_row, 3, 1)
        self.current_row += 1
        
        # Section pour les périphériques
        devices_frame = Gtk.Frame(label="Périphériques de sortie")
        devices_frame.set_hexpand(True)
        self.main_grid.attach(devices_frame, 0, self.current_row, 3, 1)
        self.current_row += 1
        
        # Conteneur pour les périphériques avec défilement
        self.devices_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.devices_box.set_margin_left(10)
        self.devices_box.set_margin_right(10)
        self.devices_box.set_margin_top(10)
        self.devices_box.set_margin_bottom(10)
        devices_frame.add(self.devices_box)
        
        # Ajouter deux périphériques par défaut
        self.add_device_row()
        self.add_device_row()
        
        # Boutons pour gérer les périphériques
        device_buttons_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        device_buttons_box.set_halign(Gtk.Align.CENTER)
        self.devices_box.pack_start(device_buttons_box, False, False, 5)
        
        self.add_device_button = Gtk.Button(label="+ Ajouter un périphérique")
        self.add_device_button.connect("clicked", self.on_add_device_clicked)
        device_buttons_box.pack_start(self.add_device_button, False, False, 0)
        
        self.remove_device_button = Gtk.Button(label="- Retirer le dernier")
        self.remove_device_button.connect("clicked", self.on_remove_device_clicked)
        device_buttons_box.pack_start(self.remove_device_button, False, False, 0)
        
        # Section de contrôle de volume principal
        volume_frame = Gtk.Frame(label="Contrôle de volume général (actif seulement pendant la combinaison)")
        volume_frame.set_hexpand(True)
        self.main_grid.attach(volume_frame, 0, self.current_row, 3, 1)
        self.current_row += 1
        
        volume_main_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        volume_main_box.set_margin_left(10)
        volume_main_box.set_margin_right(10)
        volume_main_box.set_margin_top(10)
        volume_main_box.set_margin_bottom(10)
        volume_frame.add(volume_main_box)
        
        # Volume principal
        volume_main_label = Gtk.Label(label="Volume général:")
        volume_main_box.pack_start(volume_main_label, False, False, 0)
        
        self.main_volume_scale = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL)
        self.main_volume_scale.set_range(0, 100)
        self.main_volume_scale.set_value(50)
        self.main_volume_scale.set_digits(0)
        self.main_volume_scale.set_hexpand(True)
        self.main_volume_scale.connect("value-changed", self.on_main_volume_changed)
        volume_main_box.pack_start(self.main_volume_scale, True, True, 0)
        
        self.main_volume_label = Gtk.Label(label="50%")
        self.main_volume_label.set_size_request(40, -1)
        volume_main_box.pack_start(self.main_volume_label, False, False, 0)
        
        # Bouton mute principal
        self.main_mute_button = Gtk.Button(label="🔊")
        self.main_mute_button.connect("clicked", self.on_main_mute_clicked)
        self.main_mute_button.set_size_request(40, -1)
        volume_main_box.pack_start(self.main_mute_button, False, False, 0)
        
        # Option périphérique par défaut
        self.default_check = Gtk.CheckButton(label="Définir comme périphérique par défaut")
        self.default_check.set_active(True)
        self.main_grid.attach(self.default_check, 0, self.current_row, 3, 1)
        self.current_row += 1
        
        # Boutons principaux
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        button_box.set_hexpand(True)
        self.main_grid.attach(button_box, 0, self.current_row, 3, 1)
        self.current_row += 1
        
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
        status_frame = Gtk.Frame(label="Statut")
        status_frame.set_hexpand(True)
        status_frame.set_vexpand(True)
        self.main_grid.attach(status_frame, 0, self.current_row, 3, 1)
        
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_hexpand(True)
        scrolled.set_vexpand(True)
        scrolled.set_min_content_height(120)
        status_frame.add(scrolled)
        
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
        
        # Mettre à jour l'état des boutons
        self.update_device_buttons_state()
    
    def add_device_row(self):
        """Ajoute une nouvelle ligne de sélection de périphérique avec contrôles de volume"""
        device_number = len(self.device_combos) + 1
        
        # Créer la boîte principale pour cette ligne
        device_row = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        device_row.set_hexpand(True)
        
        # Première ligne : sélection du périphérique
        selection_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        selection_row.set_hexpand(True)
        
        # Label pour le périphérique
        device_label = Gtk.Label(label=f"Périphérique {device_number}:")
        device_label.set_size_request(120, -1)
        device_label.set_halign(Gtk.Align.START)
        device_label.get_style_context().add_class("device-label")
        selection_row.pack_start(device_label, False, False, 0)
        
        # ComboBox pour le périphérique
        device_combo = Gtk.ComboBox()
        renderer_text = Gtk.CellRendererText()
        device_combo.pack_start(renderer_text, True)
        device_combo.add_attribute(renderer_text, "text", 1)
        device_combo.set_hexpand(True)
        selection_row.pack_start(device_combo, True, True, 0)
        
        device_row.pack_start(selection_row, False, False, 0)
        
        # Deuxième ligne : contrôles de volume
        volume_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        volume_row.set_hexpand(True)
        volume_row.set_margin_left(20)  # Indenter légèrement
        
        # Label volume
        volume_label_text = Gtk.Label(label="Volume:")
        volume_label_text.set_size_request(60, -1)
        volume_row.pack_start(volume_label_text, False, False, 0)
        
        # Slider de volume
        volume_scale = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL)
        volume_scale.set_range(0, 100)
        volume_scale.set_value(50)
        volume_scale.set_digits(0)
        volume_scale.set_hexpand(True)
        volume_scale.connect("value-changed", self.on_device_volume_changed, device_number - 1)
        volume_row.pack_start(volume_scale, True, True, 0)
        
        # Label pourcentage
        volume_percent_label = Gtk.Label(label="50%")
        volume_percent_label.set_size_request(40, -1)
        volume_row.pack_start(volume_percent_label, False, False, 0)
        
        # Bouton mute
        mute_button = Gtk.Button(label="🔊")
        mute_button.connect("clicked", self.on_device_mute_clicked, device_number - 1)
        mute_button.set_size_request(40, -1)
        volume_row.pack_start(mute_button, False, False, 0)
        
        device_row.pack_start(volume_row, False, False, 0)
        
        # Séparateur
        separator = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        separator.set_margin_top(5)
        separator.set_margin_bottom(5)
        device_row.pack_start(separator, False, False, 0)
        
        # Ajouter à nos listes
        self.device_combos.append(device_combo)
        self.device_rows.append(device_row)
        self.volume_scales.append(volume_scale)
        self.mute_buttons.append(mute_button)
        self.volume_labels.append(volume_percent_label)
        self.device_sink_inputs.append(None)
        
        # Ajouter à l'interface avant les boutons
        button_box_index = len(self.devices_box.get_children()) - 1
        self.devices_box.pack_start(device_row, False, False, 0)
        self.devices_box.reorder_child(device_row, button_box_index)
        
        # Afficher la nouvelle ligne
        device_row.show_all()
        
        # Mettre à jour la liste des périphériques pour cette nouvelle combobox
        self.populate_single_combo(device_combo)
        
        return device_combo
    
    def remove_device_row(self):
        """Retire la dernière ligne de sélection de périphérique"""
        if len(self.device_combos) > 2:  # Garder au minimum 2 périphériques
            # Retirer de l'interface
            last_row = self.device_rows.pop()
            last_combo = self.device_combos.pop()
            last_volume = self.volume_scales.pop()
            last_mute = self.mute_buttons.pop()
            last_label = self.volume_labels.pop()
            last_sink_input = self.device_sink_inputs.pop()
            
            self.devices_box.remove(last_row)
        
        self.update_device_buttons_state()
    
    def update_device_buttons_state(self):
        """Met à jour l'état des boutons d'ajout/suppression de périphériques"""
        # Limite à 8 périphériques maximum pour des raisons pratiques
        self.add_device_button.set_sensitive(len(self.device_combos) < 8)
        self.remove_device_button.set_sensitive(len(self.device_combos) > 2)
    
    def setup_css(self):
        """Configure le CSS pour l'interface"""
        css_provider = Gtk.CssProvider()
        css = """
        .title {
            font-size: 18px;
            font-weight: bold;
            margin-bottom: 10px;
        }
        .device-label {
            font-weight: bold;
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
        
        # Créer un nouveau modèle de données pour les périphériques
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
        
        # Mettre à jour toutes les combobox
        for i, combo in enumerate(self.device_combos):
            combo.set_model(store)
            # Sélectionner un périphérique différent pour chaque combo si possible
            if len(store) > i:
                combo.set_active(i)
            elif len(store) > 0:
                combo.set_active(0)
        
        self.append_status(f"Trouvé {len(store)} périphériques audio.", "success")
    
    def populate_single_combo(self, combo):
        """Remplit une seule combobox avec la liste des périphériques"""
        # Si on a déjà un modèle sur une autre combobox, on le réutilise
        if len(self.device_combos) > 0 and self.device_combos[0].get_model():
            model = self.device_combos[0].get_model()
            combo.set_model(model)
            
            # Sélectionner un périphérique différent des autres si possible
            selected_indices = []
            for other_combo in self.device_combos:
                if other_combo != combo:
                    active = other_combo.get_active()
                    if active >= 0:
                        selected_indices.append(active)
            
            # Trouver le premier index non utilisé
            for i in range(len(model)):
                if i not in selected_indices:
                    combo.set_active(i)
                    break
            else:
                # Si tous les indices sont utilisés, sélectionner le premier
                if len(model) > 0:
                    combo.set_active(0)
    
    def get_selected_devices(self):
        """Retourne la liste des périphériques sélectionnés (uniques)"""
        selected_devices = []
        selected_names = []
        
        for combo in self.device_combos:
            device_iter = combo.get_active_iter()
            if device_iter:
                model = combo.get_model()
                sink_name = model[device_iter][2]  # Nom technique
                sink_desc = model[device_iter][1]  # Description
                
                # Éviter les doublons
                if sink_name not in selected_names:
                    selected_devices.append({
                        'name': sink_name,
                        'description': sink_desc
                    })
                    selected_names.append(sink_name)
        
        return selected_devices
    
    def find_sink_inputs_for_combined_sink(self):
        """Trouve les sink-inputs associés à notre sortie combinée"""
        if not self.combined_sink_active or not self.combined_name:
            return []
        
        sink_inputs = []
        output = self.run_command("pactl list short sink-inputs")
        
        for line in output.splitlines():
            if line.strip():
                parts = line.split()
                if len(parts) >= 3:
                    sink_input_id = parts[0]
                    sink_name = parts[1]
                    
                    # Si ce sink-input appartient à notre sortie combinée
                    if sink_name == self.combined_name:
                        sink_inputs.append(sink_input_id)
        
        return sink_inputs
    
    def set_sink_input_volume(self, sink_input_id, volume_percent):
        """Définit le volume d'un sink-input spécifique"""
        # PulseAudio utilise des valeurs de 0 à 65536 (où 65536 = 100%)
        volume_value = int((volume_percent / 100.0) * 65536)
        self.run_command(f"pactl set-sink-input-volume {sink_input_id} {volume_value}")
    
    def set_sink_input_mute(self, sink_input_id, muted):
        """Définit l'état de sourdine d'un sink-input spécifique"""
        mute_value = "1" if muted else "0"
        self.run_command(f"pactl set-sink-input-mute {sink_input_id} {mute_value}")
    
    def set_sink_volume(self, sink_name, volume_percent):
        """Définit le volume d'un sink spécifique"""
        volume_value = int((volume_percent / 100.0) * 65536)
        self.run_command(f"pactl set-sink-volume {sink_name} {volume_value}")
    
    def set_sink_mute(self, sink_name, muted):
        """Définit l'état de sourdine d'un sink spécifique"""
        mute_value = "1" if muted else "0"
        self.run_command(f"pactl set-sink-mute {sink_name} {mute_value}")
    
    def on_main_volume_changed(self, scale):
        """Gestionnaire pour le changement de volume principal"""
        volume = int(scale.get_value())
        self.main_volume_label.set_text(f"{volume}%")
        
        if self.combined_sink_active and self.combined_name:
            self.set_sink_volume(self.combined_name, volume)
    
    def on_main_mute_clicked(self, button):
        """Gestionnaire pour le bouton de sourdine principal"""
        if button.get_label() == "🔊":
            button.set_label("🔇")
            if self.combined_sink_active and self.combined_name:
                self.set_sink_mute(self.combined_name, True)
        else:
            button.set_label("🔊")
            if self.combined_sink_active and self.combined_name:
                self.set_sink_mute(self.combined_name, False)
    
    def on_device_volume_changed(self, scale, device_index):
        """Gestionnaire pour le changement de volume d'un périphérique"""
        volume = int(scale.get_value())
        self.volume_labels[device_index].set_text(f"{volume}%")
        
        # Appliquer le volume immédiatement, même si la combinaison n'est pas active
        selected_devices = self.get_selected_devices()
        if device_index < len(selected_devices):
            device_name = selected_devices[device_index]['name']
            self.set_sink_volume(device_name, volume)
            
            if self.combined_sink_active:
                self.append_status(f"Volume de '{selected_devices[device_index]['description']}' défini à {volume}%", "info")
            else:
                self.append_status(f"Volume pré-configuré pour '{selected_devices[device_index]['description']}': {volume}%", "info")
    
    def on_device_mute_clicked(self, button, device_index):
        """Gestionnaire pour le bouton de sourdine d'un périphérique"""
        if button.get_label() == "🔊":
            button.set_label("🔇")
            muted = True
        else:
            button.set_label("🔊")
            muted = False
        
        # Appliquer la sourdine immédiatement, même si la combinaison n'est pas active
        selected_devices = self.get_selected_devices()
        if device_index < len(selected_devices):
            device_name = selected_devices[device_index]['name']
            self.set_sink_mute(device_name, muted)
            status = "en sourdine" if muted else "réactivé"
            
            if self.combined_sink_active:
                self.append_status(f"Audio de '{selected_devices[device_index]['description']}' {status}", "info")
            else:
                self.append_status(f"Audio pré-configuré pour '{selected_devices[device_index]['description']}': {status}", "info")
    
    def create_combined_sink(self):
        """Crée une sortie audio combinée"""
        selected_devices = self.get_selected_devices()
        
        if len(selected_devices) < 2:
            self.append_status("Veuillez sélectionner au moins deux périphériques différents.", "error")
            return False
        
        # Générer un nom pour la sortie combinée
        self.combined_name = f"combined-output-{int(time.time())}"
        
        # Créer la liste des esclaves (slaves)
        slaves = ",".join([device['name'] for device in selected_devices])
        
        # Créer la sortie combinée
        self.append_status(f"Création de la sortie combinée '{self.combined_name}'...", "info")
        self.append_status(f"Combinaison de {len(selected_devices)} périphériques:", "info")
        for device in selected_devices:
            self.append_status(f"  - {device['description']}", "info")
        
        output = self.run_command(f"pactl load-module module-combine-sink sink_name=\"{self.combined_name}\" slaves=\"{slaves}\"")
        
        if output.strip().isdigit():
            self.module_id = output.strip()
            self.combined_sink_active = True
            self.append_status("Sortie combinée créée avec succès!", "success")
            
            # Appliquer le volume principal initial
            main_volume = int(self.main_volume_scale.get_value())
            self.set_sink_volume(self.combined_name, main_volume)
            
            # Appliquer les volumes individuels
            for i, device in enumerate(selected_devices):
                if i < len(self.volume_scales):
                    volume = int(self.volume_scales[i].get_value())
                    self.set_sink_volume(device['name'], volume)
            
            # Définir comme périphérique par défaut si demandé
            if self.default_check.get_active():
                self.run_command(f"pactl set-default-sink {self.combined_name}")
                self.append_status("Défini comme périphérique par défaut.", "success")
            
            self.append_status("Contrôles de volume individuels activés.", "success")
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
            # Réinitialiser les sink-inputs
            self.device_sink_inputs = [None] * len(self.device_sink_inputs)
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
            self.refresh_button.set_sensitive(False)
            self.add_device_button.set_sensitive(False)
            self.remove_device_button.set_sensitive(False)
            self.default_check.set_sensitive(False)
            
            # Activer le contrôle de volume principal seulement quand la combinaison est active
            self.main_volume_scale.set_sensitive(True)
            self.main_mute_button.set_sensitive(True)
            
            for combo in self.device_combos:
                combo.set_sensitive(False)
            
            # Les contrôles de volume individuels restent toujours actifs
            for i, (scale, button) in enumerate(zip(self.volume_scales, self.mute_buttons)):
                scale.set_sensitive(True)
                button.set_sensitive(True)
        else:
            self.start_button.set_sensitive(True)
            self.stop_button.set_sensitive(False)
            self.refresh_button.set_sensitive(True)
            self.default_check.set_sensitive(True)
            
            # Désactiver seulement le contrôle de volume principal
            self.main_volume_scale.set_sensitive(False)
            self.main_mute_button.set_sensitive(False)
            
            for combo in self.device_combos:
                combo.set_sensitive(True)
            
            # Garder les contrôles de volume individuels actifs même avant le démarrage
            for i, (scale, button) in enumerate(zip(self.volume_scales, self.mute_buttons)):
                scale.set_sensitive(True)
                button.set_sensitive(True)
            
            self.update_device_buttons_state()
    
    def reset_volume_controls(self):
        """Remet les contrôles de volume à leur état initial"""
        # Remettre le volume principal à 50%
        self.main_volume_scale.set_value(50)
        self.main_volume_label.set_text("50%")
        self.main_mute_button.set_label("🔊")
        
        # Remettre tous les volumes individuels à 50%
        for i, (scale, label, button) in enumerate(zip(self.volume_scales, self.volume_labels, self.mute_buttons)):
            scale.set_value(50)
            label.set_text("50%")
            button.set_label("🔊")
    
    def on_add_device_clicked(self, button):
        """Gestionnaire d'événement pour le bouton d'ajout de périphérique"""
        self.add_device_row()
        self.update_device_buttons_state()
    
    def on_remove_device_clicked(self, button):
        """Gestionnaire d'événement pour le bouton de suppression de périphérique"""
        self.remove_device_row()
    
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
            selected_devices = self.get_selected_devices()
            self.append_status(f"La sortie combinée est active. L'audio est maintenant redirigé vers {len(selected_devices)} périphériques.", "success")
            self.append_status("Les volumes pré-configurés ont été appliqués.", "info")
            self.append_status("Vous pouvez maintenant ajuster le volume général et les volumes individuels.", "info")
    
    def on_stop_clicked(self, button):
        """Gestionnaire d'événement pour le bouton Arrêter"""
        if self.remove_combined_sink():
            self.update_ui_state()
            self.reset_volume_controls()
    
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
    # Initialiser l'état de l'interface
    app.update_ui_state()
    Gtk.main()

if __name__ == "__main__":
    main()