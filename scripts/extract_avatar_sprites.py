from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[1]
ASSETS_DIR = ROOT / "assets"
OUTPUT_DIR = ASSETS_DIR / "sprites"


@dataclass(frozen=True)
class Sprite:
    source: str
    box: tuple[int, int, int, int]
    output: str


def grid_sprites(
    source: str,
    bounds: tuple[int, int, int, int],
    rows: int,
    cols: int,
    output_dir: str,
    prefix: str,
    inset_fraction: float = 0.04,
) -> list[Sprite]:
    left, top, right, bottom = bounds
    width = (right - left) / cols
    height = (bottom - top) / rows
    sprites = []
    for row in range(rows):
        for col in range(cols):
            inset_x = 0 if inset_fraction == 0 else max(3, round(width * inset_fraction))
            inset_y = 0 if inset_fraction == 0 else max(3, round(height * inset_fraction))
            box = (
                round(left + col * width) + inset_x,
                round(top + row * height) + inset_y,
                round(left + (col + 1) * width) - inset_x,
                round(top + (row + 1) * height) - inset_y,
            )
            index = row * cols + col + 1
            sprites.append(Sprite(source, box, f"{output_dir}/{prefix}_{index:03d}.png"))
    return sprites


def build_sprite_map() -> list[Sprite]:
    sprites: list[Sprite] = []

    skin_names = [
        "pale", "light", "wheat", "tan", "olive", "brown", "dark", "deep",
        "green", "blue", "pink", "purple", "gray", "beige", "peach", "golden",
    ]
    avatar_x = [25, 211, 398, 584, 770, 956, 1143, 1329]
    for row, (top, bottom) in enumerate([(158, 500), (568, 890)]):
        for col, left in enumerate(avatar_x):
            name = skin_names[row * 8 + col]
            sprites.append(
                Sprite(
                    "Avatar-Skin-Tones.png",
                    (left + 13, top, left + 163, bottom),
                    f"avatars/skin_tones/{name}.png",
                )
            )

    eye_names = [
        "brown", "amber", "gold", "green", "lime", "teal",
        "cyan", "blue", "royal_blue", "navy", "purple", "violet",
        "pink", "magenta", "red", "orange", "silver", "black",
        "aqua", "ice_blue", "lavender", "turquoise", "rose", "mixed",
    ]
    eye_centers_x = [153, 399, 645, 890, 1136, 1381]
    eye_centers_y = [286, 474, 660, 846]
    for row, center_y in enumerate(eye_centers_y):
        for col, center_x in enumerate(eye_centers_x):
            name = eye_names[row * 6 + col]
            sprites.append(
                Sprite(
                    "Eyes.png",
                    (center_x - 72, center_y - 54, center_x + 72, center_y + 54),
                    f"eyes/{name}.png",
                )
            )

    sprites.extend(
        grid_sprites(
            "Hairs.png",
            (35, 35, 1505, 932),
            8,
            14,
            "hair",
            "hair",
            inset_fraction=0,
        )
    )
    sprites.extend(
        grid_sprites(
            "Items.png",
            (25, 65, 1515, 1000),
            6,
            14,
            "items",
            "item",
            inset_fraction=0,
        )
    )

    clothing_layouts = [
        (
            "Clothes-Modern-Feminine.png",
            "clothes/modern_feminine",
            [
                ("tops/common", (18, 101, 511, 508), 4, 5),
                ("tops/uncommon", (524, 101, 1011, 508), 4, 5),
                ("tops/rare_epic", (1023, 101, 1518, 508), 4, 5),
                ("bottoms/common", (18, 599, 511, 997), 4, 5),
                ("bottoms/uncommon", (524, 599, 1011, 997), 4, 5),
                ("bottoms/rare_epic", (1023, 599, 1518, 997), 4, 5),
            ],
        ),
        (
            "Clothes-Modern-Masculine.png",
            "clothes/modern_masculine",
            [
                ("tops/common", (13, 100, 504, 521), 5, 5),
                ("tops/uncommon", (516, 100, 1007, 521), 5, 5),
                ("tops/rare_epic", (1019, 100, 1520, 521), 5, 5),
                ("bottoms/common", (13, 608, 504, 964), 4, 5),
                ("bottoms/uncommon", (516, 608, 1007, 964), 4, 5),
                ("bottoms/rare_epic", (1019, 608, 1520, 964), 4, 5),
            ],
        ),
        (
            "Clothes-RPG-Feminine.png",
            "clothes/rpg_feminine",
            [
                ("tops/common", (13, 102, 511, 516), 4, 5),
                ("tops/uncommon", (523, 102, 1002, 516), 4, 5),
                ("tops/rare_epic", (1013, 102, 1521, 516), 4, 5),
                ("bottoms/common", (13, 609, 511, 1007), 4, 5),
                ("bottoms/uncommon", (523, 609, 1002, 1007), 4, 5),
                ("bottoms/rare_epic", (1013, 609, 1521, 1007), 4, 5),
            ],
        ),
        (
            "Clothes-RPG-Neutral.png",
            "clothes/rpg_neutral",
            [
                ("tops/common", (188, 122, 592, 533), 3, 5),
                ("tops/uncommon", (604, 122, 1043, 533), 3, 5),
                ("tops/rare_epic", (1054, 122, 1521, 533), 3, 5),
                ("bottoms/common", (188, 630, 592, 953), 3, 5),
                ("bottoms/uncommon", (604, 630, 1043, 953), 3, 5),
                ("bottoms/rare_epic", (1054, 630, 1521, 953), 3, 5),
            ],
        ),
    ]
    for source, collection, sections in clothing_layouts:
        for section, bounds, rows, cols in sections:
            prefix = section.replace("/", "_")
            sprites.extend(
                grid_sprites(
                    source,
                    bounds,
                    rows,
                    cols,
                    f"{collection}/{section}",
                    prefix,
                    inset_fraction=0.08,
                )
            )

    return sprites


def estimate_background(rgb: np.ndarray) -> np.ndarray:
    height, width, _ = rgb.shape
    patch = max(3, min(height, width) // 12)
    corners = np.array(
        [
            np.median(rgb[:patch, :patch], axis=(0, 1)),
            np.median(rgb[:patch, -patch:], axis=(0, 1)),
            np.median(rgb[-patch:, :patch], axis=(0, 1)),
            np.median(rgb[-patch:, -patch:], axis=(0, 1)),
        ],
        dtype=np.float32,
    )
    y = np.linspace(0, 1, height, dtype=np.float32)[:, None, None]
    x = np.linspace(0, 1, width, dtype=np.float32)[None, :, None]
    top = corners[0] * (1 - x) + corners[1] * x
    bottom = corners[2] * (1 - x) + corners[3] * x
    return top * (1 - y) + bottom * y


def transparent_crop(image: Image.Image) -> Image.Image | None:
    rgb = np.asarray(image.convert("RGB"), dtype=np.float32)
    background = estimate_background(rgb)
    distance = np.linalg.norm(rgb - background, axis=2)

    raw = distance > 19
    joined = ndimage.binary_dilation(raw, iterations=2)
    joined = ndimage.binary_closing(joined, iterations=2)
    labels, count = ndimage.label(joined)
    if count == 0:
        return None

    height, width = raw.shape
    center_y, center_x = height / 2, width / 2
    keep = np.zeros_like(raw)
    for label_id in range(1, count + 1):
        ys, xs = np.where(labels == label_id)
        if len(xs) < 18:
            continue
        component_width = int(xs.max() - xs.min() + 1)
        component_height = int(ys.max() - ys.min() + 1)
        if component_width <= max(5, round(width * 0.07)) and component_height >= height * 0.35:
            continue
        if component_height <= max(5, round(height * 0.07)) and component_width >= width * 0.35:
            continue
        component_center_x = xs.mean()
        component_center_y = ys.mean()
        central = (
            width * 0.08 <= component_center_x <= width * 0.92
            and height * 0.06 <= component_center_y <= height * 0.94
        )
        distance_to_center = ((component_center_x - center_x) / width) ** 2 + (
            (component_center_y - center_y) / height
        ) ** 2
        if central and distance_to_center < 0.42:
            keep |= labels == label_id

    if not keep.any():
        return None

    keep = ndimage.binary_dilation(keep, iterations=1)
    alpha = np.where(keep & (distance > 9), 255, 0).astype(np.uint8)

    ys, xs = np.where(alpha > 0)
    if not len(xs):
        return None
    padding = 3
    left = max(0, int(xs.min()) - padding)
    top = max(0, int(ys.min()) - padding)
    right = min(width, int(xs.max()) + padding + 1)
    bottom = min(height, int(ys.max()) + padding + 1)

    rgba = np.dstack([rgb.astype(np.uint8), alpha])
    return Image.fromarray(rgba, "RGBA").crop((left, top, right, bottom))


def extract_irregular_grid(
    source_image: Image.Image,
    sprites: list[Sprite],
) -> dict[str, Image.Image]:
    """Segment a full grid and assign every foreground component by center."""
    left = min(sprite.box[0] for sprite in sprites)
    top = min(sprite.box[1] for sprite in sprites)
    right = max(sprite.box[2] for sprite in sprites)
    bottom = max(sprite.box[3] for sprite in sprites)
    sheet = source_image.crop((left, top, right, bottom)).convert("RGB")
    rgb = np.asarray(sheet, dtype=np.float32)

    flat = rgb.reshape(-1, 3)
    background_candidates = (
        (flat[:, 2] > flat[:, 0] + 3)
        & (flat[:, 2] > flat[:, 1] + 2)
        & (flat.max(axis=1) < 80)
    )
    background_color = np.median(flat[background_candidates], axis=0)
    distance = np.linalg.norm(rgb - background_color, axis=2)

    foreground = distance > 9
    labels, count = ndimage.label(foreground)

    centers = np.array(
        [
            (
                ((sprite.box[0] + sprite.box[2]) / 2) - left,
                ((sprite.box[1] + sprite.box[3]) / 2) - top,
            )
            for sprite in sprites
        ],
        dtype=np.float32,
    )
    assigned: list[list[int]] = [[] for _ in sprites]

    for label_id in range(1, count + 1):
        ys, xs = np.where(labels == label_id)
        if len(xs) < 8:
            continue
        centroid = np.array([xs.mean(), ys.mean()], dtype=np.float32)
        nearest = int(np.argmin(np.sum((centers - centroid) ** 2, axis=1)))
        assigned[nearest].append(label_id)

    outputs: dict[str, Image.Image] = {}
    rgba = np.dstack([rgb.astype(np.uint8), np.zeros(distance.shape, dtype=np.uint8)])
    for index, sprite in enumerate(sprites):
        if not assigned[index]:
            continue
        component_mask = np.isin(labels, assigned[index])
        alpha = np.where(component_mask & (distance > 5), 255, 0).astype(np.uint8)
        ys, xs = np.where(alpha > 0)
        if not len(xs):
            continue

        padding = 3
        crop_left = max(0, int(xs.min()) - padding)
        crop_top = max(0, int(ys.min()) - padding)
        crop_right = min(rgb.shape[1], int(xs.max()) + padding + 1)
        crop_bottom = min(rgb.shape[0], int(ys.max()) + padding + 1)
        sprite_rgba = rgba.copy()
        sprite_rgba[:, :, 3] = alpha
        outputs[sprite.output] = Image.fromarray(sprite_rgba, "RGBA").crop(
            (crop_left, crop_top, crop_right, crop_bottom)
        )
    return outputs


def create_qa_preview(paths: list[Path]) -> None:
    tile_size = 180
    columns = 5
    rows = (len(paths) + columns - 1) // columns
    preview = Image.new("RGB", (columns * tile_size, rows * tile_size), "#f1f1f1")

    checker = Image.new("RGB", (tile_size, tile_size), "white")
    pixels = checker.load()
    square = 18
    for y in range(tile_size):
        for x in range(tile_size):
            pixels[x, y] = (225, 225, 225) if (x // square + y // square) % 2 else (250, 250, 250)

    for index, path in enumerate(paths):
        sprite = Image.open(path).convert("RGBA")
        sprite.thumbnail((tile_size - 24, tile_size - 24), Image.Resampling.NEAREST)
        tile = checker.copy()
        x = (tile_size - sprite.width) // 2
        y = (tile_size - sprite.height) // 2
        tile.paste(sprite, (x, y), sprite)
        preview.paste(tile, ((index % columns) * tile_size, (index // columns) * tile_size))

    preview.save(OUTPUT_DIR / "_qa_preview.png", optimize=True)


def create_category_preview(folder: Path, output_name: str, columns: int) -> None:
    paths = sorted(folder.glob("*.png"))
    tile_size = 112
    rows = (len(paths) + columns - 1) // columns
    preview = Image.new("RGB", (columns * tile_size, rows * tile_size), "white")

    for index, path in enumerate(paths):
        sprite = Image.open(path).convert("RGBA")
        sprite.thumbnail((tile_size - 10, tile_size - 10), Image.Resampling.NEAREST)
        tile = Image.new("RGB", (tile_size, tile_size), "white")
        pixels = tile.load()
        square = 14
        for y in range(tile_size):
            for x in range(tile_size):
                pixels[x, y] = (226, 226, 226) if (x // square + y // square) % 2 else (250, 250, 250)
        x = (tile_size - sprite.width) // 2
        y = (tile_size - sprite.height) // 2
        tile.paste(sprite, (x, y), sprite)
        preview.paste(tile, ((index % columns) * tile_size, (index // columns) * tile_size))

    preview.save(OUTPUT_DIR / output_name, optimize=True)


def main() -> None:
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    OUTPUT_DIR.mkdir(parents=True)

    source_images: dict[str, Image.Image] = {}
    manifest: list[dict] = []
    failed: list[str] = []
    sprite_map = build_sprite_map()
    irregular_outputs: dict[str, Image.Image] = {}

    for source_name in ("Hairs.png", "Items.png"):
        source_sprites = [sprite for sprite in sprite_map if sprite.source == source_name]
        source_image = Image.open(ASSETS_DIR / source_name).convert("RGB")
        source_images[source_name] = source_image
        irregular_outputs.update(extract_irregular_grid(source_image, source_sprites))

    for sprite in sprite_map:
        if sprite.source not in source_images:
            source_images[sprite.source] = Image.open(ASSETS_DIR / sprite.source).convert("RGB")
        if sprite.source in {"Hairs.png", "Items.png"}:
            extracted = irregular_outputs.get(sprite.output)
        else:
            extracted = transparent_crop(source_images[sprite.source].crop(sprite.box))
        if extracted is None:
            failed.append(sprite.output)
            continue

        destination = OUTPUT_DIR / sprite.output
        destination.parent.mkdir(parents=True, exist_ok=True)
        extracted.save(destination, optimize=True)
        manifest.append(
            {
                "path": destination.relative_to(ASSETS_DIR).as_posix(),
                "source": sprite.source,
                "source_box": sprite.box,
                "width": extracted.width,
                "height": extracted.height,
            }
        )

    (OUTPUT_DIR / "manifest.json").write_text(
        json.dumps({"sprites": manifest, "failed": failed}, indent=2),
        encoding="utf-8",
    )
    preview_paths = [
        OUTPUT_DIR / "avatars/skin_tones/pale.png",
        OUTPUT_DIR / "avatars/skin_tones/deep.png",
        OUTPUT_DIR / "eyes/black.png",
        OUTPUT_DIR / "hair/hair_001.png",
        OUTPUT_DIR / "hair/hair_106.png",
        OUTPUT_DIR / "clothes/modern_feminine/tops/common/tops_common_001.png",
        OUTPUT_DIR / "clothes/modern_masculine/tops/rare_epic/tops_rare_epic_001.png",
        OUTPUT_DIR / "clothes/rpg_feminine/bottoms/rare_epic/bottoms_rare_epic_014.png",
        OUTPUT_DIR / "clothes/rpg_neutral/tops/uncommon/tops_uncommon_006.png",
        OUTPUT_DIR / "items/item_001.png",
        OUTPUT_DIR / "items/item_084.png",
    ]
    create_qa_preview(preview_paths)
    create_category_preview(OUTPUT_DIR / "hair", "_qa_hair.png", columns=14)
    create_category_preview(OUTPUT_DIR / "items", "_qa_items.png", columns=14)
    print(f"Extracted {len(manifest)} sprites into {OUTPUT_DIR}")
    if failed:
        print(f"Failed to extract {len(failed)} sprites; see manifest.json")


if __name__ == "__main__":
    main()
