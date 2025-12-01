import os
from pathlib import Path
from typing import Dict, List, Tuple

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

APP_TITLE = "VietOCR Labeling API"
LABEL_FILE_NAME = os.getenv("LABEL_FILE", "label.txt")
DATA_DIR = Path(os.getenv("DATA_DIR", "./data")).resolve()
ALLOWED_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp"}


class LabelBody(BaseModel):
    label: str


app = FastAPI(title=APP_TITLE, version="0.1.0")
app.mount("/files", StaticFiles(directory=DATA_DIR), name="files")


def ensure_data_dir() -> None:
    if not DATA_DIR.exists():
        raise RuntimeError(f"DATA_DIR '{DATA_DIR}' does not exist. Create it or set DATA_DIR env.")
    if not DATA_DIR.is_dir():
        raise RuntimeError(f"DATA_DIR '{DATA_DIR}' is not a directory.")


def safe_filename(filename: str) -> str:
    # Only keep the final component to avoid path traversal
    return Path(filename).name


def resolve_image_path(filename: str) -> Tuple[str, Path]:
    name_only = safe_filename(filename)
    img_path = (DATA_DIR / name_only).resolve()
    if DATA_DIR not in img_path.parents and img_path != DATA_DIR:
        raise HTTPException(status_code=400, detail="Invalid filename path.")
    if img_path.suffix.lower() not in ALLOWED_IMAGE_EXTS:
        raise HTTPException(status_code=400, detail="Unsupported image extension.")
    return name_only, img_path


def merge_label_files() -> None:
    """
    Rebuild label.txt from existing per-image .txt files when label.txt is missing.
    """
    ensure_data_dir()
    lines: List[str] = []
    for txt_file in sorted(DATA_DIR.glob("*.txt")):
        if txt_file.name.lower() == LABEL_FILE_NAME.lower():
            continue
        content = txt_file.read_text(encoding="utf-8").strip()
        image_name = txt_file.with_suffix(".jpg").name
        lines.append(f"{image_name}\t{content}")
    label_file = DATA_DIR / LABEL_FILE_NAME
    label_file.write_text("\n".join(lines), encoding="utf-8")


def load_labels() -> Dict[str, str]:
    label_file = DATA_DIR / LABEL_FILE_NAME
    if not label_file.exists():
        merge_label_files()
    labels: Dict[str, str] = {}
    if not label_file.exists():
        return labels
    for line in label_file.read_text(encoding="utf-8").splitlines():
        if "\t" not in line:
            continue
        filename, text = line.split("\t", 1)
        labels[safe_filename(filename)] = text
    return labels


def save_labels(labels: Dict[str, str]) -> None:
    label_file = DATA_DIR / LABEL_FILE_NAME
    label_file.write_text(
        "\n".join(f"{name}\t{label}" for name, label in sorted(labels.items())),
        encoding="utf-8",
    )


def paginate(items: List[Tuple[str, str]], page: int, size: int) -> List[Tuple[str, str]]:
    start = max(page - 1, 0) * size
    end = start + size
    return items[start:end]


@app.on_event("startup")
def on_startup() -> None:
    ensure_data_dir()
    # Initialize label file if needed
    if not (DATA_DIR / LABEL_FILE_NAME).exists():
        merge_label_files()


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok", "data_dir": str(DATA_DIR)}


@app.get("/labels")
def list_labels(
    page: int = 1,
    size: int = 50,
    only_unlabeled: bool = False,
    search: str = "",
) -> Dict[str, object]:
    labels = load_labels()
    search_lower = search.lower().strip()
    filtered = []
    for name, label in sorted(labels.items()):
        if only_unlabeled and label.strip() != "":
            continue
        if search_lower and search_lower not in name.lower() and search_lower not in label.lower():
            continue
        filtered.append((name, label))

    total = len(filtered)
    page_items = paginate(filtered, page, size)
    items = [{"file": name, "label": label, "image_url": f"/files/{name}"} for name, label in page_items]
    return {"total": total, "page": page, "size": size, "items": items}


@app.get("/labels/{filename}")
def get_label(filename: str) -> Dict[str, str]:
    labels = load_labels()
    name_only = safe_filename(filename)
    if name_only not in labels:
        raise HTTPException(status_code=404, detail="Label not found.")
    return {"file": name_only, "label": labels[name_only], "image_url": f"/files/{name_only}"}


@app.post("/labels/{filename}")
def set_label(filename: str, body: LabelBody) -> Dict[str, str]:
    name_only, img_path = resolve_image_path(filename)
    if not img_path.exists():
        raise HTTPException(status_code=404, detail="Image not found in DATA_DIR.")

    labels = load_labels()
    labels[name_only] = body.label
    txt_path = img_path.with_suffix(".txt")
    txt_path.write_text(body.label, encoding="utf-8")
    save_labels(labels)
    return {"file": name_only, "label": body.label}


@app.post("/refresh")
def refresh_labels() -> Dict[str, str]:
    merge_label_files()
    return {"status": "refreshed"}
