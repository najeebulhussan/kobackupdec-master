# Changelog

All notable changes to this project will be documented in this file.

## [GUI_v1.2] — 2026-05-08

### Added
- **Standalone Executable Compilation:** Added `build.py` script to seamlessly package the application into a `.exe` using PyInstaller.
- **Custom Application Icon:** Generated and integrated a professional `.ico` icon into the executable bundle.

---

## [GUI_v1.1] — 2026-05-08

### Added
- **Drag-and-Drop:** Added `tkinterdnd2` support allowing users to drag backup folders directly into the application.
- **Settings Persistence:** Created `config.json` integration to save and automatically load user preferences and selected directories across sessions.
- **Log Exporting:** Added an "Export Log" button to save the current terminal output to a text file for auditing.
- **Output Folder Quick Access:** Added an "Open Output" button that becomes clickable after a successful decryption to instantly view the extracted files.

---

## [GUI_v1.0] — 2026-05-08

### Added
- **Full GUI application** (`kobackupdec_gui.py`) with modern dark theme
- **Password verification** — validates password against backup before decryption starts
- **Selective folder decryption** — scan backup and choose specific folders (pictures, video, audios, etc.)
- **Pause / Resume** button to temporarily halt decryption
- **Stop** button to cancel decryption mid-process
- **Real-time log output** with color-coded levels (INFO=green, WARNING=yellow, ERROR=red, DEBUG=gray)
- **Responsive layout** — resizes from 600×500 to fullscreen with auto-reflowing folder checkboxes
- **Progress status** — shows current phase and folder being processed
- **Browse dialogs** for backup and destination folders
- **Show/hide password** toggle
- **Select All / Deselect All** for folder selection
- **Auto-scan** — folder list auto-populates when backup path is set

### Unchanged
- Core decryption engine (`kobackupdec.py`) — no modifications to original code
- CLI interface — fully preserved and backward-compatible

---

## [20200705] — 2020-07-05

### Fixed
- `decrypt_large_package` now correctly reads input in chunks

## [20200611] — 2020-06-11

### Added
- `--expandtar` option to control automatic TAR expansion
- `--writable` option to skip setting read-only permissions on decrypted files
- Large TAR files are managed in chunks but not expanded

## [20200607] — 2020-06-07

### Fixed
- Merged empty `CheckMsg` handling
- Updated `folder_to_media_type` mapping (by @realSnoopy)

## [20200406] — 2020-04-06

### Fixed
- Merged file and folder permissions fix (by @lp4n6)

## [20200405] — 2020-04-05

### Added
- Python minor version check with informative note (thanks @lp4n6)

## [2020test] — 2020

### Changed
- Complete rewrite to handle v9 and v10 KoBackup structures

## [20200107] — 2020-01-07

### Fixed
- Merged pull by @lp4n6, fixed current version handling

## [20191113] — 2019-11-13

### Fixed
- Double folder creation error

## [20190729] — 2019-07-29

### Added
- First public release
- Huawei KoBackup / HiSuite backup decryption
- Automatic output folder restructuring to mimic Android filesystem
- Support for APK, DB, TAR, and media file decryption
