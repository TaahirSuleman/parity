import base64


def png_to_data_url(png: bytes) -> str:
    return "data:image/png;base64," + base64.b64encode(png).decode()
