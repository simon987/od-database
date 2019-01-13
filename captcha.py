import os
import random

import numpy
import pylab
from PIL import Image, ImageDraw, ImageFont
import mpl_toolkits.mplot3d.axes3d as axes3d
import io
from wand.image import Image as WImage
from flask import request, session

import config
from common import logger

SIZE = (60, 20)
with open("words.txt") as f:
    WORDS = f.read().splitlines(keepends=False)


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

    if "cap" in session and session["cap"] == attempt:
        session["cap_remaining"] = config.CAPTCHA_EVERY
        return True
    return False


def make_captcha():
    word = random.choice(WORDS)
    path = get_path(word)

    logger.info("generating CAPTCHA: " + word)

    if os.path.exists(path):
        os.remove(path)

    image = Image.new('L', SIZE, 255)
    image_draw = ImageDraw.Draw(image)
    font = ImageFont.truetype("static/Hack-Regular.ttf", 12)

    image_draw.text((5, 3), word, font=font)

    x, y = numpy.meshgrid(range(SIZE[0]), range(SIZE[1]))
    z = 1 - numpy.asarray(image) / 255

    fig = pylab.figure()
    ax = axes3d.Axes3D(fig)
    ax.plot_wireframe(x, -y, z, rstride=1, cstride=1)
    ax.set_zlim((0, 20))
    ax.set_axis_off()
    pylab.close(fig)

    buf = io.BytesIO()
    fig.savefig(buf, dpi=150)
    buf.seek(0)
    image.close()

    with WImage(blob=buf.read()) as img:
        img.trim()
        img.save(filename=path)

    return word


if __name__ == "__main__":
    make_captcha()
