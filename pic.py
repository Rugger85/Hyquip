from io import BytesIO

import streamlit as st
from PIL import Image, ImageColor, ImageDraw, ImageFont


st.set_page_config(page_title="Photo Text Stamp", layout="centered")


def load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Use a common bundled font when available, otherwise fall back safely."""
    for font_name in ("arial.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(font_name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_width: int) -> list[str]:
    lines = []
    for original_line in text.splitlines():
        words = original_line.split()
        if not words:
            lines.append("")
            continue

        line = words[0]
        for word in words[1:]:
            candidate = f"{line} {word}"
            if draw.textbbox((0, 0), candidate, font=font)[2] <= max_width:
                line = candidate
            else:
                lines.append(line)
                line = word
        lines.append(line)
    return lines


def stamp_image(
    image: Image.Image,
    text: str,
    position: str,
    font_size: int,
    text_color: str,
    box_color: str,
    box_opacity: int,
    padding: int,
) -> Image.Image:
    output = image.convert("RGBA")
    overlay = Image.new("RGBA", output.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(overlay)
    font = load_font(font_size)

    max_text_width = int(output.width * 0.9) - (padding * 2)
    lines = wrap_text(draw, text, font, max_text_width)
    line_boxes = [draw.textbbox((0, 0), line or " ", font=font) for line in lines]
    line_height = max((box[3] - box[1] for box in line_boxes), default=font_size)
    text_width = max((box[2] - box[0] for box in line_boxes), default=0)
    text_height = (line_height * len(lines)) + (max(len(lines) - 1, 0) * 6)

    box_width = text_width + (padding * 2)
    box_height = text_height + (padding * 2)
    margin = max(16, padding)

    positions = {
        "Top left": (margin, margin),
        "Top right": (output.width - box_width - margin, margin),
        "Bottom left": (margin, output.height - box_height - margin),
        "Bottom right": (output.width - box_width - margin, output.height - box_height - margin),
    }
    x, y = positions[position]

    background_rgb = ImageColor.getrgb(box_color)
    background = Image.new("RGBA", (box_width, box_height), (*background_rgb, box_opacity))
    overlay.alpha_composite(background, (x, y))

    text_x = x + padding
    text_y = y + padding
    for line in lines:
        draw.text((text_x, text_y), line, fill=text_color, font=font)
        text_y += line_height + 6

    return Image.alpha_composite(output, overlay).convert("RGB")


st.title("Photo Text Stamp")
st.caption("Upload a picture, add site details, preview it, and download the stamped image.")

uploaded_file = st.file_uploader("Upload picture", type=["png", "jpg", "jpeg"])

with st.form("details_form"):
    site_id = st.text_input("Site ID")
    latitude = st.text_input("Latitude")
    longitude = st.text_input("Longitude")
    extra_fields = st.text_area(
        "Other fields",
        placeholder="Example:\nEngineer: Ali\nDate: 2026-06-05\nStatus: Completed",
        height=120,
    )

    col1, col2 = st.columns(2)
    with col1:
        position = st.selectbox("Text position", ["Bottom left", "Bottom right", "Top left", "Top right"])
        font_size = st.slider("Font size", 14, 72, 28)
    with col2:
        text_color = st.color_picker("Text color", "#FFFFFF")
        box_color = st.color_picker("Background color", "#000000")

    box_opacity = st.slider("Background opacity", 0, 255, 150)
    padding = st.slider("Text padding", 6, 40, 14)
    submitted = st.form_submit_button("Create preview", type="primary")

if uploaded_file and submitted:
    image = Image.open(uploaded_file)
    details = []
    if site_id:
        details.append(f"Site ID: {site_id}")
    if latitude:
        details.append(f"Latitude: {latitude}")
    if longitude:
        details.append(f"Longitude: {longitude}")
    if extra_fields:
        details.append(extra_fields.strip())

    if not details:
        st.warning("Please enter at least one field to place on the picture.")
    else:
        stamped = stamp_image(
            image=image,
            text="\n".join(details),
            position=position,
            font_size=font_size,
            text_color=text_color,
            box_color=box_color,
            box_opacity=box_opacity,
            padding=padding,
        )

        buffer = BytesIO()
        stamped.save(buffer, format="PNG")
        buffer.seek(0)

        st.subheader("Preview")
        st.image(stamped, use_container_width=True)
        st.download_button(
            "Download stamped picture",
            data=buffer,
            file_name="stamped_picture.png",
            mime="image/png",
        )
elif not uploaded_file:
    st.info("Upload a picture to start.")
