import difflib
import json
import os
import sys
import time

import customtkinter
import pynvml
import whisper
from pydub import AudioSegment
from whisper.tokenizer import LANGUAGES

CURRENT_PATH = os.path.dirname(os.path.realpath(__file__))
SETTINGS_FILE = os.path.join(CURRENT_PATH, "settings", "settings.json")
HOME_DIR = os.path.expanduser("~")
DOWNLOAD_DIRECTORY = os.path.join(HOME_DIR, ".cache", "whisper")


def center_window(root, width, height):
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    window_height = int((screen_width / 2) - (width / 2))
    window_width = int((screen_height / 2) - (height / 2))
    root.geometry(f"{width}x{height}+{window_height}+{window_width}")


def get_gpu_info():
    pynvml.nvmlInit()

    cuda_available = pynvml.nvmlDeviceGetCount() > 0
    gpu_count = pynvml.nvmlDeviceGetCount()

    handle = pynvml.nvmlDeviceGetHandleByIndex(0)

    gpu_name = pynvml.nvmlDeviceGetName(handle)
    mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
    total_mem = int(mem_info.total / 1e9)

    gpu_info = {
        "CUDA": cuda_available,
        "Count": gpu_count,
        "Current": 0,
        "Name": gpu_name,
        "Total Memory": total_mem
    }

    pynvml.nvmlShutdown()

    return gpu_info


def supported_models():
    try:
        pynvml.nvmlInit()
        cuda_available = pynvml.nvmlDeviceGetCount() > 0
        cuda = True
        if not cuda_available:
            cuda = False

        device = pynvml.nvmlDeviceGetHandleByIndex(0)

        total_mem = pynvml.nvmlDeviceGetMemoryInfo(device).total
        total_mem_gb = round(total_mem / (1024 ** 3))

        model_req = {
            10: ["large", "large-v1", "large-v2", "large-v3"],
            5: ["medium", "medium.en"],
            2: ["small", "small.en"],
            1: ["tiny", "base", "tiny.en", "base.en"]
        }

        models_list = []
        for req, model in model_req.items():
            if total_mem_gb >= req:
                if isinstance(model, list):
                    models_list.extend(model)
                else:
                    models_list.append(model)

        pynvml.nvmlShutdown()

        return cuda, models_list
    except pynvml.NVMLError as error:
        print(f"An error occurred while getting the GPU information: {str(error)}")
        return False, False
    except Exception as e:
        print(f"An unexpected error occurred: {str(e)}")
        return False, False


def save_settings(settings, filename):
    try:
        existing_settings = load_settings(filename)
        if isinstance(existing_settings, str):
            existing_settings = {}

        def merge_dicts(d1, d2):
            for k, v in d1.items():
                if k in d2:
                    if isinstance(v, dict) and isinstance(d2[k], dict):
                        d2[k] = merge_dicts(v, d2[k])
            d3 = d1.copy()
            d3.update(d2)
            return d3

        merged_settings = merge_dicts(existing_settings, settings)

        with open(filename, 'w') as f:
            json.dump(merged_settings, f, indent=4)

        return "Settings saved successfully."
    except Exception as e:
        return f"An error occurred while saving the settings: {e}"


def load_settings(filename):
    try:
        if not os.path.isfile(filename):
            return {}
        with open(filename, 'r') as f:
            settings = json.load(f)
        return settings
    except Exception as e:
        return {}


def save_default(filename: str = SETTINGS_FILE):
    try:
        os.remove(filename)
    except FileNotFoundError:
        pass

    languages = [language.capitalize() for language in LANGUAGES.values()]
    cuda, models = supported_models()

    default_settings = {
        "app_settings": {
            "download_path": DOWNLOAD_DIRECTORY
        },
        "whisper_settings": {
            "cuda_available": cuda,
            "support_models": models,
            "languages": languages
        }
    }

    result = save_settings(default_settings, filename)

    return result


class Transcriber:
    MODELS = whisper.available_models()

    def __init__(self, file: str = None, model_size: str = "base", language: str = "auto", task: str = "transcribe",
                 prompt: str = None):

        self.file = file

        if self.file:
            is_valid, message = self.validate_file(self.file)
            if not is_valid:
                raise ValueError(message)
        else:
            raise ValueError("File not provided")

        if model_size not in self.MODELS:
            print(f"Model ({model_size}) not available, using default: base")
            model_size = "base"

        if language == 'auto':
            language = self.detect_language()

        if language in ['en', 'english'] and model_size not in ["large", "large-v1", "large-v2", "large-3"]:
            model_size += '.en'

        if task == 'translate' and language == 'en':
            print("Can't translate english to english, using default: transcribe")
            task = "transcribe"

        settings = load_settings(SETTINGS_FILE)

        self.model = whisper.load_model(model_size, download_root=settings["app_settings"]["download_path"])
        self.language = language
        self.task = task

    def transcribe(self):
        get_result = self.model.transcribe(self.file, language=self.language, task=self.task)
        # result = get_result["text"].strip()

        return get_result

    def detect_language(self):
        model = whisper.load_model("base")
        audio = whisper.load_audio(self.file)
        audio = whisper.pad_or_trim(audio)

        mel = whisper.log_mel_spectrogram(audio).to(model.device)

        _, probs = model.detect_language(mel)
        return f"{max(probs, key=probs.get)}"

    @staticmethod
    def validate_file(file_path: str):
        if not os.path.isfile(file_path):
            return False, "File does not exist"

        try:
            AudioSegment.from_file(file_path)

            return True, "File is a valid audio file"
        except:
            return False, "File is not a valid audio file"


class CTkScrollableDropdown(customtkinter.CTkToplevel):

    def __init__(self, attach, x=None, y=None, button_color=None, height: int = 200, width: int = None,
                 fg_color=None, button_height: int = 20, justify="center", scrollbar_button_color=None,
                 scrollbar=True, scrollbar_button_hover_color=None, frame_border_width=2, values=[],
                 command=None, image_values=[], alpha: float = 0.97, frame_corner_radius=20, double_click=False,
                 resize=True, frame_border_color=None, text_color=None, autocomplete=False,
                 hover_color=None, **button_kwargs):

        super().__init__(takefocus=1)

        self.focus()
        self.lift()
        self.alpha = alpha
        self.attach = attach
        self.corner = frame_corner_radius
        self.padding = 0
        self.focus_something = False
        self.disable = True
        self.update()

        if sys.platform.startswith("win"):
            self.after(100, lambda: self.overrideredirect(True))
            self.transparent_color = self._apply_appearance_mode(self._fg_color)
            self.attributes("-transparentcolor", self.transparent_color)
        elif sys.platform.startswith("darwin"):
            self.overrideredirect(True)
            self.transparent_color = 'systemTransparent'
            self.attributes("-transparent", True)
            self.focus_something = True
        else:
            self.overrideredirect(True)
            self.transparent_color = '#000001'
            self.corner = 0
            self.padding = 18
            self.withdraw()

        self.hide = True
        self.attach.bind('<Configure>', lambda e: self._withdraw() if not self.disable else None, add="+")
        self.attach.winfo_toplevel().bind('<Configure>', lambda e: self._withdraw() if not self.disable else None,
                                          add="+")
        self.attach.winfo_toplevel().bind("<ButtonPress>", lambda e: self._withdraw() if not self.disable else None,
                                          add="+")

        self.attributes('-alpha', 0)
        self.disable = False
        self.fg_color = customtkinter.ThemeManager.theme["CTkFrame"]["fg_color"] if fg_color is None else fg_color
        self.scroll_button_color = customtkinter.ThemeManager.theme["CTkScrollbar"][
            "button_color"] if scrollbar_button_color is None else scrollbar_button_color
        self.scroll_hover_color = customtkinter.ThemeManager.theme["CTkScrollbar"][
            "button_hover_color"] if scrollbar_button_hover_color is None else scrollbar_button_hover_color
        self.frame_border_color = customtkinter.ThemeManager.theme["CTkFrame"][
            "border_color"] if frame_border_color is None else frame_border_color
        self.button_color = customtkinter.ThemeManager.theme["CTkFrame"][
            "top_fg_color"] if button_color is None else button_color
        self.text_color = customtkinter.ThemeManager.theme["CTkLabel"][
            "text_color"] if text_color is None else text_color
        self.hover_color = customtkinter.ThemeManager.theme["CTkButton"][
            "hover_color"] if hover_color is None else hover_color

        if scrollbar is False:
            self.scroll_button_color = self.fg_color
            self.scroll_hover_color = self.fg_color

        self.frame = customtkinter.CTkScrollableFrame(self, bg_color=self.transparent_color, fg_color=self.fg_color,
                                                      scrollbar_button_hover_color=self.scroll_hover_color,
                                                      corner_radius=self.corner, border_width=frame_border_width,
                                                      scrollbar_button_color=self.scroll_button_color,
                                                      border_color=self.frame_border_color)
        self.frame._scrollbar.grid_configure(padx=3)
        self.frame.pack(expand=True, fill="both")
        self.dummy_entry = customtkinter.CTkEntry(self.frame, fg_color="transparent", border_width=0, height=1, width=1)
        self.no_match = customtkinter.CTkLabel(self.frame, text="No Match")
        self.height = height
        self.height_new = height
        self.width = width
        self.command = command
        self.fade = False
        self.resize = resize
        self.autocomplete = autocomplete
        self.var_update = customtkinter.StringVar()
        self.appear = False

        if justify.lower() == "left":
            self.justify = "w"
        elif justify.lower() == "right":
            self.justify = "e"
        else:
            self.justify = "c"

        self.button_height = button_height
        self.values = values
        self.button_num = len(self.values)
        self.image_values = None if len(image_values) != len(self.values) else image_values

        self.resizable(width=False, height=False)
        self.transient(self.master)
        self._init_buttons(**button_kwargs)

        # Add binding for different ctk widgets
        if double_click or self.attach.winfo_name().startswith("!ctkentry") or self.attach.winfo_name().startswith(
                "!ctkcombobox"):
            self.attach.bind('<Double-Button-1>', lambda e: self._iconify(), add="+")
        else:
            self.attach.bind('<Button-1>', lambda e: self._iconify(), add="+")

        if self.attach.winfo_name().startswith("!ctkcombobox"):
            self.attach._canvas.tag_bind("right_parts", "<Button-1>", lambda e: self._iconify())
            self.attach._canvas.tag_bind("dropdown_arrow", "<Button-1>", lambda e: self._iconify())
            if self.command is None:
                self.command = self.attach.set

        if self.attach.winfo_name().startswith("!ctkoptionmenu"):
            self.attach._canvas.bind("<Button-1>", lambda e: self._iconify())
            self.attach._text_label.bind("<Button-1>", lambda e: self._iconify())
            if self.command is None:
                self.command = self.attach.set

        self.attach.bind("<Destroy>", lambda _: self._destroy(), add="+")

        self.update_idletasks()
        self.x = x
        self.y = y

        if self.autocomplete:
            self.bind_autocomplete()

        self.deiconify()
        self.withdraw()

        self.attributes("-alpha", self.alpha)

    def _destroy(self):
        self.after(500, self.destroy_popup)

    def _withdraw(self):
        if self.winfo_viewable() and self.hide:
            self.withdraw()

        self.event_generate("<<Closed>>")
        self.hide = True

    def _update(self, a, b, c):
        self.live_update(self.attach._entry.get())

    def bind_autocomplete(self, ):
        def appear(x):
            self.appear = True

        if self.attach.winfo_name().startswith("!ctkcombobox"):
            self.attach._entry.configure(textvariable=self.var_update)
            self.attach._entry.bind("<Key>", appear)
            self.attach.set(self.values[0])
            self.var_update.trace_add('write', self._update)

        if self.attach.winfo_name().startswith("!ctkentry"):
            self.attach.configure(textvariable=self.var_update)
            self.attach.bind("<Key>", appear)
            self.var_update.trace_add('write', self._update)

    def fade_out(self):
        for i in range(100, 0, -10):
            if not self.winfo_exists():
                break
            self.attributes("-alpha", i / 100)
            self.update()
            time.sleep(1 / 100)

    def fade_in(self):
        for i in range(0, 100, 10):
            if not self.winfo_exists():
                break
            self.attributes("-alpha", i / 100)
            self.update()
            time.sleep(1 / 100)

    def _init_buttons(self, **button_kwargs):
        self.i = 0
        self.widgets = {}
        for row in self.values:
            self.widgets[self.i] = customtkinter.CTkButton(self.frame,
                                                           text=row,
                                                           height=self.button_height,
                                                           fg_color=self.button_color,
                                                           text_color=self.text_color,
                                                           image=self.image_values[
                                                               self.i] if self.image_values is not None else None,
                                                           anchor=self.justify,
                                                           command=lambda k=row: self._attach_key_press(k),
                                                           **button_kwargs)
            self.widgets[self.i].pack(fill="x", pady=2, padx=(self.padding, 0))
            self.i += 1

        self.hide = False

    def destroy_popup(self):
        self.destroy()
        self.disable = True

    def place_dropdown(self):
        self.x_pos = self.attach.winfo_rootx() if self.x is None else self.x + self.attach.winfo_rootx()
        self.y_pos = self.attach.winfo_rooty() + self.attach.winfo_reqheight() + 5 if self.y is None else self.y + self.attach.winfo_rooty()
        self.width_new = self.attach.winfo_width() if self.width is None else self.width

        if self.resize:
            if self.button_num <= 5:
                self.height_new = self.button_height * self.button_num + 55
            else:
                self.height_new = self.button_height * self.button_num + 35
            if self.height_new > self.height:
                self.height_new = self.height

        self.geometry('{}x{}+{}+{}'.format(self.width_new, self.height_new,
                                           self.x_pos, self.y_pos))
        self.fade_in()
        self.attributes('-alpha', self.alpha)
        self.attach.focus()

    def _iconify(self):
        if self.attach.cget("state") == "disabled": return
        if self.disable: return
        if self.hide:
            self.event_generate("<<Opened>>")
            self._deiconify()
            self.focus()
            self.hide = False
            self.place_dropdown()
            if self.focus_something:
                self.dummy_entry.pack()
                self.dummy_entry.focus_set()
                self.after(100, self.dummy_entry.pack_forget)
        else:
            self.withdraw()
            self.hide = True

    def _attach_key_press(self, k):
        self.event_generate("<<Selected>>")
        self.fade = True
        if self.command:
            self.command(k)
        self.fade = False
        self.fade_out()
        self.withdraw()
        self.hide = True

    def live_update(self, string=None):
        if not self.appear: return
        if self.disable: return
        if self.fade: return
        if string:
            string = string.lower()
            self._deiconify()
            i = 1
            for key in self.widgets.keys():
                s = self.widgets[key].cget("text").lower()
                text_similarity = difflib.SequenceMatcher(None, s[0:len(string)], string).ratio()
                similar = s.startswith(string) or text_similarity > 0.75
                if not similar:
                    self.widgets[key].pack_forget()
                else:
                    self.widgets[key].pack(fill="x", pady=2, padx=(self.padding, 0))
                    i += 1

            if i == 1:
                self.no_match.pack(fill="x", pady=2, padx=(self.padding, 0))
            else:
                self.no_match.pack_forget()
            self.button_num = i
            self.place_dropdown()

        else:
            self.no_match.pack_forget()
            self.button_num = len(self.values)
            for key in self.widgets.keys():
                self.widgets[key].destroy()
            self._init_buttons()
            self.place_dropdown()

        self.frame._parent_canvas.yview_moveto(0.0)
        self.appear = False

    def insert(self, value, **kwargs):
        self.widgets[self.i] = customtkinter.CTkButton(self.frame,
                                                       text=value,
                                                       height=self.button_height,
                                                       fg_color=self.button_color,
                                                       text_color=self.text_color,
                                                       anchor=self.justify,
                                                       command=lambda k=value: self._attach_key_press(k), **kwargs)
        self.widgets[self.i].pack(fill="x", pady=2, padx=(self.padding, 0))
        self.i += 1
        self.values.append(value)

    def _deiconify(self):
        if len(self.values) > 0:
            self.deiconify()

    def popup(self, x=None, y=None):
        self.x = x
        self.y = y
        self.hide = True
        self._iconify()

    def configure(self, **kwargs):
        if "height" in kwargs:
            self.height = kwargs.pop("height")
            self.height_new = self.height

        if "alpha" in kwargs:
            self.alpha = kwargs.pop("alpha")

        if "width" in kwargs:
            self.width = kwargs.pop("width")

        if "fg_color" in kwargs:
            self.frame.configure(fg_color=kwargs.pop("fg_color"))

        if "values" in kwargs:
            self.values = kwargs.pop("values")
            self.image_values = None
            self.button_num = len(self.values)
            for key in self.widgets.keys():
                self.widgets[key].destroy()
            self._init_buttons()

        if "image_values" in kwargs:
            self.image_values = kwargs.pop("image_values")
            self.image_values = None if len(self.image_values) != len(self.values) else self.image_values
            if self.image_values is not None:
                i = 0
                for key in self.widgets.keys():
                    self.widgets[key].configure(image=self.image_values[i])
                    i += 1

        if "button_color" in kwargs:
            for key in self.widgets.keys():
                self.widgets[key].configure(fg_color=kwargs.pop("button_color"))

        if "hover_color" not in kwargs:
            kwargs["hover_color"] = self.hover_color

        for key in self.widgets.keys():
            self.widgets[key].configure(**kwargs)
