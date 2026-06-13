"""
Script d'import des photos dans uploads/ et en DB.

Usage :
  cd backend
  conda activate y-plaza
  python import_photos.py --dossier "../mes_photos/"

Convention : les photos sont nommées dans l'ordre ; les 2 premières vont au
1er bien (par created_at ASC), les 2 suivantes au 2ème bien, etc.
Formats acceptés : .jpg .jpeg .png .webp (insensible à la casse).
"""

import argparse
import re
import shutil
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.property import Property, PropertyImage

BASE = Path(__file__).resolve().parent.parent
UPLOAD_DIR = BASE / "uploads" / "properties"
ACCEPTED = {".jpg", ".jpeg", ".png", ".webp"}


def _natural_key(path: Path) -> list:
    return [int(c) if c.isdigit() else c.lower() for c in re.split(r"(\d+)", path.name)]


def collect_photos(folder: Path) -> list[Path]:
    # Supporte à la fois un dossier plat et des sous-dossiers (bien-001/, bien-002/, ...)
    photos = [f for f in folder.rglob('*') if f.is_file() and f.suffix.lower() in ACCEPTED]
    return sorted(photos, key=lambda p: _natural_key(p.parent) + _natural_key(p))


def run(dossier: str) -> None:
    folder = Path(dossier).resolve()
    if not folder.exists():
        print(f"❌ Dossier introuvable : {folder}")
        sys.exit(1)

    photos = collect_photos(folder)
    if not photos:
        print(f"❌ Aucune photo acceptée trouvée dans {folder}")
        sys.exit(1)

    pairs = [(photos[i], photos[i + 1]) for i in range(0, len(photos) - 1, 2)]
    print(f"{len(photos)} photos → {len(pairs)} paires")

    db: Session = SessionLocal()
    try:
        props = (
            db.query(Property)
            .order_by(Property.created_at.asc())
            .limit(len(pairs))
            .all()
        )

        if len(props) < len(pairs):
            print(f"⚠  Seulement {len(props)} biens en DB — {len(pairs) - len(props)} paires ignorées")
            pairs = pairs[: len(props)]

        updated = 0
        for prop, (img1, img2) in zip(props, pairs):
            # Supprime les images existantes pour ce bien
            db.query(PropertyImage).filter(PropertyImage.property_id == prop.id).delete()

            dest_dir = UPLOAD_DIR / str(prop.id)
            dest_dir.mkdir(parents=True, exist_ok=True)

            for idx, src in enumerate([img1, img2]):
                filename = f"{uuid.uuid4()}{src.suffix.lower()}"
                dest = dest_dir / filename
                shutil.copy2(src, dest)
                url = f"/uploads/properties/{prop.id}/{filename}"
                db.add(PropertyImage(property_id=prop.id, url=url, is_primary=(idx == 0)))
                label = "PRIMARY" if idx == 0 else "second "
                print(f"  [{str(prop.id)[:8]}] {label} ← {src.name}")

            updated += 1

        db.commit()
        print(f"\n✅ {updated} biens mis à jour.")
    except Exception as e:
        db.rollback()
        print(f"❌ Erreur : {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Import photos → uploads/ + DB")
    parser.add_argument("--dossier", required=True, help="Chemin du dossier contenant les photos")
    args = parser.parse_args()
    run(args.dossier)
