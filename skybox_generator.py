import os
import zipfile

import numpy as np
from PIL import Image, ImageFile


ImageFile.LOAD_TRUNCATED_IMAGES = True

OUTPUT_DIR = "generated"


def generate_skybox(image_path, size=512):
    os.makedirs(OUTPUT_DIR, exist_ok=True)


    panorama_img = Image.open(image_path).convert("RGB")

    original_path = os.path.join(OUTPUT_DIR, "panorama_original.png")
    panorama_img.save(original_path, compress_level=0)

    panorama = np.array(panorama_img)
    height, width, _ = panorama.shape


    face_directions = {
        "front": lambda x, y: (x, -y, 1),
        "back": lambda x, y: (-x, -y, -1),
        "left": lambda x, y: (-1, -y, x),
        "right": lambda x, y: (1, -y, -x),
        "top": lambda x, y: (x, 1, y),
        "bottom": lambda x, y: (x, -1, -y),
    }

    generated_faces = {}
    face_images = {}


    for face_name, direction in face_directions.items():

        face_pixels = np.zeros((size, size, 3), dtype=np.uint8)

        for y in range(size):
            ny = (2 * y / size) - 1

            for x in range(size):
                nx = (2 * x / size) - 1

                vx, vy, vz = direction(nx, ny)

                length = np.sqrt(vx * vx + vy * vy + vz * vz)
                vx /= length
                vy /= length
                vz /= length

                theta = np.arctan2(vz, vx)
                phi = np.arcsin(vy)

                u = (theta + np.pi) / (2 * np.pi)
                v = (np.pi / 2 - phi) / np.pi

                px = int(u * width) % width
                py = int(v * height) % height

                face_pixels[y, x] = panorama[py, px]

        output_path = os.path.join(OUTPUT_DIR, f"{face_name}.png")

        img_face = Image.fromarray(face_pixels)
        img_face.save(output_path, compress_level=0)

        generated_faces[face_name] = output_path
        face_images[face_name] = img_face.copy()


    atlas = Image.new("RGB", (size * 4, size * 3), (0, 0, 0))

    atlas_positions = {
        "top": (size, 0),
        "left": (0, size),
        "front": (size, size),
        "right": (size * 2, size),
        "back": (size * 3, size),
        "bottom": (size, size * 2),
    }

    for name, position in atlas_positions.items():
        atlas.paste(face_images[name], position)

    atlas_path = os.path.join(OUTPUT_DIR, "skybox_final.png")
    atlas.save(atlas_path, compress_level=0)


    mc_image = Image.new("RGB", (size * 3, size * 2))

    mc_image.paste(face_images["bottom"], (0, 0))
    mc_image.paste(face_images["top"], (size, 0))
    mc_image.paste(face_images["back"], (size * 2, 0))

    mc_image.paste(face_images["left"], (0, size))
    mc_image.paste(face_images["front"], (size, size))
    mc_image.paste(face_images["right"], (size * 2, size))

    minecraft_path = os.path.join(OUTPUT_DIR, "minecraft_skybox.png")
    mc_image.save(minecraft_path, compress_level=0)


    zip_path = os.path.join(OUTPUT_DIR, "skybox.zip")

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_STORED) as archive:

        for path in generated_faces.values():
            archive.write(path, os.path.basename(path))

        archive.write(original_path, "panorama_original.png")
        archive.write(atlas_path, "skybox_final.png")
        archive.write(minecraft_path, "minecraft_skybox.png")

    return zip_path