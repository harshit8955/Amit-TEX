# Amit Tex Business Manager (Desktop Python Software)

A ready-to-run desktop software for **Amit Tex (Surat, Gujarat)** built with **Python + Tkinter + SQLite**.

## What is included

- Secure login with roles:
  - `admin`
  - `sub_admin`
  - `temp`
- Stock management for cloth and variants:
  - SKU, cloth name, variety, color, quantity, cost and selling price
- Billing management:
  - Create invoice, add stock items, GST %, auto-total, stock deduction
- Challan management:
  - Challan number, party, vehicle number, notes
- Admin panel:
  - Create users
  - Enable/disable specific features per user
- Data sharing:
  - Export/import complete JSON data for branch/partner sharing
- Logo/banner shown inside software login screen and app header

## Default login

- Username: `admin`
- Password: `admin123`

> Change this password immediately from the database/user management flow for production usage.

## Run locally

```bash
python3 main.py
```

No external package is required (uses Python standard library).

## Create desktop icon / launcher

### Windows (shortcut)
1. Right-click desktop → New → Shortcut.
2. Target:
   ```
   C:\Path\To\python.exe C:\Path\To\Amit-TEX\main.py
   ```
3. Name it: `Amit Tex Manager`.
4. Right-click shortcut → Properties → Change Icon (optional custom `.ico`).

### Linux (desktop file)
Create `AmitTex.desktop`:

```ini
[Desktop Entry]
Name=Amit Tex Manager
Exec=python3 /absolute/path/to/Amit-TEX/main.py
Icon=/absolute/path/to/icon.png
Type=Application
Terminal=false
Categories=Office;
```

Then mark executable:
```bash
chmod +x AmitTex.desktop
```

## Database

SQLite file: `amit_tex.db` (auto-created in project folder).

## Future implementation roadmap

1. **Professional Invoice PDF** with GST format and print-ready templates.
2. **WhatsApp/SMS invoice sending** via API integration.
3. **Barcode support** for SKU scanning.
4. **Advanced reports** (daily sale, profit, stock aging, party ledger).
5. **Cloud sync + multi-device real-time data**.
6. **Audit logs** for user activity and permission changes.
7. **Backup scheduler** and one-click restore.
8. **Multi-branch mode** for Surat + other warehouses.
9. **Purchase order and supplier management**.
10. **Desktop installer** (`.exe` via PyInstaller, signed package).

## Notes

- This is a functional MVP intended for quick deployment and customization.
- You can extend role/permission logic for highly granular controls.
