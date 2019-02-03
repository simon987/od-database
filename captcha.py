import random
import string

from PIL import Image, ImageDraw, ImageFont
from flask import request, session

import config
import common as oddb


def get_code():

    if "cap_remaining" in session and session["cap_remaining"] > 0:
        return """
        <span class='text-muted' style='margin: 10px'>You will not be asked to complete a captcha for the next {} pages</span>
        """.format(session["cap_remaining"])

    return """
    <div class='form-group' style='text-align: center'>
    <img src='./cap' alt='cap'  class='img-fluid' style='margin: 10px;'>
    <input class="form-control" name="cap" id="cap" placeholder="Verification captcha">
    </div>
    """


def get_path(word):
    return "captchas/{}.png".format(word)


def verify():
    if "cap_remaining" in session and session["cap_remaining"] > 0:
        session["cap_remaining"] -= 1
        return True

    attempt = request.form.get("cap") if "cap" in request.form else (
        request.args.get("cap") if "cap" in request.args else ""
    )

    if "cap" in session and session["cap"] in oddb.sessionStore and oddb.sessionStore[session["cap"]] == attempt:
        session["cap_remaining"] = config.CAPTCHA_EVERY
        return True
    return False


cfg = {
    "image": {
        "size": (200, 72),
        "supersampling": 2
    },
    "noise": {
        "min": 100,
        "max": 250
    },
    "colors": {
        "green": [(1, 51, 1), (34, 204, 34)],
        "yellow": [(67, 67, 1), (221, 221, 0)],
        "cyan": [(17, 51, 85), (85, 187, 254)],
        "magenta": [(51, 1, 51), (254, 0, 254)],
        "red": [(67, 1, 1), (254, 68, 68)],
        "orange": [(68, 51, 1), (255, 153, 0)]
    },
    "lines": {
        "back_thin": {"n": 3, "w": 5},
        "back_thick": {"n": 3, "w": 6},
        "back_positions": [
            {
                "ax": (0, 10),
                "ay": (0, 36),
                "bx": (150, 200),
                "by": (18, 50)
            },
            {
                "ax": (0, 10),
                "ay": (18, 50),
                "bx": (150, 200),
                "by": (0, 17)
            }
        ],
        "front_horizontal_thin": {"n": 2, "w": 3},
        "front_horizontal_thick": {"n": 2, "w": 4},
        "front_horizontal_positions": [
            {
                "ax": (0, 20),
                "ay": (0, 34),
                "bx": (150, 200),
                "by": (18, 50)
            },
            {
                "ax": (0, 20),
                "ay": (18, 72),
                "bx": (140, 200),
                "by": (0, 36)
            },
        ],
        "front_vertical": {"n": 2, "w": 4},
        "front_vertical_positions": {
            "outside": 5,
            "font_width": 13,
            "ay": (0, 16),
            "by": (54, 72)
        }
    },
    "text": {
        "font": {
            "path": "static/Hack-Regular.ttf",
            "size": 60,
            "outline": [1, 2]
        },
        "letters": {
            "3": {
                "count": 3,
                "x_min": 35,
                "x_max": 50,
                "y_min": -5,
                "y_max": 8
            },
            "4": {
                "count": 4,
                "x_min": 20,
                "x_max": 35,
                "y_min": -5,
                "y_max": 8
            },
            "5": {
                "count": 5,
                "x_min": 5,
                "x_max": 20,
                "y_min": -5,
                "y_max": 8
            }
        }
    }
}

size = cfg["image"]["size"]
c = cfg["image"]["supersampling"]

# Additional config
letter_count = "4"


def horizontal_lines(draw, c, line_par, line_pos, fill):
    for _ in range(line_par["n"]):
        pos = random.randrange(0, len(line_pos))
        ax = random.randint(*line_pos[pos]["ax"])
        ay = random.randint(*line_pos[pos]["ay"])
        bx = random.randint(*line_pos[pos]["bx"])
        by = random.randint(*line_pos[pos]["by"])
        draw.line([(ax*c, ay*c), (bx*c, by*c)], width=line_par["w"]*c, fill=fill)


def make_captcha():

    color_name, color = random.choice(list(cfg["colors"].items()))
    text = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(cfg["text"]["letters"][letter_count]["count"]))

    path = get_path(text)

    w = size[0]*c
    h = size[1]*c

    img = Image.new('RGB', (w, h))
    pixels = img.load()

    # noise
    for x in range(w):
        for y in range(h):
            rcol = random.randint(cfg["noise"]["min"], cfg["noise"]["max"])
            pixels[x, y] = (rcol, rcol, rcol)

    # background lines
    draw = ImageDraw.Draw(img)

    horizontal_lines(draw, c, cfg["lines"]["back_thin"], cfg["lines"]["back_positions"], color[0])
    horizontal_lines(draw, c, cfg["lines"]["back_thick"], cfg["lines"]["back_positions"], color[0])

    # text
    ctx = cfg["text"]["font"]
    font = ImageFont.truetype(ctx["path"], ctx["size"]*c)
    outline = random.choice(ctx["outline"])

    ctx = cfg["text"]["letters"][letter_count]
    x = random.randint(ctx["x_min"], ctx["x_max"])
    y = random.randint(ctx["y_min"], ctx["y_max"])
    draw.text((x*c-outline*c, y*c-outline*c), text, color[0], font=font)
    draw.text((x*c-outline*c, y*c), text, color[0], font=font)
    draw.text((x*c-outline*c, y*c+outline*c), text, color[0], font=font)
    draw.text((x*c, y*c-outline*c), text, color[0], font=font)
    draw.text((x*c, y*c+outline*c), text, color[0], font=font)
    draw.text((x*c+outline*c, y*c-outline*c), text, color[0], font=font)
    draw.text((x*c+outline*c, y*c), text, color[0], font=font)
    draw.text((x*c+outline*c, y*c+outline*c), text, color[0], font=font)
    draw.text((x*c, y*c), text, color[1], font=font)

    # foreground lines
    horizontal_lines(draw, c, cfg["lines"]["front_horizontal_thin"], cfg["lines"]["front_horizontal_positions"], color[1])
    horizontal_lines(draw, c, cfg["lines"]["front_horizontal_thick"], cfg["lines"]["front_horizontal_positions"], color[1])

    # vertical lines
    line_par = cfg["lines"]["front_vertical"]
    line_pos = cfg["lines"]["front_vertical_positions"]

    for _ in range(line_par["n"]):
        ax = random.randint(x-line_pos["outside"], x+line_pos["outside"] + cfg["text"]["letters"][letter_count]["count"]*line_pos["font_width"])
        bx = ax + random.randint(-line_pos["font_width"], line_pos["font_width"])
        ay = random.randint(*line_pos["ay"])
        by = random.randint(*line_pos["by"])
        draw.line([(ax*c, ay*c), (bx*c, by*c)], width=line_par["w"]*c, fill=color[1])

    img.thumbnail(cfg["image"]["size"], Image.ANTIALIAS)
    img.save(path, "png")

    return text


if __name__ == "__main__":
    make_captcha()
