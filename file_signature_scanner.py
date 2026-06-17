import os
import sys
import struct
import logging
from pathlib import Path
from datetime import datetime

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


# ── Known File Signatures (Magic Bytes) ──────────────────
# Format: { extension: (header_bytes, footer_bytes_or_None, description) }
FILE_SIGNATURES = {
    "jpg":  (b"\xFF\xD8\xFF",         b"\xFF\xD9",    "JPEG Image"),
    "png":  (b"\x89PNG\r\n\x1a\n",   b"\x00\x00\x00\x00IEND\xaeB`\x82", "PNG Image"),
    "gif":  (b"GIF87a",               b"\x00\x3B",    "GIF Image (87a)"),
    "gif89":(b"GIF89a",               b"\x00\x3B",    "GIF Image (89a)"),
    "bmp":  (b"BM",                   None,           "Bitmap Image"),
    "pdf":  (b"%PDF-",                b"%%EOF",       "PDF Document"),
    "zip":  (b"PK\x03\x04",          b"PK\x05\x06",  "ZIP Archive / DOCX / XLSX"),
    "docx": (b"PK\x03\x04",          None,           "Word Document (OOXML)"),
    "mp3":  (b"\xFF\xFB",            None,           "MP3 Audio"),
    "mp4":  (b"\x00\x00\x00\x18ftyp",None,           "MP4 Video"),
    "exe":  (b"MZ",                  None,           "Windows Executable"),
    "txt":  (None,                   None,           "Plain Text (no magic bytes)"),
    "7z":   (b"\x37\x7A\xBC\xAF\x27\x1C", None,    "7-Zip Archive"),
    "rar":  (b"Rar!\x1a\x07",        None,           "RAR Archive"),
}


def bytes_to_hex(data: bytes, limit: int = 16) -> str:
    """Convert bytes to readable hex string."""
    return " ".join(f"{b:02X}" for b in data[:limit])


def scan_file_for_signatures(file_path: Path, chunk_size: int = 1024 * 1024) -> list:
    """
    Scan a file/disk image for known magic byte signatures.
    
    Args:
        file_path  : Path to the disk image or raw file to scan
        chunk_size : Read buffer size in bytes (default: 1MB)
    
    Returns:
        List of dicts with detected file info: offset, extension, description
    """
    detections = []
    file_size = file_path.stat().st_size

    log.info(f"Scanning: {file_path} ({file_size / 1024:.1f} KB)")
    log.info(f"Chunk size: {chunk_size / 1024:.0f} KB")

    with open(file_path, "rb") as f:
        offset = 0
        buffer = b""

        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break

            # Overlap buffer with previous chunk to catch signatures at boundaries
            data = buffer[-32:] + chunk
            data_offset = offset - min(32, len(buffer))

            for ext, (header, footer, desc) in FILE_SIGNATURES.items():
                if header is None:
                    continue

                pos = 0
                while True:
                    idx = data.find(header, pos)
                    if idx == -1:
                        break

                    abs_offset = data_offset + idx
                    hex_preview = bytes_to_hex(data[idx:idx+16])

                    detections.append({
                        "offset_bytes": abs_offset,
                        "offset_hex":   f"0x{abs_offset:08X}",
                        "extension":    ext,
                        "description":  desc,
                        "header_hex":   hex_preview,
                        "sector":       abs_offset // 512,
                    })

                    log.info(
                        f"  [FOUND] {desc} (.{ext}) at offset {abs_offset} "
                        f"(sector {abs_offset // 512}) | Header: {hex_preview}"
                    )
                    pos = idx + 1

            buffer = chunk
            offset += len(chunk)

    log.info(f"Scan complete. {len(detections)} file signatures detected.")
    return detections


def extract_file_at_offset(disk_image: Path, offset: int, output_path: Path,
                            size_limit: int = 10 * 1024 * 1024):
    """
    Extract raw bytes starting at a given offset up to size_limit.
    Used to carve out a detected file from a disk image.
    
    Args:
        disk_image  : Path to the raw disk image
        offset      : Byte offset where the file begins
        output_path : Destination path for the carved file
        size_limit  : Maximum bytes to extract (default: 10MB)
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(disk_image, "rb") as f:
        f.seek(offset)
        data = f.read(size_limit)

    output_path.write_bytes(data)
    log.info(f"Carved {len(data)} bytes from offset {offset} → {output_path}")


def create_demo_disk_image(output_path: Path):
    """
    Create a small synthetic disk image containing embedded file signatures
    for demonstration purposes.
    """
    log.info(f"Creating demo disk image at: {output_path}")

    # Simulate a 64KB 'disk image' with embedded file signatures
    disk = bytearray(64 * 1024)

    # Write some 'random' data
    for i in range(len(disk)):
        disk[i] = i % 256

    # Embed a fake JPEG at offset 1024
    jpeg_header = b"\xFF\xD8\xFF\xE0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
    disk[1024:1024+len(jpeg_header)] = jpeg_header
    disk[8192:8194] = b"\xFF\xD9"  # JPEG footer

    # Embed a fake PNG at offset 16384
    png_header = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
    disk[16384:16384+len(png_header)] = png_header

    # Embed a fake PDF at offset 32768
    pdf_header = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>"
    disk[32768:32768+len(pdf_header)] = pdf_header
    pdf_footer = b"\n%%EOF"
    disk[40000:40000+len(pdf_footer)] = pdf_footer

    # Embed a fake ZIP/DOCX at offset 49152
    zip_header = b"PK\x03\x04\x14\x00\x00\x00\x08\x00"
    disk[49152:49152+len(zip_header)] = zip_header

    output_path.write_bytes(bytes(disk))
    log.info(f"Demo disk image created: {output_path.stat().st_size} bytes")
    log.info("Embedded signatures: JPEG (offset 1024), PNG (16384), PDF (32768), ZIP (49152)")


def generate_scan_report(detections: list, output_dir: Path):
    """Generate a text report of all detected file signatures."""
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = output_dir / f"signature_scan_{timestamp}.txt"

    lines = [
        "=" * 70,
        "   FILE SIGNATURE SCAN REPORT — Digital Forensics",
        "=" * 70,
        f"Timestamp : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Total Signatures Detected : {len(detections)}",
        "",
        f"{'Offset (Hex)':<14} {'Sector':<10} {'Extension':<10} {'Description':<28} {'Header (Hex)'}",
        "-" * 70,
    ]

    for d in detections:
        lines.append(
            f"{d['offset_hex']:<14} {d['sector']:<10} {d['extension']:<10} "
            f"{d['description']:<28} {d['header_hex']}"
        )

    lines += [
        "",
        "=" * 70,
        "RECOVERY RECOMMENDATION:",
        "Use the sector offsets above with TestDisk or PhotoRec to carve files.",
        "Command: photorec /d recovered/ disk_image.img",
        "=" * 70,
    ]

    report_path.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    log.info(f"Scan report saved: {report_path}")


def main():
    print("\n" + "=" * 65)
    print("   FILE SIGNATURE SCANNER — Forensic Disk Analysis Tool")
    print("=" * 65 + "\n")

    demo_image = Path("recovery_lab/demo_disk.img")
    demo_image.parent.mkdir(parents=True, exist_ok=True)

    # Create demo image if no real image provided
    if len(sys.argv) > 1:
        target = Path(sys.argv[1])
        if not target.exists():
            log.error(f"File not found: {target}")
            sys.exit(1)
        log.info(f"Scanning user-provided file: {target}")
    else:
        log.info("No disk image provided. Creating demo image for demonstration...")
        create_demo_disk_image(demo_image)
        target = demo_image

    # Run scan
    detections = scan_file_for_signatures(target)

    # Generate report
    generate_scan_report(detections, Path("recovery_lab/reports"))

    # Demo: carve first detected file
    if detections:
        first = detections[0]
        carved_out = Path(f"recovery_lab/carved/carved_{first['offset_hex']}.{first['extension']}")
        extract_file_at_offset(target, first["offset_bytes"], carved_out)
        print(f"\n✅ Demo carve complete: {carved_out}")

    print(f"\n📄 Scan complete. {len(detections)} signatures found.")
    print("   Use these offsets with TestDisk/PhotoRec for real disk recovery.\n")


if __name__ == "__main__":
    main()
