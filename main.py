import glob
import json
import os
import platform
import shutil
import sys
import threading
from datetime import timedelta

import ctkcomponents
import customtkinter as ctk
from CTkToolTip import CTkToolTip
from PIL import Image
from customtkinter import filedialog
from mutagen import File, MutagenError
from pygame import mixer, error
from pywinstyles import set_opacity, apply_style
from whisper import _download, _MODELS
from whisper.utils import get_writer

from util import (center_window, get_gpu_info, save_default, load_settings, save_settings, Transcriber,
                  CTkScrollableDropdown)

PATH = os.path.join(os.path.dirname(__file__))
SETTINGS_FILE = os.path.join(PATH, "settings", "settings.json")
ctk.set_default_color_theme(f"{PATH}\\assets\\blue.json")
ICON_PATH = os.path.join(PATH, "assets\\icons")
LOGO = f"{ICON_PATH}\\logo.ico"
ICONS = {
    "new": ctk.CTkImage(Image.open(f"{ICON_PATH}\\new_file.png"), Image.open(f"{ICON_PATH}\\new_file.png"), (28, 28)),
    "settings": ctk.CTkImage(Image.open(f"{ICON_PATH}\\settings.png"), Image.open(f"{ICON_PATH}\\settings.png"),
                             (24, 24)),
    "check": ctk.CTkImage(Image.open(f"{ICON_PATH}\\check.png"), Image.open(f"{ICON_PATH}\\check.png"),
                          (20, 20)),

    "play": ctk.CTkImage(Image.open(f"{ICON_PATH}\\play.png"), Image.open(f"{ICON_PATH}\\play.png"), (20, 20)),
    "pause": ctk.CTkImage(Image.open(f"{ICON_PATH}\\pause.png"), Image.open(f"{ICON_PATH}\\pause.png"), (20, 20)),
    "audio": ctk.CTkImage(Image.open(f"{ICON_PATH}\\audio.png"), Image.open(f"{ICON_PATH}\\audio.png"), (20, 20)),
    "mute": ctk.CTkImage(Image.open(f"{ICON_PATH}\\mute.png"), Image.open(f"{ICON_PATH}\\mute.png"), (20, 20)),

    "transcribe": ctk.CTkImage(Image.open(f"{ICON_PATH}\\text.png"), Image.open(f"{ICON_PATH}\\text.png"), (20, 20)),
    "text": ctk.CTkImage(Image.open(f"{ICON_PATH}\\text.png"), Image.open(f"{ICON_PATH}\\text.png"), (24, 24)),
    "cc": ctk.CTkImage(Image.open(f"{ICON_PATH}\\cc.png"), Image.open(f"{ICON_PATH}\\cc.png"), (24, 24)),

    "open": ctk.CTkImage(Image.open(f"{ICON_PATH}\\open_folder.png"), Image.open(f"{ICON_PATH}\\open_folder.png"),
                         (24, 24)),
    "change": ctk.CTkImage(Image.open(f"{ICON_PATH}\\change_folder.png"), Image.open(f"{ICON_PATH}\\change_folder.png"),
                           (24, 24)),
    "delete": ctk.CTkImage(Image.open(f"{ICON_PATH}\\delete.png"), Image.open(f"{ICON_PATH}\\delete.png"), (20, 20)),
    "models": ctk.CTkImage(Image.open(f"{ICON_PATH}\\models.png"), Image.open(f"{ICON_PATH}\\models.png"),
                           (24, 24)),
    "downloaded": ctk.CTkImage(Image.open(f"{ICON_PATH}\\downloaded.png"), Image.open(f"{ICON_PATH}\\downloaded.png"),
                               (18, 18)),
    "download": ctk.CTkImage(Image.open(f"{ICON_PATH}\\download.png"), Image.open(f"{ICON_PATH}\\download.png"),
                             (24, 24)),
    "gpu": ctk.CTkImage(Image.open(f"{ICON_PATH}\\gpu.png"), Image.open(f"{ICON_PATH}\\gpu.png"),
                        (24, 24)),

    "back": ctk.CTkImage(Image.open(f"{ICON_PATH}\\back.png"), Image.open(f"{ICON_PATH}\\back.png"),
                         (24, 24)),

    "model": ctk.CTkImage(Image.open(f"{ICON_PATH}\\model.png"), Image.open(f"{ICON_PATH}\\model.png"), (22, 22)),
    "language": ctk.CTkImage(Image.open(f"{ICON_PATH}\\language.png"), Image.open(f"{ICON_PATH}\\language.png"),
                             (22, 22)),
    "to_english": ctk.CTkImage(Image.open(f"{ICON_PATH}\\to_english.png"), Image.open(f"{ICON_PATH}\\to_english.png"),
                               (22, 22)),
    "prompt": ctk.CTkImage(Image.open(f"{ICON_PATH}\\prompt.png"), Image.open(f"{ICON_PATH}\\prompt.png"), (22, 22)),
    "audio_file": ctk.CTkImage(Image.open(f"{ICON_PATH}\\audio_file.png"), Image.open(f"{ICON_PATH}\\audio_file.png"),
                               (22, 22)),

    "export": ctk.CTkImage(Image.open(f"{ICON_PATH}\\export.png"), Image.open(f"{ICON_PATH}\\export.png"),
                           (20, 20))
}
BTN_OPTION = {
    "height": 30,
    "compound": "left",
    "anchor": "w",
    "fg_color": "transparent",
    "text_color": "#FFFFFF",
    "corner_radius": 5,
    "hover_color": "#43454A"
}


class CTkAudioPlayer(ctk.CTkFrame):
    def __init__(self, master: any, file, width=600, height=120, **kwargs):
        super().__init__(master, width, height, **kwargs)
        self.root = master
        self.file = file
        self.audio = File(self.file)
        try:
            self.mixer = mixer
            self.mixer.init()
            self.mixer.music.load(self.file)
        except error as e:
            ctkcomponents.CTkAlert(state="error", title="Pygame Error", body_text=str(e))
            self.destroy()

        self.audio_length = int(self.audio.info.length)
        self.is_playing = False
        self.is_muted = False
        self.job_id = None
        self.current_time = 0

        self.play_btn = ctk.CTkButton(self, text="", image=ICONS["play"], command=self.play_pause, width=20, height=20,
                                      fg_color="transparent", hover=False, border_width=0)
        self.play_btn.grid(row=0, column=0, padx=10, pady=10, sticky="w")

        self.current_time_label = ctk.CTkLabel(self, text="00:00:00")
        self.current_time_label.grid(row=0, column=1, padx=0, pady=10, sticky="ew")

        self.slider = ctk.CTkSlider(self, from_=0, to=self.audio_length, height=18)
        self.slider.set(0)
        self.slider.grid(row=0, column=2, padx=5, pady=10, sticky="ew")
        self.slider.bind("<Button-1>", self.start_drag)
        self.slider.bind("<ButtonRelease-1>", self.stop_drag)

        self.total_time_label = ctk.CTkLabel(self, text=self.format_duration(self.audio_length))
        self.total_time_label.grid(row=0, column=3, padx=0, pady=10, sticky="ew")

        self.mute_button = ctk.CTkButton(self, text="", image=ICONS["audio"], command=self.toggle_mute, width=20,
                                         height=20, fg_color="transparent", hover=False, border_width=0)
        self.mute_button.grid(row=0, column=4, padx=10, pady=10, sticky="e")

    def play_pause(self):
        if self.is_playing:
            self.pause()
        else:
            self.play()

    def pause(self):
        if self.job_id is not None:
            self.root.after_cancel(self.job_id)
        self.mixer.music.pause()
        self.is_playing = False
        self.play_btn.configure(image=ICONS["play"])

    def toggle_mute(self):
        if self.is_muted:
            mixer.music.set_volume(1)
            self.is_muted = False
            self.mute_button.configure(image=ICONS["audio"])
        else:
            mixer.music.set_volume(0)
            self.is_muted = True
            self.mute_button.configure(image=ICONS["mute"])

    def play(self):
        self.mixer.music.play(0, self.current_time)
        self.is_playing = True
        self.play_btn.configure(image=ICONS["pause"])
        self.update_slider()

    def stop(self):
        if self.job_id is not None:
            self.root.after_cancel(self.job_id)
        self.mixer.music.stop()
        self.is_playing = False
        self.current_time = 0
        self.current_time_label.configure(text=self.format_duration(0))
        self.slider.set(0)
        self.play_btn.configure(image=ICONS["play"])

    def start_drag(self, event):
        if self.job_id is not None:
            self.root.after_cancel(self.job_id)
            self.job_id = None

    def stop_drag(self, event):
        self.change_position()
        if self.is_playing:
            self.job_id = self.root.after(1000, self.update_slider)

    def change_position(self, _=None):
        new_time = int(self.slider.get())
        self.current_time = new_time
        if self.is_playing:
            self.mixer.music.rewind()
            self.mixer.music.set_pos(new_time)
        else:
            self.mixer.music.play(0, self.current_time)
            self.is_playing = True
            self.play_btn.configure(image=ICONS["pause"])

        self.current_time_label.configure(text=self.format_duration(new_time))

    def update_slider(self):
        if self.is_playing:
            self.current_time += 1
            if self.current_time >= self.audio_length or not self.mixer.music.get_busy():
                self.stop()
            else:

                self.slider.set(self.current_time)
                self.current_time_label.configure(text=self.format_duration(self.current_time))
                self.job_id = self.master.after(1000, self.update_slider)

    @staticmethod
    def format_duration(duration_s):
        hours, remainder = divmod(duration_s, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02}:{minutes:02}:{seconds:02}"


class Settings(ctk.CTkFrame):
    def __init__(self, master: any, **kwargs):
        super().__init__(master, width=700, height=800, fg_color="transparent", border_width=0, **kwargs)

        self.root = master
        self.grid_propagate(False)
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(1, weight=1)

        self.settings = load_settings(SETTINGS_FILE)

        self.download_folder = self.settings["app_settings"]["download_path"]

        self.installed_models = [os.path.basename(path) for path in self.get_files(self.download_folder, "pt")]
        self.installed_models = [model.replace('.pt', '') for model in self.installed_models]

        self.left_frame = ctk.CTkFrame(self, border_width=0, corner_radius=2, width=250)
        self.left_frame.grid(row=0, column=0, padx=0, pady=0, sticky="nsw", rowspan=2)
        self.left_frame.grid_propagate(False)

        self.top_frame = ctk.CTkFrame(self, border_width=0, corner_radius=2, fg_color="transparent", height=80)
        self.top_frame.grid(row=0, column=1, padx=0, pady=0, sticky="new", rowspan=1)
        self.top_frame.grid_columnconfigure(0, weight=1)
        self.top_frame.grid_propagate(False)

        self.title = ctk.CTkLabel(self.top_frame, text="", font=("", 18))
        self.title.grid(row=0, column=0, padx=20, pady=20, sticky="w")

        self.close_btn = ctk.CTkButton(self.top_frame, text="", image=ICONS["back"], width=60, height=30,
                                       command=self.on_close)
        self.close_btn.grid(row=0, column=1, padx=20, pady=20, sticky="e")

        self.main_frame = ctk.CTkScrollableFrame(self, corner_radius=2, scrollbar_button_color="#393B40",
                                                 scrollbar_button_hover_color="#43454A", fg_color="transparent")
        self.main_frame.grid(row=1, column=1, padx=2, pady=2, sticky="nsew")
        self.main_frame.grid_columnconfigure(0, weight=1)

        self.pref_label = ctk.CTkLabel(self.left_frame, text="Preferences", font=("", 15, "bold"), text_color="gray60")
        self.pref_label.grid(row=0, column=0, padx=20, pady=10, sticky="w")

        self.model_btn = ctk.CTkButton(self.left_frame, text="Models", width=210, image=ICONS["models"],
                                       compound="left",
                                       anchor="w", height=40, font=("", 14),
                                       command=lambda: self.toggle_pages("models"))
        self.model_btn.grid(row=1, column=0, padx=20, pady=(10, 5), sticky="ew")

        self.gpu_btn = ctk.CTkButton(self.left_frame, text="GPU Info", width=210, image=ICONS["gpu"], compound="left",
                                     anchor="w", height=40, font=("", 14), fg_color="transparent",
                                     command=lambda: self.toggle_pages("gpu"))
        self.gpu_btn.grid(row=2, column=0, padx=20, pady=5, sticky="ew")

        self.model_widgets()

    def toggle_pages(self, page_name):
        for widgets in self.main_frame.winfo_children():
            widgets.grid_forget()

        if page_name == "models":
            self.gpu_btn.configure(fg_color="transparent")
            self.model_btn.configure(fg_color="#393B40")
            self.model_widgets()
        elif page_name == "gpu":
            self.model_btn.configure(fg_color="transparent")
            self.gpu_btn.configure(fg_color="#393B40")
            self.gpu_widget()

    def model_widgets(self):
        self.installed_models = [os.path.basename(path) for path in self.get_files(self.download_folder, "pt")]
        self.installed_models = [model.replace('.pt', '') for model in self.installed_models]

        model_data = {
            "tiny": {"description": "Least accurate but super fast", "size": "77 MB", "downloaded": False},
            "base": {"description": "Better accuracy with decent speed", "size": "148 MB", "downloaded": False},
            "small": {"description": "Good accuracy with moderate speed", "size": "487 MB", "downloaded": False},
            "medium": {"description": "Great accuracy but very slow", "size": "1.53 GB", "downloaded": False},
            "large": {"description": "Super accuracy but very slow", "size": "3.09 GB", "downloaded": False}
        }

        for model in model_data:
            if model in self.installed_models:
                model_data[model]["downloaded"] = True
            else:
                model_data[model]["downloaded"] = False

        en_model_data = {
            "tiny.en": {"description": "Least accurate but super fast", "size": "77 MB", "downloaded": False},
            "base.en": {"description": "Better accuracy with decent speed", "size": "148 MB", "downloaded": False},
            "small.en": {"description": "Good accuracy with moderate speed", "size": "487 MB", "downloaded": False},
            "medium.en": {"description": "Great accuracy but very slow", "size": "1.53 GB", "downloaded": False}
        }

        for model in en_model_data:
            if model in self.installed_models:
                en_model_data[model]["downloaded"] = True
            else:
                en_model_data[model]["downloaded"] = False

        row_index = 1

        self.title.configure(text="Model Settings")

        frame_1 = ctk.CTkFrame(self.main_frame, height=80)
        frame_1.grid(row=1, column=0, padx=20, pady=5, sticky="ew")
        frame_1.grid_propagate(False)
        frame_1.grid_columnconfigure(0, weight=1)

        frame_2 = ctk.CTkFrame(self.main_frame, height=440)
        frame_2.grid(row=2, column=0, padx=20, pady=5, sticky="ew")
        frame_2.grid_propagate(False)
        frame_2.grid_columnconfigure(0, weight=1)

        frame_3 = ctk.CTkFrame(self.main_frame, height=380)
        frame_3.grid(row=3, column=0, padx=20, pady=5, sticky="ew")
        frame_3.grid_propagate(False)
        frame_3.grid_columnconfigure(0, weight=1)

        download_label = ctk.CTkLabel(frame_1, text="Download Folder", font=("", 15))
        download_label.grid(row=0, column=0, padx=10, pady=(10, 0), sticky="w")
        self.path_label = ctk.CTkLabel(frame_1, text=self.download_folder, font=("", 12), text_color="gray70")
        self.path_label.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="w")

        open_btn = ctk.CTkButton(frame_1, text="", width=50, image=ICONS["open"],
                                 command=lambda: self.open_folder(self.download_folder))
        open_btn.grid(row=0, column=1, padx=2, pady=0, sticky="e", rowspan=2)
        CTkToolTip(open_btn, message="Open folder", corner_radius=5, x_offset=0)

        change_btn = ctk.CTkButton(frame_1, text="", width=50, image=ICONS["change"], command=self.change_path)
        change_btn.grid(row=0, column=2, padx=(2, 10), pady=0, sticky="e", rowspan=2)
        CTkToolTip(change_btn, message="Change folder", corner_radius=5, x_offset=0)

        label = ctk.CTkLabel(frame_2, text="Multilingual Models", font=("", 15, "bold"))
        label.grid(row=0, column=0, padx=20, pady=(10, 0), sticky="w")
        label_description = ctk.CTkLabel(frame_2, text="All-purpose models with support for 106 languages",
                                         font=("", 12),
                                         text_color="gray70")
        label_description.grid(row=1, column=0, padx=20, pady=(0, 10), sticky="w")

        for model_name in model_data:
            row_index += 1
            separator = ctk.CTkFrame(frame_2, height=2, fg_color="gray30")
            separator.grid(row=row_index, column=0, padx=20, pady=0, sticky="ew")

            row_index += 1

            name = model_name.capitalize()
            desc = model_data[model_name]["description"]
            size = model_data[model_name]["size"]
            is_downloaded = model_data[model_name]["downloaded"]

            self.create_model_frame(frame_2, row_index, name, desc, size, is_downloaded)

        label2 = ctk.CTkLabel(frame_3, text="English Only Models", font=("", 15, "bold"))
        label2.grid(row=0, column=0, padx=20, pady=(10, 0), sticky="w")
        label2_description = ctk.CTkLabel(frame_3, text="High-performance models exclusively for English",
                                          font=("", 12),
                                          text_color="gray70")
        label2_description.grid(row=1, column=0, padx=20, pady=(0, 10), sticky="w")

        row_index = 1

        for en_model_name in en_model_data:
            row_index += 1
            separator = ctk.CTkFrame(frame_3, height=2, fg_color="gray30")
            separator.grid(row=row_index, column=0, padx=20, pady=0, sticky="ew")

            row_index += 1

            name = en_model_name.capitalize()
            desc = en_model_data[en_model_name]["description"]
            size = en_model_data[en_model_name]["size"]
            is_downloaded = en_model_data[en_model_name]["downloaded"]

            self.create_model_frame(frame_3, row_index, name, desc, size, is_downloaded)

    def gpu_widget(self):
        # title = ctk.CTkLabel(self.main_frame, text="GPU Information", font=("", 18))
        # title.grid(row=0, column=0, padx=20, pady=20, sticky="w")
        self.title.configure(text="GPU Information")

        frame_1 = ctk.CTkFrame(self.main_frame, height=300)
        frame_1.grid(row=1, column=0, padx=20, pady=5, sticky="ew")
        frame_1.grid_propagate(False)
        frame_1.grid_columnconfigure(0, weight=1)

        get_info = get_gpu_info()

        cuda_available = get_info.get("CUDA available", "N/A")
        if cuda_available:
            cuda_available = "True"
        else:
            cuda_available = "False"

        labels = ["CUDA Available", "GPU Count", "Current GPU", "GPU Name", "Total Memory"]
        values = [cuda_available, get_info.get("Count", "N/A"), get_info.get("Current", "N/A"),
                  get_info.get("Name", "N/A"), f"{get_info.get('Total Memory', 'N/A')} GB"]

        for i, (label, value) in enumerate(zip(labels, values)):
            label_widget = ctk.CTkLabel(frame_1, text=label, font=("", 15))
            label_widget.grid(row=i, column=0, padx=20, pady=(20, 10), sticky="w")

            value_widget = ctk.CTkLabel(frame_1, text=value, font=("", 13))
            value_widget.grid(row=i, column=1, padx=20, pady=(20, 10), sticky="e")

    def create_model_frame(self, frame, index, name, desc, size, is_downloaded):
        model_frame = ctk.CTkFrame(frame, height=60)
        model_frame.grid(row=index, column=0, padx=10, pady=5, sticky="ew")
        model_frame.grid_propagate(False)
        model_frame.grid_columnconfigure(0, weight=1)

        model_name = ctk.CTkLabel(model_frame, text=name, font=("", 15, "bold"))
        model_name.grid(row=0, column=0, padx=10, pady=(5, 0), sticky="w")
        model_description = ctk.CTkLabel(model_frame, text=f"{desc} ({size})", font=("", 13),
                                         text_color="gray70")
        model_description.grid(row=1, column=0, padx=10, pady=(0, 5), sticky="w")

        if is_downloaded:
            model_name.configure(image=ICONS["downloaded"], compound="right")
            action_btn = ctk.CTkButton(model_frame, text="Delete", width=120, image=ICONS["delete"], compound="left",
                                       fg_color="gray10", hover_color="gray12",
                                       command=lambda m_name=name: self.delete_model(m_name))
            action_btn.grid(row=0, column=1, padx=10, pady=5, sticky="e", rowspan=2)
        else:
            action_btn = ctk.CTkButton(model_frame, text="Download", width=120, image=ICONS["download"],
                                       compound="left",
                                       fg_color="gray10", hover_color="gray12",
                                       command=lambda m_name=name: self.download_model(m_name))
            action_btn.grid(row=0, column=1, padx=10, pady=5, sticky="e", rowspan=2)

    def change_path(self):
        destination_directory = ctk.filedialog.askdirectory(parent=self, mustexist=True, title="move to")

        if not destination_directory:
            return

        pt_files = self.get_files(self.download_folder, "pt")

        for file in pt_files:
            self.move_file(file, destination_directory)

        save_settings({"app_settings": {"download_path": destination_directory}}, SETTINGS_FILE)

        self.download_folder = destination_directory
        self.path_label.configure(text=self.download_folder)

        ctkcomponents.CTkNotification(self, message="Download folder changed")

    def delete_model(self, name):
        model_name = str(name).lower()
        alert = ctkcomponents.CTkAlert(title="Remove Model",
                                       body_text=f"Are you sure you want to delete the model '{model_name}'? This action cannot be undone.",
                                       btn1="Yes")
        answer = alert.get()
        if not answer or answer == "Cancel":
            return

        self.installed_models = [os.path.basename(path) for path in self.get_files(self.download_folder, "pt")]
        self.installed_models = [model.replace('.pt', '') for model in self.installed_models]

        if model_name in self.installed_models:
            file_path = f"{self.download_folder}/{model_name}.pt"
            if os.path.exists(file_path):
                os.remove(file_path)

                self.toggle_pages("models")
                ctkcomponents.CTkNotification(self.root,
                                              message=f"The model '{model_name}' has been successfully deleted.")
                self.root.update()

    def download_model(self, name):
        alert = ctkcomponents.CTkAlert(state="info", title="Download",
                                       body_text=f"You are about to download the model '{name}'. Don't worry, the download will continue in the background even if you close the app.",
                                       btn1="Ok", btn2="Cancel")
        answer = alert.get()

        if not answer or answer == "Cancel":
            return

        model_name = str(name).lower()
        loader = ctkcomponents.CTkLoader(self.root)

        def start_download():
            try:
                _download(_MODELS[model_name], self.download_folder, False)
                download_complete()
            except Exception as e:
                download_incomplete(e)

        def download_complete():
            self.toggle_pages("models")
            loader.destroy()
            notification = ctkcomponents.CTkNotification(self.root,
                                                         message="Download complete! Your model is now ready for use.")
            notification.configure(width=500)
            self.root.update()

        def download_incomplete(error):
            print(error)
            self.toggle_pages("models")
            loader.destroy()
            notification = ctkcomponents.CTkNotification(self.root, state="error",
                                                         message="Download failed. Please check your connection and try again.")
            notification.configure(width=500)
            self.root.update()

        download_thread = threading.Thread(target=start_download)
        download_thread.start()

    @staticmethod
    def is_json_file_empty(filename):
        if os.stat(filename).st_size == 0:
            return True

        with open(filename, 'r') as f:
            data = json.load(f)
            if not data:
                return True

        return False

    @staticmethod
    def open_folder(path: str):
        try:
            os.startfile(path)
        except FileNotFoundError:
            pass

    @staticmethod
    def get_files(directory, extension):
        pattern = os.path.join(directory, f"*.{extension}")

        files = glob.glob(pattern)

        return files

    @staticmethod
    def move_file(source_path, destination_path):
        try:
            if not os.path.isfile(source_path):
                return f"Source file {source_path} does not exist."
            if not os.path.isdir(destination_path):
                os.makedirs(destination_path)
            shutil.move(source_path, destination_path)

            return f"File moved successfully."
        except Exception as e:
            return f"An error occurred while moving the file: {e}"

    def on_close(self):
        self.destroy()


class TranscriptionConfiguration(ctk.CTkFrame):
    def __init__(self, master: any, file_path: str = "N/A", duration: str = "00:00", **kwargs):
        WIDTH = master.winfo_reqwidth()
        HEIGHT = master.winfo_reqheight()
        super().__init__(master, width=WIDTH, height=HEIGHT, **kwargs)

        set_opacity(self.winfo_id(), value=0.9)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.root = master
        self.models = []
        self.file_path = file_path
        self.duration = duration

        self.settings = load_settings(SETTINGS_FILE)
        self.get_models = self.settings["whisper_settings"]["support_models"]
        for models in self.get_models:
            if not str(models).endswith(".en"):
                self.models.append(str(models).capitalize())

        self.get_languages = self.settings["whisper_settings"]["languages"]
        self.languages = list(self.get_languages)
        self.languages.insert(0, "Auto")

        self.main_frame = ctk.CTkFrame(self, width=600, height=450, border_width=1, corner_radius=10,
                                       fg_color="transparent")
        self.main_frame.grid(row=0, column=0, padx=20, pady=20)
        self.main_frame.grid_propagate(False)
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(3, weight=1)

        self.title = ctk.CTkLabel(self.main_frame, text="Transcription Configuration", font=("", 16))
        self.title.grid(row=0, column=0, padx=20, pady=10, sticky="ew")

        self.frame1 = ctk.CTkFrame(self.main_frame, width=600, height=220, border_width=1, border_color="#424448")
        self.frame1.grid(row=1, column=0, padx=20, pady=5)
        self.frame1.grid_propagate(False)
        self.frame1.grid_columnconfigure(0, weight=1)

        self.frame2 = ctk.CTkFrame(self.main_frame, width=600, height=95, border_width=1, border_color="#424448")
        self.frame2.grid(row=2, column=0, padx=20, pady=5)
        self.frame2.grid_propagate(False)
        self.frame2.grid_columnconfigure(0, weight=1)

        self.frame3 = ctk.CTkFrame(self.main_frame, width=600, height=55)
        self.frame3.grid(row=3, column=0, padx=5, pady=5, sticky="sew")
        self.frame3.grid_propagate(False)
        self.frame3.grid_columnconfigure(0, weight=1)

        self.model_label = ctk.CTkLabel(self.frame1, text="Model", font=("", 14), image=ICONS["model"], compound="left")
        self.model_label.grid(row=0, column=0, padx=20, pady=(20, 5), sticky="w")
        self.model_value = ctk.CTkOptionMenu(self.frame1, fg_color="#2B2D30", button_color="#2B2D30", font=("", 14),
                                             button_hover_color="#2B2D30", width=50, dropdown_hover_color="#43454A")
        self.model_dropdown = CTkScrollableDropdown(self.model_value, values=self.models, width=140, scrollbar=False,
                                                    frame_corner_radius=8, alpha=1.0, x=-20)
        self.model_value.set(self.models[0])
        self.model_value.grid(row=0, column=1, padx=20, pady=(20, 5), sticky="e")

        self.separator1 = ctk.CTkFrame(self.frame1, height=2, fg_color="#36373b")
        self.separator1.grid(row=1, column=0, padx=20, pady=5, sticky="ew", columnspan=2)

        self.language_label = ctk.CTkLabel(self.frame1, text="Transcription Language", font=("", 14),
                                           image=ICONS["language"], compound="left")
        self.language_label.grid(row=2, column=0, padx=20, pady=5, sticky="w")
        self.language_value = ctk.CTkOptionMenu(self.frame1, fg_color="#2B2D30", button_color="#2B2D30", font=("", 14),
                                                button_hover_color="#2B2D30", width=50, dropdown_hover_color="#43454A")
        self.language_dropdown = CTkScrollableDropdown(self.language_value, values=self.languages, width=140,
                                                       scrollbar=False,
                                                       frame_corner_radius=8, alpha=1.0, x=-30)
        self.language_value.set(self.languages[0])
        self.language_value.grid(row=2, column=1, padx=20, pady=5, sticky="e")

        self.separator2 = ctk.CTkFrame(self.frame1, height=2, fg_color="#36373b")
        self.separator2.grid(row=3, column=0, padx=20, pady=5, sticky="ew", columnspan=2)

        self.translate_label = ctk.CTkLabel(self.frame1, text="Translate to English", font=("", 14),
                                            image=ICONS["to_english"], compound="left")
        self.translate_label.grid(row=4, column=0, padx=20, pady=5, sticky="w")
        self.translate_value = ctk.CTkCheckBox(self.frame1, onvalue=True, offvalue=False, text="", hover=False,
                                               width=20,
                                               fg_color="#43454A")
        self.translate_value.grid(row=4, column=1, padx=20, pady=5, sticky="e")

        self.separator3 = ctk.CTkFrame(self.frame1, height=2, fg_color="#36373b")
        self.separator3.grid(row=5, column=0, padx=20, pady=5, sticky="ew", columnspan=2)

        self.prompt_label = ctk.CTkLabel(self.frame1, text="Prompt", font=("", 14), image=ICONS["prompt"],
                                         compound="left")
        self.prompt_label.grid(row=6, column=0, padx=20, pady=5, sticky="w")
        self.prompt_value = ctk.CTkTextbox(self.frame1, height=30, width=150)
        self.prompt_value.insert("end", "Insert Prompt (optional)")
        self.prompt_value.grid(row=6, column=1, padx=20, pady=5, sticky="e")

        self.file_title = ctk.CTkLabel(self.frame2, text="Imported Files", font=("", 14, "bold"))
        self.file_title.grid(row=0, column=0, padx=10, pady=5, sticky="w")

        self.separator4 = ctk.CTkFrame(self.frame2, height=2, fg_color="#36373b")
        self.separator4.grid(row=1, column=0, padx=0, pady=5, sticky="ew", columnspan=2)

        self.file_label = ctk.CTkLabel(self.frame2, text=self.file_path, font=("", 13), image=ICONS["audio_file"],
                                       compound="left", text_color="gray70")
        self.file_label.grid(row=2, column=0, padx=20, pady=5, sticky="w")

        self.duration_label = ctk.CTkLabel(self.frame2, text=self.duration, text_color="gray70")
        self.duration_label.grid(row=2, column=1, padx=20, pady=5, sticky="w")

        self.transcribe_btn = ctk.CTkButton(self.frame3, text="Transcribe", width=150, height=35,
                                            command=self.transcribe_callback)
        self.transcribe_btn.grid(row=0, column=0, padx=(20, 5), pady=10, sticky="nse")

        self.cancel_btn = ctk.CTkButton(self.frame3, text="Cancel", width=150, height=35, border_width=1,
                                        fg_color="transparent", command=self.on_close)
        self.cancel_btn.grid(row=0, column=1, padx=(5, 20), pady=10, sticky="nse")

    def transcribe_callback(self):
        file_path = self.file_path
        model = self.model_value.get().lower()
        language = self.language_value.get().lower()
        translate = self.translate_value.get()
        task = "translate" if translate else "transcribe"
        prompt = self.prompt_value.get("0.0", "end")

        loader = ctkcomponents.CTkLoader(self.root)
        self.on_close()

        def start_transcription():
            try:
                transcriber = Transcriber(file_path, model_size=model, language=language, task=task, prompt=prompt)
                result = transcriber.transcribe()
                self.root.update_result(result)
            except Exception as e:
                print(e)
            finally:
                if loader.winfo_exists():
                    loader.destroy()

        thread = threading.Thread(target=start_transcription, daemon=True)
        thread.start()

    def on_close(self):
        self.destroy()


class ExportWindow(ctk.CTkFrame):
    def __init__(self, master: any, audio_path, result, **kwargs):
        WIDTH = master.winfo_reqwidth()
        HEIGHT = master.winfo_reqheight()
        super().__init__(master, width=WIDTH, height=HEIGHT, corner_radius=0, **kwargs)

        self.root = master
        self.audio_path = audio_path
        self.result = result

        set_opacity(self.winfo_id(), value=0.9)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.main_frame = ctk.CTkFrame(self, width=490, height=210, border_width=1, corner_radius=10)
        self.main_frame.grid(row=0, column=0, padx=20, pady=20)
        self.main_frame.grid_propagate(False)
        self.main_frame.grid_columnconfigure(0, weight=1)

        self.title = ctk.CTkLabel(self.main_frame, text="Download Text and Subtitles", font=("", 18))
        self.title.grid(row=0, column=0, padx=20, pady=20, sticky="w")

        self.label = ctk.CTkLabel(self.main_frame, text="Format", font=("", 15))
        self.label.grid(row=1, column=0, padx=20, pady=(10, 0), sticky="w")

        self.values = [
            "Text File (.txt)",
            "Subtitles (.srt)",
            "WebVTT (.vtt)",
            "Tab-Separated Values (.tsv)",
            "JSON File (.json)",
            "Save as all extensions"
        ]

        self.option = ctk.CTkOptionMenu(self.main_frame, fg_color="#2B2D30", button_color="#2B2D30", font=("", 14),
                                        button_hover_color="#2B2D30", width=200, dropdown_hover_color="#43454A")
        self.option_dropdown = CTkScrollableDropdown(self.option, values=self.values, width=250, scrollbar=False,
                                                     frame_corner_radius=8, alpha=1.0, x=0)
        self.option.set(self.values[0])
        self.option.grid(row=2, column=0, padx=20, pady=(0, 20), sticky="w")

        self.export_btn = ctk.CTkButton(self.main_frame, text="Export", command=self.export_callback, height=30,
                                        width=150)
        self.export_btn.grid(row=3, column=0, padx=(20, 5), pady=10, sticky="e")

        self.cancel_btn = ctk.CTkButton(self.main_frame, text="Cancel", command=self.on_close, height=30, width=80)
        self.cancel_btn.grid(row=3, column=1, padx=(5, 20), pady=10, sticky="ew")

    def export_callback(self):
        file_name = os.path.basename(self.audio_path).split(".", 1)[0]
        file_extension_map = {
            "Text File (.txt)": ".txt",
            "Subtitles (.srt)": ".srt",
            "WebVTT (.vtt)": ".vtt",
            "Tab-Separated Values (.tsv)": ".tsv",
            "JSON File (.json)": ".json",
            "Save as all extensions": ".all",
        }

        extension = self.option.get()

        file_extension = file_extension_map[extension]
        output_path = ctk.filedialog.asksaveasfilename(
            parent=self.root,
            initialfile=file_name,
            title="Export subtitle",
            defaultextension=file_extension,
            filetypes=[(f"{extension} Files", "*" + file_extension)]
        )
        if output_path:
            dir_name, _ = os.path.split(output_path)
            try:
                writer = get_writer(file_extension.strip("."), dir_name)
                writer(self.result, self.audio_path,
                       {"highlight_words": True, "max_line_count": 50, "max_line_width": 3})
                ctkcomponents.CTkNotification(self.root, state="info", message="Export successful!")
            except Exception as e:
                ctkcomponents.CTkNotification(self.root, state="error", message=str(e))
            finally:
                self.on_close()

    def on_close(self):
        self.destroy()


class APP(ctk.CTk):
    WIDTH = 1300
    HEIGHT = 900

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        center_window(self, self.WIDTH, self.HEIGHT)
        self.resizable(False, False)
        self.title("Winsper")
        self.iconbitmap(LOGO)

        self.create_settings()

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        self.copy_btn = None
        self.export_btn = None
        self.audio_title = None
        self.result_frame = None
        self.file_frame = None
        self.pages = {}
        self.current_page = None

        self.sidebar_frame = ctk.CTkFrame(self, width=300, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, padx=0, pady=0, sticky="nsw")
        self.sidebar_frame.grid_propagate(False)

        self.main_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_frame.grid(row=0, column=1, padx=0, pady=0, sticky="nsew")
        self.main_frame.grid_propagate(False)
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(1, weight=1)

        self.sidebar_widgets()

    def sidebar_widgets(self):
        open_btn = ctk.CTkButton(self.sidebar_frame, text="New File", width=200, height=35, image=ICONS["new"],
                                 compound="left", anchor="w", font=("", 15), command=self.select_file)
        open_btn.grid(row=0, column=0, padx=(20, 10), pady=20, sticky="ew")

        settings_btn = ctk.CTkButton(self.sidebar_frame, text="", width=48, height=35, image=ICONS["settings"],
                                     command=self.open_settings)
        settings_btn.grid(row=0, column=1, padx=(10, 20), pady=20, sticky="nsew")

        separator = ctk.CTkFrame(self.sidebar_frame, width=280, height=2, corner_radius=0, fg_color="#393B40")
        separator.grid(row=1, column=0, padx=0, pady=10, sticky="n", columnspan=2)

        self.file_frame = ctk.CTkFrame(self.sidebar_frame, width=280, fg_color="transparent")
        self.file_frame.grid(row=2, column=0, padx=0, pady=10, sticky="n", columnspan=2)

    def open_settings(self):
        Settings(self).grid(row=0, column=0, padx=0, pady=0, columnspan=2, sticky="nsew")

    def open_transcriber(self, file_path, duration):
        transcriber = TranscriptionConfiguration(self, file_path, duration)
        transcriber.grid(row=0, column=0, padx=0, pady=0, columnspan=2, sticky="nsew")

    def open_export(self, audio_path, result):
        export = ExportWindow(self, audio_path, result)
        export.grid(row=0, column=0, padx=0, pady=0, columnspan=2, sticky="nsew")

    def delete_opened_file(self, page_name):
        data = self.pages[page_name]
        data["button"].destroy()
        self.pages.pop(page_name)

        try:
            first_key = next(iter(self.pages))
            self.toggle_pages(first_key)
        except StopIteration:
            self.current_page = None
            for widget in self.main_frame.winfo_children():
                widget.grid_forget()

    def select_file(self):
        file_path = filedialog.askopenfilename(parent=self, defaultextension=".mp3",
                                               filetypes=[("Audio files", "*.mp3 *.wav")])
        if not file_path:
            return

        get_base_name = os.path.basename(file_path)
        base_name, extension = os.path.splitext(get_base_name)
        duration = self.get_audio_duration(file_path)
        title = self.truncate_text(base_name, 35)

        if not duration:
            ctkcomponents.CTkNotification(master=self, state="error",
                                          message="An error occurred while processing the audio file")
            return

        file_btn = ctk.CTkButton(self.file_frame, text="", width=280, height=50)
        file_btn.grid(padx=0, pady=5, sticky="ew")
        file_name = ctk.CTkLabel(file_btn,
                                 text=title,
                                 font=("", 18), compound="left")
        file_name.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        set_opacity(file_name.winfo_id(), color=file_name.cget("bg_color")[1])

        file_details = ctk.CTkLabel(file_btn, text=f"{extension.upper()}   {duration}", font=("", 12),
                                    text_color="gray70")
        file_details.grid(row=1, column=0, padx=5, pady=0, sticky="w")
        set_opacity(file_details.winfo_id(), color=file_details.cget("bg_color")[1])

        data = {
            "button": file_btn,
            "title": base_name,
            "path": file_path,
            "text": None
        }

        self.pages[base_name] = data

        file_btn.configure(command=lambda: self.toggle_pages(base_name))

        self.toggle_pages(base_name)

        popup_menu = ctkcomponents.CTkPopupMenu(master=file_btn, width=180, height=150, title="Options",
                                                corner_radius=5, border_width=1, fg_color="#393B40",
                                                border_color="#5A5D63")
        file_btn.bind("<Button-3>", lambda event, menu=popup_menu: ctkcomponents.do_popup(event, menu),
                      add="+")

        btn1 = ctk.CTkButton(popup_menu.frame, text="Delete",
                             command=lambda value=base_name: self.delete_opened_file(value), **BTN_OPTION,
                             image=ICONS["delete"])
        btn1.pack(expand=True, fill="x", padx=10, pady=0)

        btn2 = ctk.CTkButton(popup_menu.frame, text="Transcribe",
                             command=lambda value1=file_path, value2=duration: self.open_transcriber(value1, value2),
                             **BTN_OPTION,
                             image=ICONS["transcribe"])
        btn2.pack(expand=True, fill="x", padx=10, pady=(0, 1))

        self.open_transcriber(file_path, duration)

    def toggle_pages(self, page_name):
        data = self.pages[page_name]

        try:
            self.audio_title.destroy()
        except Exception:
            pass

        self.audio_title = ctk.CTkLabel(self.main_frame, text="", font=("", 20, "bold"))
        self.audio_title.grid(row=0, column=0, padx=20, pady=(20, 5), sticky="w")
        self.audio_title.configure(text=data["title"])

        self.result_frame = ctk.CTkScrollableFrame(self.main_frame, corner_radius=2, scrollbar_button_color="#393B40",
                                                   scrollbar_button_hover_color="#43454A", fg_color="transparent")
        self.result_frame.grid(row=1, column=0, padx=0, pady=5, sticky="nsew", columnspan=3)

        audio_player = CTkAudioPlayer(self.main_frame, data["path"])
        audio_player.grid(row=2, column=0, padx=20, pady=(5, 10), sticky="w")

        self.copy_btn = ctk.CTkButton(self.main_frame, text="Plain Text", width=150, height=35, image=ICONS["text"],
                                      compound="left", font=("", 14), command=lambda: self.copy_text(data["text"]))
        self.copy_btn.grid(row=2, column=1, padx=(10, 3), pady=(5, 10), sticky="sw")

        self.export_btn = ctk.CTkButton(self.main_frame, text="Export Options", height=35, image=ICONS["cc"],
                                        compound="left",
                                        font=("", 14), command=lambda: self.open_export(data["path"], data["text"]))
        self.export_btn.grid(row=2, column=2, padx=(3, 10), pady=(5, 10), sticky="sw")

        self.copy_btn.configure(state="disabled")
        self.export_btn.configure(state="disabled")

        if data["text"]:
            self.copy_btn.configure(state="normal")
            self.export_btn.configure(state="normal")

        self.current_page = page_name

        self.after(100, lambda: self.update_result(self.pages[self.current_page]["text"]))

    def update_result(self, result):
        self.pages[self.current_page]["text"] = result
        if result:
            for index, segment in enumerate(result['segments'], start=0):
                start = timedelta(seconds=int(segment['start']))
                end = timedelta(seconds=int(segment['end']))
                text = segment['text']

                time_stamps = ctk.CTkLabel(self.result_frame, text=f"{start} --> {end}", width=140, height=30,
                                           fg_color="#2B2D30",
                                           corner_radius=8)
                time_stamps.grid(row=index, column=0, padx=10, pady=5, sticky="w")

                text_label = ctk.CTkLabel(self.result_frame,
                                          text=text,
                                          height=30, font=("", 16),
                                          justify="left",
                                          anchor="w",
                                          cursor="xterm")
                text_label.grid(row=index, column=1, padx=5, pady=5, sticky="nsew")

            self.copy_btn.configure(state="normal")
            self.export_btn.configure(state="normal")

    def copy_text(self, text):
        if text:
            text = text["text"]
            self.clipboard_clear()
            self.clipboard_append(text)
            ctkcomponents.CTkNotification(self, state="info", message="Text copied to clipboard!")

    @staticmethod
    def create_settings():
        if not os.path.exists(SETTINGS_FILE):
            os.mkdir(os.path.join(PATH, "settings"))
            save_default(SETTINGS_FILE)

    @staticmethod
    def get_audio_duration(file_path):
        try:
            mixer.init()
            mixer.music.load(file_path)
            audio = File(file_path)
            duration_s = int(audio.info.length)
            hours, remainder = divmod(duration_s, 3600)
            minutes, seconds = divmod(remainder, 60)

            return f"{hours:02}:{minutes:02}:{seconds:02}"

        except (error, MutagenError) as e:
            return None

    @staticmethod
    def truncate_text(text, max_length):
        if len(text) > max_length:
            return text[:max_length - 3] + '...'
        else:
            return text


if __name__ == "__main__":
    if not platform.system() == "Windows":
        print("[!] This app only support Windows operating system.")
        sys.exit()

    app = APP()
    apply_style(app, "mica")
    app.mainloop()
