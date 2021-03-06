import re
from os import path

from PIL import Image


# bbox indices
LEFT = 0
TOP = 1
RIGHT = 2
BOTTOM = 3

class Verbatim(str):
    """text that should be inserted literally in lua"""

def to_lua_literal(item, indent=0):
    """Formats a Python object as a multi-line Lua literal"""
    if item is None:
        return "nil"
    elif type(item) is bool:
        return "true" if item else "false";
    elif type(item) is Verbatim:
        return item
    elif type(item) in [int, float]:
        return repr(item)
    elif type(item) is str:
        return f'"{item}"'

    elif type(item) is dict:
        lines = ["{"]
        indent += 4
        for key, value in item.items():
            if value is None:
                continue

            if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", key):
                key = f'["{key}"]'

            lines.append(f"{' '*indent}{key} = {to_lua_literal(value, indent)},")

        indent -= 4
        lines.append(f"{' '*indent}}}")
        return "\n".join(lines)

    elif type(item) is list:
        lines = ["{"]
        indent += 4
        for sub_item in item:
            lines.append(f"{' '*indent}{to_lua_literal(sub_item, indent)},")
        indent -= 4
        lines.append(f"{' '*indent}}}")
        return "\n".join(lines)

    else:
        raise TypeError(f"unhandled type {type(item).__name__}")

def crop_and_save(img, img_path):
    bbox = Image.eval(img, lambda c: c > 40).getbbox()
    print(f"Writing {img_path}")
    img.crop(bbox).save(img_path)
    return bbox

def process_picture(name, is_shadow=False):
    img = Image.open(path.join("render", f"{name}.png"))

    hr_bbox = crop_and_save(img, path.join("src", "graphics", "entity", f"{name}-hr.png"))
    bbox = crop_and_save(
        img.resize((512, 320), Image.LANCZOS),
        path.join("src", "graphics", "entity", f"{name}.png")
    )

    # Note that the enteties are rendered as a 10x16 tile region centred at (5, 5)
    x_shift = (bbox[RIGHT] + bbox[LEFT]) / 2 - 5*32
    y_shift = (bbox[BOTTOM] + bbox[TOP]) / 2 - 5*32

    hr_x_shift = (hr_bbox[RIGHT] + hr_bbox[LEFT]) / 2 - 5*64
    hr_y_shift = (hr_bbox[BOTTOM] + hr_bbox[TOP]) / 2 - 5*64

    return {
        "filename": f"__subspace_storage__/graphics/entity/{name}.png",
        "width": bbox[RIGHT] - bbox[LEFT],
        "height": bbox[BOTTOM] - bbox[TOP],
        "shift": Verbatim(f"util.by_pixel({x_shift}, {y_shift})"),
        "draw_as_shadow": True if is_shadow else None,
        "hr_version": {
            "filename": f"__subspace_storage__/graphics/entity/{name}-hr.png",
            "width": hr_bbox[RIGHT] - hr_bbox[LEFT],
            "height": hr_bbox[BOTTOM] - hr_bbox[TOP],
            "shift": Verbatim(f"util.by_pixel_hr({hr_x_shift}, {hr_y_shift})"),
            "scale": 0.5,
            "draw_as_shadow": True if is_shadow else None,
        },
    }


def process_interactor(kind, pictures):
    extractor_layer = process_picture(f"{kind}-extractor")
    injector_layer = process_picture(f"{kind}-injector")
    shadow_layer = process_picture(f"{kind}-shadow", True)

    pictures[f"subspace-{kind}-extractor"] = {
        "layers": [
            extractor_layer,
            shadow_layer,
        ],
    }

    pictures[f"subspace-{kind}-injector"] = {
        "layers": [
            injector_layer,
            shadow_layer,
        ],
    }

def square(bbox, center_x, center_y):
    """Calculate smallest centered square that contains bbox"""
    half_width = max(bbox[RIGHT] - center_x, center_x - bbox[LEFT])
    half_height = max(bbox[BOTTOM] - center_y, center_y - bbox[BOTTOM])
    return (
        center_x - half_width,
        center_y - half_height,
        center_x + half_width,
        center_y + half_height
    )

def process_icon(entity, icons):
    img = Image.open(path.join("render", f"{entity}.png"))
    bbox = square(img.getbbox(), 64*5, 64*5)

    img = img.crop(bbox)
    icon = Image.new("RGBA", (120, 64), (0, 0, 0, 0))
    icon.paste(img.resize((64, 64), Image.LANCZOS))
    icon.paste(img.resize((32, 32), Image.LANCZOS), (64, 0))
    icon.paste(img.resize((16, 16), Image.LANCZOS), (96, 0))
    icon.paste(img.resize((8, 8), Image.LANCZOS), (112, 0))

    icon_path = path.join("src", "graphics", "icons", f"{entity}.png")
    print(f"Writing {icon_path}")
    icon.save(icon_path)
    icons[f"subspace-{entity}"] = f"__subspace_storage__/graphics/icons/{entity}.png"

def write_lua_data(file_path, data):
    print(f"Writing {file_path}")
    with open(file_path, "w", newline="\n") as f:
        f.write("-- Auto generated by post.py, do not edit\n")
        f.write("return ")
        f.write(to_lua_literal(data))
        f.write("\n")

entity_pictures = {}
for kind in ["item", "fluid", "electricity"]:
    process_interactor(kind, entity_pictures)

write_lua_data(
    path.join("src", "prototypes", "entity_pictures.lua"),
    entity_pictures
)


entity_icons = {}
for kind in ["item", "fluid", "electricity"]:
    for direction in ["extractor", "injector"]:
        process_icon(f"{kind}-{direction}", entity_icons)

write_lua_data(
    path.join("src", "prototypes", "entity_icons.lua"),
    entity_icons
)
