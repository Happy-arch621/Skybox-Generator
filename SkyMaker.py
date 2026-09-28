import tkinter as tk
from tkinter import filedialog, ttk, messagebox
from PIL import Image
import numpy as np
import json
import os
import threading
import shutil
import random
import string
import sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

VERSION = '2.0.0'

# ---------------------------------------------------------------------------
# Idiomas / Languages
# ---------------------------------------------------------------------------

CURRENT_LANG = 'en'

TRANSLATIONS = {
    'en': {
        'lang_button':      "Español",
        'blend_label':      "Seam Blend Width (Pixels):",
        'no_images':        "No images selected.",
        'selected_images':  "Selected {count} image(s):\n{names}",
        'select_title':     "Select Panoramic Images",
        'image_files':      "Image Files",
        'all_files':        "All Files",
        'select_btn':       "Select Images",
        'create_btn':       "Create Sky",
        'dnd_ready':        "Drag & Drop is ready!",
        'starting':         "Starting: {name}",
        'all_finished':     "All tasks finished!",
        'error_title':      "Error",
        'error_failed':     "Failed to process {name}:\n{error}",
        'loading_pano':     "Loading panorama...",
        'healing_seam':     "Healing panorama seam...",
        'generated_face':   "Generated face: {face}",
        'analysing_seam':   "Analysing seam...",
        'blending_seams':   "Blending seams...",
        'assembling':       "Assembling skybox template...",
        'encoding':         "Encoding skybox template...",
        'saving_assets':    "Saving assets...",
        'writing_props':    "Writing sky properties...",
        'creating_zip':     "Creating ZIP archive...",
    },
    'es': {
        'lang_button':      "English",
        'blend_label':      "Ancho de fusión (píxeles):",
        'no_images':        "No hay imágenes seleccionadas.",
        'selected_images':  "{count} imagen(es) seleccionada(s):\n{names}",
        'select_title':     "Seleccionar imágenes panorámicas",
        'image_files':      "Archivos de imagen",
        'all_files':        "Todos los archivos",
        'select_btn':       "Seleccionar imágenes",
        'create_btn':       "Crear cielo",
        'dnd_ready':        "¡Arrastrar y soltar está listo!",
        'starting':         "Iniciando: {name}",
        'all_finished':     "¡Todas las tareas terminaron!",
        'error_title':      "Error",
        'error_failed':     "No se pudo procesar {name}:\n{error}",
        'loading_pano':     "Cargando panorama...",
        'healing_seam':     "Reparando costura del panorama...",
        'generated_face':   "Cara generada: {face}",
        'analysing_seam':   "Analizando costura...",
        'blending_seams':   "Fusionando costuras...",
        'assembling':       "Ensamblando plantilla del skybox...",
        'encoding':         "Codificando plantilla del skybox...",
        'saving_assets':    "Guardando archivos...",
        'writing_props':    "Escribiendo propiedades del cielo...",
        'creating_zip':     "Creando archivo ZIP...",
    },
}


def t(key: str, **kwargs) -> str:
    """Devuelve el texto traducido al idioma actual."""
    text = TRANSLATIONS[CURRENT_LANG].get(key, TRANSLATIONS['en'].get(key, key))
    return text.format(**kwargs) if kwargs else text


def _log(tag: str, msg: str) -> None:
    """Structured console log. Format: [TAG  ]  message"""
    print(f"[{tag:<5}]  {msg}")

FACE_SIZE = 2048
FACE_NAMES = ['right', 'back', 'top', 'bottom', 'front', 'left']

PACK_FORMAT = 15  # Minecraft 1.20.x

SKY_LAYERS = [
    {
        "id": 1,
        "startFadeIn": "18:00", "endFadeIn": "18:45",
        "startFadeOut": "18:50", "endFadeOut": "19:10",
        "blend": "add", "rotate": True, "axis": "0.0 -0.2 0.0",
        "source": "cloud2.png",
    },
    {
        "id": 2,
        "startFadeIn": "4:45", "endFadeIn": "5:10",
        "startFadeOut": "5:20", "endFadeOut": "6:05",
        "blend": "add", "rotate": True, "axis": "0.0 -0.2 0.0",
        "source": "cloud2.png",
    },
    {
        "id": 3,
        "startFadeIn": "5:30", "endFadeIn": "6:00",
        "startFadeOut": "17:30", "endFadeOut": "18:20",
        "blend": "replace", "rotate": True, "axis": "0.0 -0.2 0.0",
        "source": "cloud1.png",
    },
    {
        "id": 4,
        "startFadeIn": "17:30", "endFadeIn": "20:00",
        "startFadeOut": None, "endFadeOut": "6:10",
        "blend": "add", "rotate": True, "axis": None,
        "source": "starfield01.png",
    },
    {
        "id": 5,
        "startFadeIn": "19:30", "endFadeIn": "19:50",
        "startFadeOut": None, "endFadeOut": "4:40",
        "blend": "add", "rotate": True, "axis": "0.0 -0.2 0.0",
        "source": "starfield02.png",
    },
    {
        "id": 6,
        "startFadeIn": "18:30", "endFadeIn": "18:45",
        "startFadeOut": None, "endFadeOut": "5:25",
        "blend": "add", "rotate": True, "axis": "0.0 -0.2 0.0",
        "source": "starfield03.png",
    },
]


# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------

def vector_to_uv_vec(x, y, z):
    lon = np.arctan2(z, x)
    lat = np.arcsin(np.clip(y, -1.0, 1.0))
    u = (lon / np.pi + 1) / 2
    v = 0.5 - lat / np.pi
    return u, v


# ---------------------------------------------------------------------------
# Panorama seam healing
# ---------------------------------------------------------------------------

def heal_panorama_seam(pano_img, heal_width=100):
    arr = np.array(pano_img, dtype=np.float32)
    H, W, C = arr.shape
    hw = min(heal_width, W // 8)

    left_strip  = arr[:, :hw, :].copy()
    right_strip = arr[:, W - hw:, :].copy()

    alpha_out = np.linspace(1.0, 0.0, hw, dtype=np.float32)[np.newaxis, :, np.newaxis]
    alpha_in  = alpha_out[:, ::-1, :]

    arr[:, :hw, :]     = (1 - alpha_out) * left_strip  + alpha_out * right_strip[:, ::-1, :]
    arr[:, W - hw:, :] = (1 - alpha_in)  * right_strip + alpha_in  * left_strip[:, ::-1, :]

    return Image.fromarray(arr.astype(np.uint8))


# ---------------------------------------------------------------------------
# Interpolation kernels
# ---------------------------------------------------------------------------

def _lanczos_weight(t):
    t = np.abs(t).astype(np.float32)
    return np.where(t < 2, np.sinc(t) * np.sinc(t / 2), np.float32(0.0))


_LANCZOS2_OFFSETS = [-1, 0, 1, 2]


def _sample_panorama(pano_array, px_f, py_f, offsets, weight_fn):
    H, W, C = pano_array.shape
    result     = np.zeros((*px_f.shape, C), dtype=np.float32)
    weight_sum = np.zeros(px_f.shape,       dtype=np.float32)

    x0 = np.floor(px_f).astype(np.int32)
    y0 = np.floor(py_f).astype(np.int32)

    for di in offsets:
        yi = np.clip(y0 + di, 0, H - 1)
        wy = weight_fn(py_f - (y0 + di))
        for dj in offsets:
            xi = (x0 + dj) % W
            wx = weight_fn(px_f - (x0 + dj))
            w  = (wx * wy).astype(np.float32)
            result     += w[:, :, np.newaxis] * pano_array[yi, xi].astype(np.float32)
            weight_sum += w

    weight_sum = np.maximum(weight_sum, 1e-8)[:, :, np.newaxis]
    return np.clip(result / weight_sum, 0, 255)


# ---------------------------------------------------------------------------
# Cubemap face generation
# ---------------------------------------------------------------------------

def generate_face(pano_array, face_name):
    p_height, p_width, _ = pano_array.shape

    indices = np.linspace(0, FACE_SIZE - 1, FACE_SIZE)
    x_idx, y_idx = np.meshgrid(indices, indices)

    u_vals = 2 * (x_idx + 0.5) / FACE_SIZE - 1
    v_vals = 2 * (y_idx + 0.5) / FACE_SIZE - 1

    if face_name == 'right':
        vec = (np.ones_like(u_vals), -v_vals, -u_vals)
    elif face_name == 'back':
        vec = (-np.ones_like(u_vals), -v_vals, u_vals)
    elif face_name == 'top':
        vec = (u_vals, np.ones_like(u_vals), v_vals)
    elif face_name == 'bottom':
        vec = (u_vals, -np.ones_like(u_vals), -v_vals)
    elif face_name == 'front':
        vec = (u_vals, -v_vals, np.ones_like(u_vals))
    elif face_name == 'left':
        vec = (-u_vals, -v_vals, -np.ones_like(u_vals))
    else:
        raise ValueError(f"Unknown face name: {face_name!r}")

    mag = np.sqrt(vec[0] ** 2 + vec[1] ** 2 + vec[2] ** 2)
    dir_x, dir_y, dir_z = vec[0] / mag, vec[1] / mag, vec[2] / mag

    u, v = vector_to_uv_vec(dir_x, dir_y, dir_z)

    px_f = (u * p_width)  % p_width
    py_f = (v * p_height) % p_height

    result = _sample_panorama(pano_array, px_f, py_f, _LANCZOS2_OFFSETS, _lanczos_weight)

    return Image.fromarray(result.astype(np.uint8))


# ---------------------------------------------------------------------------
# Face edge blending — adaptive mirror, cosine fade, vectorized
# ---------------------------------------------------------------------------

def advanced_blend_from_middle(img, blend_width, mirror_left_onto_right=True, label='face'):
    width, _ = img.size
    mid = width // 2
    blend_width = min(blend_width, mid)

    img_array = np.array(img, dtype=np.float32)

    alpha_vec = ((1 + np.cos(np.linspace(0, np.pi, blend_width))) / 2
                 ).astype(np.float32)

    if mirror_left_onto_right:
        mirror = np.fliplr(img_array[:, :mid, :])
        alpha  = alpha_vec[np.newaxis, :, np.newaxis]
        orig   = img_array[:, mid:mid + blend_width, :]
        src    = mirror[:, :blend_width, :]
        img_array[:, mid:mid + blend_width, :] = alpha * src + (1 - alpha) * orig
    else:
        right_half = img_array[:, mid:, :]
        alpha  = alpha_vec[::-1][np.newaxis, :, np.newaxis]
        orig   = img_array[:, mid - blend_width:mid, :]
        src    = right_half[:, :blend_width, :][:, ::-1, :]
        img_array[:, mid - blend_width:mid, :] = alpha * src + (1 - alpha) * orig

    _log('BLEND', f'{label:<6}  {"LEFT→RIGHT" if mirror_left_onto_right else "RIGHT→LEFT"}')
    return Image.fromarray(np.clip(img_array, 0, 255).astype(np.uint8))


# ---------------------------------------------------------------------------
# Template assembly
# ---------------------------------------------------------------------------

def fix_template_seam_columns(template_img):
    """
    Replace the two center seam columns of 'up', 'bottom', and 'back' faces
    in the assembled 6144×4096 skybox template with their outer neighbours.
    """
    arr = np.array(template_img, dtype=np.uint8)
    H, W = arr.shape[:2]

    c0_r = FACE_SIZE // 2
    c0_l = c0_r - 1

    c1_r = FACE_SIZE + FACE_SIZE // 2
    c1_l = c1_r - 1

    if W < c1_r + 2:
        _log('SEAM', f'ERROR: template width {W} too small for seam fix (need ≥ {c1_r + 2})')
        return template_img

    arr[:FACE_SIZE, c0_l, :] = arr[:FACE_SIZE, c0_l - 1, :]
    arr[:FACE_SIZE, c0_r, :] = arr[:FACE_SIZE, c0_r + 1, :]
    arr[:, c1_l, :] = arr[:, c1_l - 1, :]
    arr[:, c1_r, :] = arr[:, c1_r + 1, :]
    _log('SEAM', f'Seam fix applied  template={W}×{H}  '
                 f'cols {c0_l},{c0_r} (bottom only)  cols {c1_l},{c1_r} (up+back)')
    return Image.fromarray(arr)


# PERF: accepts in-memory dict {layout_name: PIL.Image} — no disk reads.
# layout_name keys: 'down', 'up', 'east', 'left', 'back', 'south'
def combine_faces_into_template(face_images: dict) -> Image.Image:
    tile_size = FACE_SIZE
    template = Image.new("RGB", (tile_size * 3, tile_size * 2))

    layout = {
        'down':  (0,             0),
        'up':    (tile_size,     0),
        'east':  (tile_size * 2, 0),
        'left':  (0,             tile_size),
        'back':  (tile_size,     tile_size),
        'south': (tile_size * 2, tile_size),
    }

    for name, (x, y) in layout.items():
        img = face_images.get(name)
        if img is not None:
            template.paste(img.convert("RGB"), (x, y))

    return template  # PERF: return instead of saving — caller uses directly


# ---------------------------------------------------------------------------
# Properties file helper
# ---------------------------------------------------------------------------

def sky_layer_to_properties(layer):
    lines = []
    if layer.get("startFadeIn"):  lines.append(f"startFadeIn={layer['startFadeIn']}")
    if layer.get("endFadeIn"):    lines.append(f"endFadeIn={layer['endFadeIn']}")
    if layer.get("startFadeOut"): lines.append(f"startFadeOut={layer['startFadeOut']}")
    if layer.get("endFadeOut"):   lines.append(f"endFadeOut={layer['endFadeOut']}")
    lines.append(f"blend={layer['blend']}")
    if layer.get("rotate"):       lines.append("rotate=true")
    if layer.get("axis"):         lines.append(f"axis={layer['axis']}")
    lines.append(f"source=./{layer['source']}")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Pack structure generator — no template folder needed
# ---------------------------------------------------------------------------

def generate_pack_structure(final_output_dir, skybox_template, pano_path,
                             progress_callback=None, status_callback=None):
    """
    Build the complete Minecraft resource pack directory from scratch.
    PERF: encodes the skybox PNG exactly once, then uses shutil.copy2 for all
    remaining destinations (avoids 15 redundant PNG re-encodes).
    PERF: all file copies run in parallel via ThreadPoolExecutor.
    """
    def _progress(v):
        if progress_callback:
            progress_callback(v)

    def _status(msg):
        if status_callback:
            status_callback(msg)

    SKY_DIRS = [
        os.path.join(final_output_dir, "assets", "minecraft", "mcpatcher", "sky", "world0"),
        os.path.join(final_output_dir, "assets", "minecraft", "optifine",  "sky", "world0"),
    ]
    for d in SKY_DIRS:
        os.makedirs(d, exist_ok=True)

    # pack.mcmeta
    mcmeta = {
        "pack": {
            "pack_format": PACK_FORMAT,
            "description": f"\u00a70Generated via vuacy SkyMaker {VERSION}"
        }
    }
    with open(os.path.join(final_output_dir, "pack.mcmeta"), "w", encoding="utf-8") as f:
        json.dump(mcmeta, f, indent=2)

    # pack.png thumbnail
    icon = Image.open(pano_path).convert("RGB")
    icon.thumbnail((128, 128), Image.Resampling.LANCZOS)
    icon.save(os.path.join(final_output_dir, "pack.png"), "PNG")

    _progress(91)

    asset_filenames = [
        "skybox.png",
        "skybox2.png",
        "cloud1.png",
        "cloud2.png",
        "starfield01.png",
        "starfield02.png",
        "starfield03.png",
        "starfield.png",
    ]

    # PERF: encode the large template PNG exactly once.
    _status(t("encoding"))
    tmp_png = os.path.join(final_output_dir, "_skybox_tmp.png")
    skybox_template.save(tmp_png, "PNG")
    _log('PACK', f'Template encoded once → {os.path.basename(tmp_png)}')
    _progress(93)

    # Build list of all (src, dst) copy tasks.
    copy_tasks = []
    for sky_dir in SKY_DIRS:
        dir_label = 'optifine' if 'optifine' in sky_dir else 'mcpatcher'
        for filename in asset_filenames:
            dst = os.path.join(sky_dir, filename)
            copy_tasks.append((tmp_png, dst, dir_label, filename))

    # PERF: all copies run in parallel — I/O-bound, threads are ideal.
    _status(t("saving_assets"))
    with ThreadPoolExecutor(max_workers=8) as ex:
        futs = [ex.submit(shutil.copy2, src, dst)
                for src, dst, _label, _name in copy_tasks]
        for i, f in enumerate(futs):
            f.result()
            _progress(94 + int((i + 1) / len(futs) * 4))
            _, _, dir_label, filename = copy_tasks[i]
            _log('PACK', f'{dir_label}  {filename}')

    os.remove(tmp_png)

    # Write .properties files
    _status(t("writing_props"))
    _progress(99)
    for sky_dir in SKY_DIRS:
        for layer in SKY_LAYERS:
            content = sky_layer_to_properties(layer)
            with open(os.path.join(sky_dir, f"sky{layer['id']}.properties"),
                      "w", encoding="utf-8") as f:
                f.write(content)


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def generate_random_foldername(length=8):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))


def get_next_sky_number(all_skys_dir):
    if not os.path.exists(all_skys_dir):
        return 1
    existing = os.listdir(all_skys_dir)
    numbers = []
    for item in existing:
        if item.startswith("Sky"):
            base = os.path.splitext(item)[0]
            num_part = base[3:]
            if num_part.isdigit():
                numbers.append(int(num_part))
    return max(numbers) + 1 if numbers else 1


# ---------------------------------------------------------------------------
# Per-face processing (parallel worker)
# ---------------------------------------------------------------------------

NAME_MAP = {
    'right':  'east',
    'back':   'back',
    'top':    'up',
    'bottom': 'down',
    'front':  'south',
    'left':   'left',
}

# Maps combine_faces_into_template layout keys back to FACE_NAMES keys.
_LAYOUT_TO_FACE = {
    'down':  'bottom',
    'up':    'top',
    'east':  'right',
    'left':  'left',
    'back':  'back',
    'south': 'front',
}

BLEND_FACES = {'top', 'bottom', 'back'}


def process_single_face(face_name, pano_array, out_dir):
    """
    Generate one cubemap face, save it to out_dir, and return (face_name, img_array).
    """
    img = generate_face(pano_array, face_name)

    if face_name == 'top':
        img = img.rotate(90, expand=True)
    elif face_name == 'bottom':
        img = img.rotate(-90, expand=True)

    output_path = os.path.join(out_dir, f"{NAME_MAP[face_name]}.png")
    img.save(output_path)
    _log('FACE', f'Generated: {NAME_MAP[face_name]:<6}  (lanczos2)')
    return face_name, np.array(img)


# ---------------------------------------------------------------------------
# Main processing pipeline
# ---------------------------------------------------------------------------

def main_process(pano_path, blend_width, progress_callback,
                 status_callback=None):
    def _status(msg):
        if status_callback:
            status_callback(msg)

    pano_dir = os.path.dirname(os.path.abspath(pano_path))
    _log('INFO', f'Processing: {os.path.basename(pano_path)}  blend={blend_width}px  sampling=lanczos2')

    all_skys_dir = os.path.join(pano_dir, "allSkys")
    os.makedirs(all_skys_dir, exist_ok=True)

    sky_num = get_next_sky_number(all_skys_dir)
    sky_folder_name = f"Sky{sky_num}"
    final_output_dir = os.path.join(all_skys_dir, sky_folder_name)

    temp_out_dir = os.path.join(pano_dir, f"temp_faces_{generate_random_foldername(4)}")
    os.makedirs(temp_out_dir, exist_ok=True)

    # Load and heal panorama seam
    _status(t("loading_pano"))
    progress_callback(2)
    pano_img = Image.open(pano_path).convert('RGB')

    _status(t("healing_seam"))
    progress_callback(5)
    pano_img = heal_panorama_seam(pano_img, heal_width=pano_img.size[0] // 8)

    # Convert panorama to numpy array ONCE — shared read-only across all workers.
    pano_array = np.array(pano_img)

    completed_steps = 0
    face_arrays: dict[str, np.ndarray] = {}

    # Generate all 6 faces fully in parallel.
    max_workers = min(6, os.cpu_count() or 6)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(process_single_face, face, pano_array,
                            temp_out_dir)
            for face in FACE_NAMES
        ]
        for future in futures:
            face_name, img_arr = future.result()
            face_arrays[face_name] = img_arr
            completed_steps += 1
            _status(t("generated_face", face=NAME_MAP[face_name]))
            progress_callback(5 + int(completed_steps / len(FACE_NAMES) * 75))

    # Aggregate variance across ALL blend faces → one consistent blend direction.
    _status(t("analysing_seam"))
    total_var_left = total_var_right = 0.0
    for face_name in BLEND_FACES:
        arr = face_arrays[face_name].astype(np.float32)
        mid = arr.shape[1] // 2
        bw  = min(blend_width, mid)
        total_var_left  += float(np.var(arr[:, mid - bw:mid, :]))
        total_var_right += float(np.var(arr[:, mid:mid + bw, :]))

    mirror_left_onto_right = total_var_left <= total_var_right
    direction = "LEFT→RIGHT" if mirror_left_onto_right else "RIGHT→LEFT"
    _log('SEAM', f'Aggregate  var_left={total_var_left:>9.1f}  var_right={total_var_right:>9.1f}  → {direction}  (all blend faces)')
    progress_callback(83)

    # PERF: blend all 3 faces in parallel, return PIL Images directly (no disk save needed).
    _status(t("blending_seams"))

    def _blend_face_worker(face_name):
        face_img = Image.fromarray(face_arrays[face_name])
        blended  = advanced_blend_from_middle(face_img, blend_width,
                                              mirror_left_onto_right=mirror_left_onto_right,
                                              label=NAME_MAP[face_name])
        return face_name, blended

    blended_images: dict[str, Image.Image] = {}
    with ThreadPoolExecutor(max_workers=3) as ex:
        futs = [ex.submit(_blend_face_worker, fn) for fn in BLEND_FACES]
        for f in futs:
            face_name, blended = f.result()
            blended_images[face_name] = blended

    progress_callback(87)

    # PERF: build in-memory face_images dict for template assembly.
    # Blend faces use the freshly blended PIL Images; non-blend faces use their arrays.
    # No disk reads required at all.
    face_images_for_template = {
        layout_name: (blended_images[face_name]
                      if face_name in blended_images
                      else Image.fromarray(face_arrays[face_name]))
        for layout_name, face_name in _LAYOUT_TO_FACE.items()
    }

    # PERF: assemble template entirely in memory — no sky_result.png write/read.
    _status(t("assembling"))
    progress_callback(88)
    skybox_img = fix_template_seam_columns(combine_faces_into_template(face_images_for_template))
    progress_callback(90)
    _log('SEAM', 'Seam fix applied in memory.')

    # Build resource pack entirely from code.
    os.makedirs(final_output_dir, exist_ok=True)
    generate_pack_structure(
        final_output_dir, skybox_img, pano_path,
        progress_callback=progress_callback,
        status_callback=status_callback,
    )

    shutil.rmtree(temp_out_dir, ignore_errors=True)

    # Zip and clean up
    _status(t("creating_zip"))
    try:
        shutil.make_archive(final_output_dir, 'zip', final_output_dir)
        shutil.rmtree(final_output_dir, ignore_errors=True)
        _log('ZIP', f'{sky_folder_name}.zip created  →  {os.path.join(all_skys_dir, sky_folder_name)}.zip')
    except Exception as e:
        _log('ZIP', f'ERROR: {e}')

    progress_callback(100)
    _log('INFO', f'Done — {sky_folder_name}.zip')


# ---------------------------------------------------------------------------
# GUI
# ---------------------------------------------------------------------------

root = tk.Tk()
root.title("Skymaker by vuacy (" + VERSION + ")")
root.geometry("500x400")
root.resizable(False, False)


def safe_update_progress(value):
    try:
        root.after(0, lambda: progress.configure(value=value))
    except Exception:
        pass


def safe_update_status(text, color="blue"):
    try:
        root.after(0, lambda: status_label.config(text=text, fg=color))
    except Exception:
        pass


def safe_show_error(title, message):
    try:
        root.after(0, lambda: messagebox.showerror(title, message))
    except Exception:
        pass


def safe_reset_ui():
    try:
        root.after(0, lambda: [
            progress.pack_forget(),
            create_btn.config(state="normal"),
            select_btn.config(state="normal"),
        ])
    except Exception:
        pass


# --- Seam blend width ---
blend_label = tk.Label(root, text=t("blend_label"), font=("Arial", 10, "bold"))
blend_label.pack(pady=(12, 4))
blend_values = [str(i) for i in range(50, 1001, 50)]
blend_box = ttk.Combobox(root, values=blend_values, state="readonly", width=15)
blend_box.set("500")
blend_box.pack(pady=4)

# --- File selection ---
selected_file_label = tk.Label(root, text=t("no_images"), fg="gray",
                               wraplength=460, font=("Arial", 9))
selected_file_label.pack(pady=10)

status_label = tk.Label(root, text="", fg="blue", font=("Arial", 9))
status_label.pack(pady=4)

progress = ttk.Progressbar(root, length=380, mode='determinate')
progress.pack(pady=8)
progress.pack_forget()

selected_files = []


def select_images(files=None):
    global selected_files
    if not files:
        files = filedialog.askopenfilenames(
            title=t("select_title"),
            filetypes=[(t("image_files"), "*.jpg;*.jpeg;*.png"), (t("all_files"), "*.*")]
        )
    if files:
        selected_files = [os.path.abspath(f) for f in files]
        update_selected_label()
        create_btn.pack(pady=10)


def update_selected_label():
    if not selected_files:
        selected_file_label.config(text=t("no_images"), fg="gray")
        return
    count = len(selected_files)
    names = ", ".join(os.path.basename(f) for f in selected_files[:3])
    selected_file_label.config(
        text=t("selected_images", count=count, names=names) + ("..." if count > 3 else ""),
        fg="green"
    )


def run_creation():
    if not selected_files:
        return

    blend_width = int(blend_box.get())

    progress.pack()
    create_btn.config(state="disabled")
    select_btn.config(state="disabled")

    def task():
        total_files = len(selected_files)
        for i, file_path in enumerate(selected_files):
            prefix = f"[{i + 1}/{total_files}] "
            def _status(msg, _p=prefix):
                safe_update_status(_p + msg)
            safe_update_status(prefix + t("starting", name=os.path.basename(file_path)))
            try:
                main_process(file_path, blend_width,
                             safe_update_progress,
                             status_callback=_status)
            except Exception as e:
                safe_show_error(
                    t("error_title"),
                    t("error_failed", name=os.path.basename(file_path), error=str(e))
                )

        safe_update_status(t("all_finished"), color="green")
        safe_reset_ui()

    threading.Thread(target=task, daemon=True).start()


select_btn = tk.Button(
    root, text=t("select_btn"), command=select_images,
    bg="#4CAF50", fg="white", font=("Arial", 10, "bold"), padx=20, pady=5
)
select_btn.pack(pady=10)

create_btn = tk.Button(
    root, text=t("create_btn"), command=run_creation,
    bg="#2196F3", fg="white", font=("Arial", 10, "bold"), padx=20, pady=5
)


# --- Cambio de idioma / Language toggle ---
def toggle_language():
    global CURRENT_LANG
    CURRENT_LANG = 'es' if CURRENT_LANG == 'en' else 'en'
    lang_btn.config(text=t("lang_button"))
    blend_label.config(text=t("blend_label"))
    select_btn.config(text=t("select_btn"))
    create_btn.config(text=t("create_btn"))
    update_selected_label()
    # Solo limpiamos el estado si no hay un proceso en curso
    if str(select_btn.cget("state")) == "normal":
        status_label.config(text="")


lang_btn = tk.Button(root, text=t("lang_button"), command=toggle_language,
                     font=("Arial", 8), padx=6, pady=1)
lang_btn.place(relx=1.0, x=-8, y=8, anchor="ne")


# Drag & Drop support
def init_dnd():
    try:
        import windnd
        def on_drop(files):
            try:
                decoded = [f.decode('utf-8') if isinstance(f, bytes) else f
                           for f in files]
                root.after(10, lambda: select_images(decoded))
            except Exception:
                pass
        windnd.hook_dropfiles(root, func=on_drop)
        status_label.config(text=t("dnd_ready"), fg="gray")
    except ImportError:
        pass
    except Exception as e:
        print(f"DND Init failed: {e}")


root.after(100, init_dnd)
root.mainloop()
