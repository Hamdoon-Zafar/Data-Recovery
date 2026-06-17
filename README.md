# Lost Data Retrieval — Cybersecurity Capstone Task 1

**Internship Domain:** Cybersecurity  
**Technique:** Digital Forensics & File System Recovery  
**Tools Used:** TestDisk (CLI), Recuva (GUI), Python 3.8+

---

##  Project Overview

This project demonstrates the recovery of permanently deleted files from FAT32 and NTFS file systems. It simulates a real-world data loss scenario and provides both automated Python-based recovery logic and integration wrappers for professional forensic tools (TestDisk and Recuva).

### Core Concepts Demonstrated
- **FAT32 deletion mechanics:** How the `0xE5` directory entry marker works
- **NTFS MFT flagging:** How the Master File Table marks clusters as free without erasing data
- **File carving:** Detecting file magic bytes (signatures) at raw byte offsets
- **MD5 integrity verification:** Confirming recovered files match originals
- **Forensic chain of custody:** Audit logs and recovery reports

---

##  Repository Structure

```
task1_data_recovery/
│
├── simulate_and_recover.py     # Main script: seed, delete, recover, report
├── file_signature_scanner.py   # Raw disk image scanner using file magic bytes
├── recuva_helper.py            # Recuva CLI automation + Python fallback
├── requirements.txt            # Python dependencies
└── README.md                   # This file
```

---

## Setup & Requirements

### System Requirements
- Python 3.8 or higher
- Windows 10/11 (for Recuva) or Linux/macOS (for TestDisk + Python scripts)
- Administrator / root privileges for disk-level operations

### Install Python Dependencies

```bash
pip install -r requirements.txt
```

### Optional Tool Downloads

| Tool | URL | Platform |
|------|-----|----------|
| TestDisk 7.2 | https://www.cgsecurity.org/wiki/TestDisk_Download | Windows / Linux / macOS |
| Recuva 1.53 | https://www.ccleaner.com/recuva/download | Windows only |

---

##  Running the Scripts

### Script 1: Full Recovery Simulation

Simulates the complete lifecycle — file seeding, deletion, recovery, and audit report.

```bash
python simulate_and_recover.py
```

**Output:**
- `recovery_lab/source_files/` — Seeded test files (then deleted)
- `recovery_lab/deleted_files_backup/` — Pre-deletion backups for hash comparison
- `recovery_lab/recovered_files/` — Files recovered by the simulation
- `recovery_lab/reports/` — Full recovery audit report with MD5 verification

**For real TestDisk recovery (Windows):**
```bash
python simulate_and_recover.py --mode testdisk --drive \\.\PhysicalDrive1
```

---

### Script 2: File Signature Scanner

Scans a disk image or any binary file for embedded file magic bytes to locate deleted files.

```bash
# Demo mode (creates a synthetic disk image with embedded signatures):
python file_signature_scanner.py

# Scan a real disk image or file:
python file_signature_scanner.py path/to/disk.img
```

**Output:**
- Console report listing all detected file types, byte offsets, and sector numbers
- `recovery_lab/reports/signature_scan_<timestamp>.txt`
- `recovery_lab/carved/` — Sample carved file from first detected signature

---

### Script 3: Recuva Helper

Automates Recuva's command-line interface or runs a Python fallback on non-Windows systems.

```bash
python recuva_helper.py
```

On Windows with Recuva installed, you will be prompted for a drive letter and scan options.  
On Linux/macOS, the script automatically runs the Python fallback recovery.

---

## 🔬 How File Recovery Works

```
DELETION EVENT
      │
      ▼
┌─────────────────────────────────────────────┐
│  FAT32: Directory entry[0] = 0xE5           │
│  NTFS:  MFT record flagged "not in use"     │
│         $Bitmap updated to mark clusters free│
└─────────────────────────────────────────────┘
      │
      │  ← DATA STILL EXISTS ON DISK ←
      ▼
RECOVERY WINDOW
      │
      ├─ TestDisk  → Reads MFT / FAT → Reconstructs file entries
      ├─ Recuva    → Scans directory entries marked 0xE5
      └─ Carving   → Matches magic bytes at raw offsets (this script)
      │
      ▼
OVERWRITE (Recovery window CLOSES)
      │
      ▼
DATA PERMANENTLY LOST
```

---

##  Sample Recovery Report Output

```
================================================================================
         DIGITAL FORENSICS — DATA RECOVERY OPERATION REPORT
================================================================================
Timestamp       : 2024-01-15 14:32:01
Total Files Created : 8
Successfully Recovered  : 8
Recovery Rate           : 100.0%
Integrity Checks Passed : 8
Integrity Checks Failed : 0

  [ VERIFIED] financial_report.txt    | MD5 Match
  [ VERIFIED] project_proposal.txt    | MD5 Match
  [ VERIFIED] sample_photo_1.txt      | MD5 Match
  ...
================================================================================
```

---

##  Forensic Disclaimer

> These scripts are developed **strictly for educational and authorized forensic purposes**. Running data recovery tools on drives you do not own or have explicit permission to access may violate computer fraud laws. Always operate within a controlled lab environment.

---


