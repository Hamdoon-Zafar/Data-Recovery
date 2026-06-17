import os
import sys
import csv
import shutil
import logging
import subprocess
import platform
from pathlib import Path
from datetime import datetime

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


RECUVA_PATHS = [
    r"C:\Program Files\Recuva\Recuva64.exe",
    r"C:\Program Files (x86)\Recuva\Recuva.exe",
    r"C:\Program Files\Recuva\Recuva.exe",
]

RECOVERY_OUTPUT = Path("recovery_lab/recuva_recovered")
RECUVA_CSV_LOG  = Path("recovery_lab/reports/recuva_scan_results.csv")


def find_recuva() -> str | None:
    """Locate Recuva executable on the system."""
    for path in RECUVA_PATHS:
        if Path(path).exists():
            log.info(f"Recuva found at: {path}")
            return path

    # Try PATH
    result = shutil.which("Recuva64") or shutil.which("Recuva")
    if result:
        log.info(f"Recuva found on PATH: {result}")
        return result

    log.warning("Recuva not found. Download from: https://www.ccleaner.com/recuva/download")
    return None


def run_recuva_scan(drive: str, file_type: int = 0, deep_scan: bool = True,
                    target_folder: str = None) -> Path | None:
    """
    Run Recuva in command-line mode.
    
    Args:
        drive         : Drive letter to scan, e.g. 'R:\\'
        file_type     : File category (0=All, 1=Pictures, 2=Music, 3=Documents)
        deep_scan     : Enable Recuva deep scan mode
        target_folder : Specific folder to scan within the drive
    
    Returns:
        Path to the output CSV if successful, else None
    """
    recuva_exe = find_recuva()
    if not recuva_exe:
        return None

    if platform.system() != "Windows":
        log.error("Recuva is a Windows-only application.")
        return None

    RECUVA_CSV_LOG.parent.mkdir(parents=True, exist_ok=True)
    RECOVERY_OUTPUT.mkdir(parents=True, exist_ok=True)

    cmd = [
        recuva_exe,
        "/cmd",
        f"/filetype:{file_type}",
        f"/outputfile:{RECUVA_CSV_LOG.resolve()}",
        drive
    ]

    if deep_scan:
        cmd.append("/deep")

    if target_folder:
        cmd.append(f"/folder:{target_folder}")

    log.info(f"Launching Recuva: {' '.join(cmd)}")

    try:
        result = subprocess.run(cmd, timeout=300, capture_output=True, text=True)
        log.info(f"Recuva exit code: {result.returncode}")

        if result.stdout:
            log.info(f"STDOUT: {result.stdout}")
        if result.stderr:
            log.warning(f"STDERR: {result.stderr}")

        if RECUVA_CSV_LOG.exists():
            log.info(f"Scan results saved to: {RECUVA_CSV_LOG}")
            return RECUVA_CSV_LOG
        else:
            log.warning("Recuva completed but no CSV output found.")
            return None

    except subprocess.TimeoutExpired:
        log.error("Recuva scan timed out after 5 minutes.")
        return None
    except Exception as e:
        log.error(f"Recuva execution error: {e}")
        return None


def parse_recuva_csv(csv_path: Path) -> list:
    """
    Parse Recuva's CSV output file.
    
    Recuva CSV columns (typical):
    Filename, Path, Last Modified, Size, State, Comment
    
    State values:
    0 = Excellent (green)
    1 = Good
    2 = Poor (orange)
    3 = Unrecoverable (red)
    """
    if not csv_path or not csv_path.exists():
        log.error(f"CSV file not found: {csv_path}")
        return []

    STATE_MAP = {
        "0": "🟢 Excellent",
        "1": "🟡 Good",
        "2": "🟠 Poor",
        "3": "🔴 Unrecoverable",
    }

    results = []
    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            state_code = row.get("State", "3").strip()
            row["State_Label"] = STATE_MAP.get(state_code, "Unknown")
            results.append(row)
            log.info(
                f"  {row['State_Label']} | {row.get('Filename', 'N/A')} "
                f"| {row.get('Size', 'N/A')} bytes | {row.get('Last Modified', 'N/A')}"
            )

    log.info(f"Parsed {len(results)} records from Recuva CSV.")
    return results


def generate_recuva_report(results: list) -> str:
    """Generate a human-readable summary of Recuva scan results."""
    if not results:
        return "No results to report."

    state_counts = {}
    for row in results:
        label = row.get("State_Label", "Unknown")
        state_counts[label] = state_counts.get(label, 0) + 1

    total       = len(results)
    recoverable = sum(v for k, v in state_counts.items() if "Unrecoverable" not in k)

    report = f"""
================================================================================
         RECUVA SCAN REPORT
================================================================================
Scan Time         : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Total Files Found : {total}
Recoverable       : {recoverable} ({recoverable/total*100:.1f}%)
Unrecoverable     : {state_counts.get('🔴 Unrecoverable', 0)}

Recovery State Breakdown:
"""
    for state, count in sorted(state_counts.items()):
        report += f"  {state:<25} : {count} files\n"

    report += """
--------------------------------------------------------------------------------
FILES BY RECOVERY STATE:
"""
    for state_filter in ["🟢 Excellent", "🟡 Good", "🟠 Poor", "🔴 Unrecoverable"]:
        filtered = [r for r in results if r.get("State_Label") == state_filter]
        if filtered:
            report += f"\n{state_filter} ({len(filtered)} files):\n"
            for r in filtered[:10]:  # Show first 10 per category
                report += f"  - {r.get('Filename', 'N/A')} ({r.get('Size', '?')} bytes)\n"
            if len(filtered) > 10:
                report += f"  ... and {len(filtered) - 10} more\n"

    report += "\n" + "=" * 80
    return report


def python_fallback_recovery(source_backup: Path, output_dir: Path) -> dict:
    """
    Pure-Python fallback recovery when Recuva is not available.
    Copies files from backup directory to recovery output, simulating recovery.
    """
    log.info("Running Python fallback recovery (Recuva not available)...")
    output_dir.mkdir(parents=True, exist_ok=True)

    recovered = []
    failed    = []

    if not source_backup.exists():
        log.error(f"Backup directory not found: {source_backup}")
        return {"recovered": [], "failed": []}

    for fp in source_backup.rglob("*"):
        if fp.is_file():
            rel = fp.relative_to(source_backup)
            dest = output_dir / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            try:
                shutil.copy2(fp, dest)
                recovered.append(str(rel))
                log.info(f"  Recovered: {rel}")
            except Exception as e:
                failed.append(str(rel))
                log.error(f"  Failed: {rel} — {e}")

    log.info(f"Fallback recovery: {len(recovered)} recovered, {len(failed)} failed")
    return {"recovered": recovered, "failed": failed}


def main():
    print("\n" + "=" * 65)
    print("   RECUVA HELPER — Automated Recovery Interface")
    print("=" * 65 + "\n")

    # Detect OS
    if platform.system() != "Windows":
        log.warning("Recuva is Windows-only. Running Python fallback demonstration...")
        backup_dir = Path("recovery_lab/deleted_files_backup")
        results    = python_fallback_recovery(backup_dir, RECOVERY_OUTPUT)

        print(f"\n✅ Fallback recovery complete:")
        print(f"   Recovered : {len(results['recovered'])} files")
        print(f"   Failed    : {len(results['failed'])} files")
        print(f"   Output    : {RECOVERY_OUTPUT.resolve()}")
        return

    # Windows: attempt real Recuva scan
    drive = input("Enter drive letter to scan (e.g. R:\\): ").strip() or "R:\\"
    file_type_input = input("File type (0=All, 1=Pictures, 2=Music, 3=Documents) [0]: ").strip()
    file_type = int(file_type_input) if file_type_input.isdigit() else 0
    deep = input("Enable deep scan? (y/n) [y]: ").strip().lower() != "n"

    csv_path = run_recuva_scan(drive, file_type=file_type, deep_scan=deep)

    if csv_path:
        results = parse_recuva_csv(csv_path)
        report  = generate_recuva_report(results)
        print(report)

        report_path = Path(f"recovery_lab/reports/recuva_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
        report_path.write_text(report)
        log.info(f"Report saved: {report_path}")
    else:
        log.warning("Recuva scan did not produce output. Running Python fallback...")
        backup_dir = Path("recovery_lab/deleted_files_backup")
        python_fallback_recovery(backup_dir, RECOVERY_OUTPUT)


if __name__ == "__main__":
    main()
