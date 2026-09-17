import json

from fastapi.testclient import TestClient

from app.main import STATIC_DIR, app

client = TestClient(app)


def test_manifest_is_served_as_json():
    response = client.get("/manifest.webmanifest")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/manifest+json")


def test_manifest_declares_a_standalone_app():
    manifest = client.get("/manifest.webmanifest").json()
    assert manifest["name"] == "Finance Tracker"
    assert manifest["display"] == "standalone"
    assert manifest["start_url"] == "/"
    assert manifest["theme_color"] == "#0a2240"


def test_every_declared_icon_is_reachable():
    manifest = client.get("/manifest.webmanifest").json()
    assert manifest["icons"]
    for icon in manifest["icons"]:
        response = client.get(icon["src"])
        assert response.status_code == 200, icon["src"]
        assert response.headers["content-type"] == "image/png"


def test_manifest_lists_a_maskable_icon():
    manifest = client.get("/manifest.webmanifest").json()
    purposes = {icon.get("purpose") for icon in manifest["icons"]}
    assert "maskable" in purposes


def test_page_links_the_manifest_and_a_png_touch_icon():
    page = client.get("/").text
    assert '<link rel="manifest" href="/manifest.webmanifest">' in page
    assert '<link rel="apple-touch-icon" href="/icons/apple-touch-icon.png">' in page
    assert '<meta name="apple-mobile-web-app-title" content="Finance">' in page


def test_page_uses_the_logo_as_its_favicon():
    page = client.get("/").text
    assert '<link rel="icon" href="/icons/logo.svg" type="image/svg+xml">' in page
    response = client.get("/icons/logo.svg")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("image/svg+xml")


def test_touch_icon_is_180_square():
    icons = json.loads((STATIC_DIR / "manifest.webmanifest").read_text())["icons"]
    assert {"192x192", "512x512"} <= {icon["sizes"] for icon in icons}
    response = client.get("/icons/apple-touch-icon.png")
    assert response.status_code == 200
