from datetime import datetime
from io import BytesIO
from pathlib import Path
from textwrap import shorten
from urllib.parse import quote_plus

import PIL
import streamlit as st
from PIL import Image, ImageDraw, ImageFont


st.set_page_config(page_title="GPS Photo Tagger", layout="centered")


def load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    pil_font_dir = Path(PIL.__file__).resolve().parent / "fonts"
    windows_font_dir = Path("C:/Windows/Fonts")
    linux_font_dirs = (
        Path("/usr/share/fonts/truetype/dejavu"),
        Path("/usr/share/fonts/truetype/liberation2"),
        Path("/usr/share/fonts/truetype/liberation"),
        Path("/usr/share/fonts/opentype/noto"),
    )
    font_paths = (
        (
            windows_font_dir / "arialbd.ttf",
            pil_font_dir / "DejaVuSans-Bold.ttf",
            linux_font_dirs[0] / "DejaVuSans-Bold.ttf",
            linux_font_dirs[1] / "LiberationSans-Bold.ttf",
            linux_font_dirs[2] / "LiberationSans-Bold.ttf",
            linux_font_dirs[3] / "NotoSans-Bold.ttf",
            "arialbd.ttf",
            "DejaVuSans-Bold.ttf",
        )
        if bold
        else (
            windows_font_dir / "arial.ttf",
            pil_font_dir / "DejaVuSans.ttf",
            linux_font_dirs[0] / "DejaVuSans.ttf",
            linux_font_dirs[1] / "LiberationSans-Regular.ttf",
            linux_font_dirs[2] / "LiberationSans-Regular.ttf",
            linux_font_dirs[3] / "NotoSans-Regular.ttf",
            "arial.ttf",
            "DejaVuSans.ttf",
        )
    )
    for font_name in font_paths:
        try:
            return ImageFont.truetype(font_name, size)
        except (OSError, TypeError):
            continue
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def text_width(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont) -> int:
    box = draw.textbbox((0, 0), text, font=font)
    return box[2] - box[0]


def wrap_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.ImageFont,
    max_width: int,
    max_lines: int | None = None,
) -> list[str]:
    lines = []
    for original_line in text.splitlines():
        words = original_line.split()
        if not words:
            lines.append("")
            continue

        line = words[0]
        for word in words[1:]:
            candidate = f"{line} {word}"
            if text_width(draw, candidate, font) <= max_width:
                line = candidate
            else:
                lines.append(line)
                line = word
        lines.append(line)

    if max_lines and len(lines) > max_lines:
        kept = lines[:max_lines]
        kept[-1] = shorten(kept[-1], width=max(12, len(kept[-1]) - 3), placeholder="...")
        return kept
    return lines


def fit_font(draw: ImageDraw.ImageDraw, text: str, size: int, min_size: int, max_width: int, bold: bool = False) -> ImageFont.ImageFont:
    for font_size in range(size, min_size - 1, -2):
        font = load_font(font_size, bold=bold)
        if text_width(draw, text, font) <= max_width:
            return font
    return load_font(min_size, bold=bold)


def google_maps_link(latitude: str, longitude: str) -> str:
    query = quote_plus(f"{latitude},{longitude}")
    return f"https://www.google.com/maps/search/?api=1&query={query}"


def draw_pin(draw: ImageDraw.ImageDraw, cx: int, cy: int, size: int) -> None:
    radius = size // 3
    draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), fill=(255, 56, 70, 255))
    draw.polygon(
        [
            (cx - radius + 5, cy + radius // 3),
            (cx + radius - 5, cy + radius // 3),
            (cx, cy + size // 2),
        ],
        fill=(255, 56, 70, 255),
    )
    inner = max(4, radius // 3)
    draw.ellipse((cx - inner, cy - inner, cx + inner, cy + inner), fill=(70, 18, 26, 255))


def draw_map_tile(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    width: int,
    height: int,
    label_font: ImageFont.ImageFont,
    small_font: ImageFont.ImageFont,
) -> None:
    draw.rounded_rectangle((x, y, x + width, y + height), radius=8, fill=(12, 18, 28, 255))
    header_h = max(24, height // 5)
    draw.rounded_rectangle((x, y, x + width, y + header_h), radius=8, fill=(22, 181, 60, 255))
    draw.rectangle((x, y + header_h - 8, x + width, y + header_h), fill=(22, 181, 60, 255))

    check_in = "Check In"
    draw.text(
        (x + (width - text_width(draw, check_in, small_font)) // 2, y + 4),
        check_in,
        font=small_font,
        fill=(235, 255, 240, 255),
    )

    for i in range(4):
        line_y = y + header_h + 12 + (i * height // 7)
        draw.line((x + 12, line_y, x + width - 12, line_y + 10), fill=(25, 37, 56, 255), width=2)

    draw_pin(draw, x + width // 2, y + height // 2 + 5, max(32, height // 3))
    google = "Google"
    draw.text((x + 14, y + height - 32), google, font=label_font, fill=(255, 255, 255, 255))


def draw_gps_tag(
    image: Image.Image,
    location_title: str,
    address: str,
    latitude: str,
    longitude: str,
    site_id: str,
    timestamp_text: str,
    extra_fields: str,
    show_map_tile: bool,
    include_map_link: bool,
    map_url: str,
) -> Image.Image:
    output = image.convert("RGBA")
    overlay = Image.new("RGBA", output.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(overlay)

    base = max(18, output.width // 34)
    title_size = max(34, base + 20)
    title_font = load_font(title_size, bold=True)
    body_font = load_font(max(22, base + 2), bold=True)
    small_font = load_font(max(18, base - 2), bold=True)
    tiny_font = load_font(max(14, base - 7), bold=True)

    margin = max(18, output.width // 26)
    tag_x = margin
    tag_w = output.width - (margin * 2)
    tag_h = max(int(output.height * 0.23), 190)
    tag_y = output.height - tag_h - margin
    padding = max(14, output.width // 75)

    draw.rounded_rectangle(
        (tag_x, tag_y, tag_x + tag_w, tag_y + tag_h),
        radius=8,
        fill=(18, 18, 18, 190),
    )

    tile_w = int(tag_w * 0.25) if show_map_tile else 0
    tile_gap = padding if show_map_tile else 0
    if show_map_tile:
        draw_map_tile(
            draw,
            tag_x + padding,
            tag_y + padding,
            tile_w,
            tag_h - (padding * 2),
            label_font=body_font,
            small_font=small_font,
        )

    text_x = tag_x + padding + tile_w + tile_gap
    text_y = tag_y + padding + 2
    text_w = tag_w - (text_x - tag_x) - padding

    badge = "GPS Map Camera"
    badge_w = text_width(draw, badge, tiny_font) + 44
    badge_x = tag_x + tag_w - badge_w - padding
    badge_y = tag_y + tag_h - padding - 28
    draw.rounded_rectangle((badge_x, badge_y, badge_x + badge_w, badge_y + 28), radius=4, fill=(35, 35, 35, 220))
    draw_pin(draw, badge_x + 18, badge_y + 13, 18)
    draw.text((badge_x + 32, badge_y + 6), badge, font=tiny_font, fill=(255, 255, 255, 255))

    if location_title:
        title_width = max(120, text_w)
        title_font = fit_font(
            draw,
            location_title,
            size=title_size,
            min_size=max(body_font.size + 4, 28),
            max_width=title_width,
            bold=True,
        )
        for line in wrap_text(draw, location_title, title_font, title_width, max_lines=1):
            draw.text((text_x, text_y), line, font=title_font, fill=(255, 255, 255, 255))
            text_y += title_font.size + 8

    if address:
        for line in wrap_text(draw, address, body_font, text_w, max_lines=2):
            draw.text((text_x, text_y), line, font=body_font, fill=(255, 255, 255, 240))
            text_y += body_font.size + 2

    detail_parts = []
    if latitude:
        detail_parts.append(f"Lat {latitude}")
    if longitude:
        detail_parts.append(f"Long {longitude}")
    if site_id:
        detail_parts.append(f"Site ID {site_id}")
    if detail_parts:
        draw.text((text_x, text_y), "  ".join(detail_parts), font=body_font, fill=(255, 255, 255, 255))
        text_y += body_font.size + 3

    if timestamp_text:
        draw.text((text_x, text_y), timestamp_text, font=body_font, fill=(255, 255, 255, 255))
        text_y += body_font.size + 3

    if extra_fields:
        for line in wrap_text(draw, extra_fields, small_font, text_w, max_lines=2):
            draw.text((text_x, text_y), line, font=small_font, fill=(255, 255, 255, 235))
            text_y += small_font.size + 2

    if include_map_link and map_url:
        link_text = shorten(map_url, width=70, placeholder="...")
        draw.text((text_x, tag_y + tag_h - padding - small_font.size), link_text, font=small_font, fill=(180, 220, 255, 255))

    return Image.alpha_composite(output, overlay).convert("RGB")


st.title("GPS Photo Tagger")
st.caption("Create a GPS Map Camera style tag with location, site details, map pin, preview, and download.")

uploaded_file = st.file_uploader("Upload picture", type=["png", "jpg", "jpeg"])

with st.form("tag_form"):
    st.subheader("Location details")
    location_title = st.text_input("Main location title", placeholder="Hub, Balochistan, Pakistan")
    address = st.text_input("Address / area line", placeholder="Hub, Balochistan, Pakistan")

    col1, col2 = st.columns(2)
    with col1:
        latitude = st.text_input("Latitude", placeholder="25.229187")
    with col2:
        longitude = st.text_input("Longitude", placeholder="67.034302")

    site_id = st.text_input("Site ID", placeholder="33896")
    extra_fields = st.text_area(
        "Other fields",
        placeholder="Example:\nEngineer: Ali\nStatus: Completed",
        height=90,
    )

    st.subheader("Map link")
    map_link_mode = st.radio(
        "Google Maps link source",
        ["Generate from latitude/longitude", "Use manual link"],
        horizontal=True,
    )
    manual_map_url = st.text_input(
        "Manual Google Maps link",
        placeholder="Paste a Google Maps link here if the generated pin does not work",
        disabled=map_link_mode == "Generate from latitude/longitude",
    )

    st.subheader("Tag style")
    col3, col4 = st.columns(2)
    with col3:
        show_map_tile = st.checkbox("Show Google pin tile", value=True)
        include_map_link = st.checkbox("Print map link on image", value=False)
    with col4:
        use_current_time = st.checkbox("Use current date/time", value=True)
        picked_date = st.date_input("Date", value=datetime.now().date(), disabled=use_current_time)
        picked_time = st.time_input("Time", value=datetime.now().time().replace(microsecond=0), disabled=use_current_time)

    submitted = st.form_submit_button("Create preview", type="primary")

if uploaded_file and submitted:
    image = Image.open(uploaded_file)
    generated_url = google_maps_link(latitude, longitude) if latitude and longitude else ""
    map_url = manual_map_url.strip() if map_link_mode == "Use manual link" else generated_url

    if not location_title and not address and not latitude and not longitude and not site_id and not extra_fields:
        st.warning("Please enter at least one detail for the GPS tag.")
    elif map_link_mode == "Generate from latitude/longitude" and not generated_url:
        st.warning("Please enter both latitude and longitude, or choose the manual link option.")
    elif map_link_mode == "Use manual link" and not map_url:
        st.warning("Please paste a manual Google Maps link, or switch back to generated link.")
    else:
        if use_current_time:
            stamp_time = datetime.now()
        else:
            stamp_time = datetime.combine(picked_date, picked_time)
        timestamp_text = stamp_time.strftime("%d/%m/%Y %I:%M %p GMT +05:00")

        stamped = draw_gps_tag(
            image=image,
            location_title=location_title.strip(),
            address=address.strip(),
            latitude=latitude.strip(),
            longitude=longitude.strip(),
            site_id=site_id.strip(),
            timestamp_text=timestamp_text,
            extra_fields=extra_fields.strip(),
            show_map_tile=show_map_tile,
            include_map_link=include_map_link,
            map_url=map_url,
        )

        buffer = BytesIO()
        stamped.save(buffer, format="PNG")
        buffer.seek(0)

        st.subheader("Preview")
        st.image(stamped, use_container_width=True)
        if map_url:
            st.link_button("Open map pin", map_url)
        st.download_button(
            "Download tagged picture",
            data=buffer,
            file_name="gps_tagged_picture.png",
            mime="image/png",
        )
elif not uploaded_file:
    st.info("Upload a picture to start.")
