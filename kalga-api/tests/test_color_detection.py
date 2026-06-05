"""Tests de la détection de couleur dominante."""
import io

from PIL import Image

from app.services.ai.color_detection import detect_color, ColorGuess


def _img_bytes(color, size=(120, 120)):
    """Crée une image PNG unie de la couleur RGB donnée."""
    img = Image.new("RGB", size, color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _img_object_on_white(obj_color, size=(200, 200), obj_box=(60, 60, 140, 140)):
    """Objet coloré centré sur fond blanc (simule un article photographié)."""
    img = Image.new("RGB", size, (255, 255, 255))
    for x in range(obj_box[0], obj_box[2]):
        for y in range(obj_box[1], obj_box[3]):
            img.putpixel((x, y), obj_color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_returns_color_guess():
    guess = detect_color(_img_bytes((200, 30, 30)))
    assert isinstance(guess, ColorGuess)


def test_solid_red_named_rouge():
    assert detect_color(_img_bytes((200, 30, 30))).name == "rouge"


def test_solid_blue_named_bleu():
    assert detect_color(_img_bytes((40, 80, 200))).name == "bleu"


def test_solid_green_named_vert():
    assert detect_color(_img_bytes((40, 160, 60))).name == "vert"


def test_pure_black_is_noir():
    assert detect_color(_img_bytes((10, 10, 10))).name == "noir"


def test_pure_white_is_blanc():
    assert detect_color(_img_bytes((245, 245, 245))).name == "blanc"


def test_gray_is_gris():
    assert detect_color(_img_bytes((128, 128, 128))).name == "gris"


def test_red_object_on_white_background_is_rouge_not_blanc():
    """Test clé : le fond blanc ne doit pas l'emporter sur l'objet rouge."""
    guess = detect_color(_img_object_on_white((200, 30, 30)))
    assert guess.name == "rouge"


def test_corrupt_bytes_graceful():
    guess = detect_color(b"not-an-image")
    assert isinstance(guess, ColorGuess)
    assert guess.confidence == 0.0


def test_confidence_high_for_clear_color():
    assert detect_color(_img_bytes((200, 30, 30))).confidence >= 0.6
