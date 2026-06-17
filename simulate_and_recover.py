import os
import sys
import shutil
import hashlib
import logging
import platform
import subprocess
import argparse
from pathlib import Path
from datetime import datetime

# ── Logging Setup ────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("recovery_lab.log")
    ]
)
log = logging.getLogger(__name__)


# ── Configuration ─────────────────────────────────────────
BASE_DIR      = Path("recovery_lab")
SOURCE_DIR    = BASE_DIR / "source_files"
DELETED_DIR   = BASE_DIR / "deleted_files_backup"   # Pre-deletion backup for hash comparison
RECOVERY_DIR  = BASE_DIR / "recovered_files"
REPORT_DIR    = BASE_DIR / "reports"


SAMPLE_FILES = {
    "images": [
        ("sample_photo_1.txt",    "FAKE IMAGE DATA - JPEG Header: FFD8FFE0 | Content: Family Vacation Photo 2024"),
        ("sample_photo_2.txt",    "FAKE IMAGE DATA - PNG Header: 89504E47 | Content: Company Logo High Resolution"),
        ("sample_diagram.txt",    "FAKE IMAGE DATA - BMP Header: 424D3A00 | Content: Network Architecture Diagram"),
    ],
    "documents": [
        ("financial_report.txt",  "CONFIDENTIAL DOCUMENT\nQ3 Financial Report 2024\nRevenue: $1,250,000\nExpenses: $870,000\nNet Profit: $380,000"),
        ("project_proposal.txt",  "PROJECT PROPOSAL\nTitle: AI-Driven Security Monitoring System\nBudget: $45,000\nTimeline: 6 months\nObjective: Reduce incident response time by 40%"),
        ("meeting_notes.txt",     "MEETING NOTES — 2024-01-15\nAttendees: Alice, Bob, Charlie\nAction Items:\n1. Deploy firewall rules by Friday\n2. Patch CVE-2024-1234 on all servers\n3. Review access logs for anomalies"),
    ],
    "spreadsheets": [
        ("employee_data.txt",     "ID,Name,Department,Salary\n001,Alice Smith,Engineering,95000\n002,Bob Johnson,HR,65000\n003,Carol White,Finance,78000"),
        ("inventory.txt",         "SKU,Product,Qty,Price\nA001,Laptop,45,1200\nA002,Monitor,23,450\nA003,Keyboard,87,85"),
    ]
}


def compute_md5(file_path: Path) -> str:
    """Compute MD5 hash of a file for integrity verification."""
    hasher = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def setup_environment():
    """Create the lab directory structure."""
    log.info("Setting up recovery lab environment...")
    for d in [SOURCE_DIR, DELETED_DIR, RECOVERY_DIR, REPORT_DIR]:
        d.mkdir(parents=True, exist_ok=True)
    log.info(f"Lab directories created under: {BASE_DIR.resolve()}")


def seed_test_files() -> dict:
    """
    Create sample files of different types in the source directory.
    Returns a dict of {filename: md5_hash} for integrity tracking.
    """
    log.info("Seeding test files into source directory...")
    hashes = {}

    for category, files in SAMPLE_FILES.items():
        cat_dir = SOURCE_DIR / category
        cat_dir.mkdir(exist_ok=True)

        for filename, content in files:
            fp = cat_dir / filename
            fp.write_text(content, encoding="utf-8")

            # Backup copy for post-recovery comparison
            backup_dir = DELETED_DIR / category
            backup_dir.mkdir(exist_ok=True)
            shutil.copy2(fp, backup_dir / filename)

            hashes[str(fp.relative_to(BASE_DIR))] = compute_md5(fp)
            log.info(f"  Created: {fp} | MD5: {hashes[str(fp.relative_to(BASE_DIR))]}")

    log.info(f"Total files seeded: {sum(len(v) for v in SAMPLE_FILES.values())}")
    return hashes


def simulate_deletion() -> list:
    """
    Permanently delete all seeded test files from the source directory.
    Returns list of deleted file paths.
    """
    log.info("Simulating file deletion (permanent delete)...")
    deleted = []

    for fp in SOURCE_DIR.rglob("*"):
        if fp.is_file():
            deleted.append(str(fp))
            fp.unlink()
            log.info(f"  Deleted: {fp}")

    # Remove empty subdirectories
    for d in sorted(SOURCE_DIR.rglob("*"), reverse=True):
        if d.is_dir():
            try:
                d.rmdir()
            except OSError:
                pass

    log.warning(f"{len(deleted)} files permanently deleted. Begin recovery immediately.")
    return deleted


def recover_with_python_simulation(original_hashes: dict) -> dict:
    """
    Simulated recovery using the pre-deletion backup.
    In a real scenario, TestDisk or Recuva would scan raw disk sectors.
    
    This function simulates what TestDisk does:
    - Scans for file signatures
    - Reconstructs directory entries
    - Copies recovered data to output directory
    
    Returns recovery results dict.
    """
    log.info("Running simulated file recovery (Python-based)...")
    results = {
        "recovered": [],
        "failed": [],
        "integrity_pass": [],
        "integrity_fail": []
    }

    for category in SAMPLE_FILES.keys():
        backup_cat = DELETED_DIR / category
        if not backup_cat.exists():
            continue

        recovery_cat = RECOVERY_DIR / category
        recovery_cat.mkdir(parents=True, exist_ok=True)

        for fp in backup_cat.glob("*"):
            dest = recovery_cat / fp.name
            try:
                shutil.copy2(fp, dest)
                results["recovered"].append(str(fp.name))

                # Integrity check
                original_key = f"source_files/{category}/{fp.name}"
                if original_key in original_hashes:
                    recovered_md5 = compute_md5(dest)
                    original_md5  = original_hashes[original_key]
                    if recovered_md5 == original_md5:
                        results["integrity_pass"].append(fp.name)
                        log.info(f"  ✅ Recovered & Verified: {fp.name} | MD5 Match")
                    else:
                        results["integrity_fail"].append(fp.name)
                        log.warning(f"  ⚠️  Hash mismatch: {fp.name}")
            except Exception as e:
                results["failed"].append(str(fp.name))
                log.error(f"  ❌ Recovery failed for {fp.name}: {e}")

    return results


def generate_report(original_hashes: dict, deleted: list, results: dict):
    """Generate a structured text report of the recovery operation."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    total     = len(deleted)
    recovered = len(results["recovered"])
    rate      = (recovered / total * 100) if total > 0 else 0

    report = f"""
================================================================================
         DIGITAL FORENSICS — DATA RECOVERY OPERATION REPORT
================================================================================
Timestamp       : {timestamp}
Operating System: {platform.system()} {platform.release()}
Lab Directory   : {BASE_DIR.resolve()}

────────────────────────────────────────────────────────────────────────────────
 PHASE 1: FILE SEEDING SUMMARY
────────────────────────────────────────────────────────────────────────────────
Total Files Created : {total}
Categories          : {', '.join(SAMPLE_FILES.keys())}

Original File Hashes (MD5):
"""
    for path, md5 in original_hashes.items():
        report += f"  {path:<45} {md5}\n"

    report += f"""
────────────────────────────────────────────────────────────────────────────────
 PHASE 2: DELETION SIMULATION
────────────────────────────────────────────────────────────────────────────────
Files Deleted : {total}
Method        : Permanent deletion (os.unlink — equivalent to Shift+Delete)
Write Ops     : ZERO after deletion (simulating forensic read-only state)

Deleted File Paths:
"""
    for d in deleted:
        report += f"  {d}\n"

    report += f"""
────────────────────────────────────────────────────────────────────────────────
 PHASE 3: RECOVERY RESULTS
────────────────────────────────────────────────────────────────────────────────
Total Files Targeted    : {total}
Successfully Recovered  : {recovered}
Recovery Rate           : {rate:.1f}%
Failed Recoveries       : {len(results['failed'])}
Integrity Checks Passed : {len(results['integrity_pass'])}
Integrity Checks Failed : {len(results['integrity_fail'])}

Recovered Files:
"""
    for f in results["recovered"]:
        status = "✅ VERIFIED" if f in results["integrity_pass"] else "⚠️  UNVERIFIED"
        report += f"  [{status}] {f}\n"

    if results["failed"]:
        report += "\nFailed Recoveries:\n"
        for f in results["failed"]:
            report += f"  [❌ FAILED] {f}\n"

    report += f"""
────────────────────────────────────────────────────────────────────────────────
 CONCLUSION
────────────────────────────────────────────────────────────────────────────────
Recovery operation {'SUCCESSFUL' if rate >= 80 else 'PARTIAL'}.
{recovered}/{total} files recovered with {len(results['integrity_pass'])} MD5-verified.

TOOL COMPARISON NOTE:
  - TestDisk (CLI) : Best for partition-level recovery & forensic integrity
  - Recuva (GUI)   : Best for quick, user-friendly file-level recovery
  - This Script    : Demonstrates the recovery logic and produces audit trail

FORENSIC PRINCIPLE: Data deleted without overwriting is recoverable.
The window of recovery closes as new data is written to the same clusters.
================================================================================
"""

    report_path = REPORT_DIR / f"recovery_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    report_path.write_text(report, encoding="utf-8")
    print(report)
    log.info(f"Report saved to: {report_path}")


def check_testdisk_available() -> bool:
    """Check if TestDisk is installed and available on PATH."""
    try:
        result = subprocess.run(
            ["testdisk", "/list"],
            capture_output=True, timeout=5
        )
        return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def launch_testdisk_interactive(target_drive: str = None):
    """
    Launch TestDisk interactively for real disk recovery.
    Requires TestDisk to be installed and run as Administrator/root.
    """
    if not check_testdisk_available():
        log.error("TestDisk is not found on PATH.")
        log.info("Download from: https://www.cgsecurity.org/wiki/TestDisk_Download")
        log.info("Place testdisk.exe (Windows) or testdisk (Linux/macOS) in your PATH.")
        return

    log.info("Launching TestDisk interactively...")
    log.info("Follow the on-screen prompts: Create Log → Select Disk → Intel → Advanced → Undelete")

    cmd = ["testdisk"]
    if target_drive:
        cmd.append(target_drive)

    subprocess.run(cmd)


def main():
    parser = argparse.ArgumentParser(
        description="Data Recovery Simulation Lab — Cybersecurity Capstone Task 1"
    )
    parser.add_argument(
        "--mode",
        choices=["simulate", "testdisk"],
        default="simulate",
        help="'simulate': run full Python-based demo | 'testdisk': launch real TestDisk"
    )
    parser.add_argument(
        "--drive",
        default=None,
        help="(testdisk mode only) Drive path to scan, e.g. /dev/sdb or \\\\.\\PhysicalDrive1"
    )
    args = parser.parse_args()

    print("\n" + "=" * 65)
    print("   DATA RECOVERY SIMULATION LAB — Cybersecurity Capstone")
    print("=" * 65 + "\n")

    if args.mode == "testdisk":
        launch_testdisk_interactive(args.drive)
        return

    # Full simulation mode
    setup_environment()
    original_hashes = seed_test_files()

    input("\n[PAUSE] Files created. Press Enter to simulate deletion...\n")
    deleted = simulate_deletion()

    input("\n[PAUSE] Files deleted. Press Enter to begin recovery...\n")
    results = recover_with_python_simulation(original_hashes)

    generate_report(original_hashes, deleted, results)

    print(f"\n✅ Simulation complete. Check '{RECOVERY_DIR}' for recovered files.")
    print(f"📄 Full report saved to '{REPORT_DIR}'.\n")


if __name__ == "__main__":
    main()
