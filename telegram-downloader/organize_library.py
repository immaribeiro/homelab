#!/usr/bin/env python3
"""Organize the ebook library into Language/Author/ folders.

- Reads real title/author from epub OPF metadata (content.opf) when present;
  falls back to filename heuristics for PDFs and metadata-less epubs.
- Dedupes by MD5: duplicate copies are moved to a _duplicates/ staging dir
  (never deleted outright).
- Clean filename convention: "<Title>.epub" inside "<Author>/" folders;
  series info appended as " (Series #N)" when known.
- Idempotent + safe: dry-run mode shows the plan without moving anything.
"""

import argparse
import hashlib
import re
import shutil
import sys
import unicodedata
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

# ---------------------------------------------------------------------------
# Metadata extraction
# ---------------------------------------------------------------------------

NS = {
    "dc": "http://purl.org/dc/elements/1.1/",
    "opf": "http://www.idpf.org/2007/opf",
}


def md5_of(path: Path) -> str:
    h = hashlib.md5()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def epub_metadata(path: Path):
    """Return (title, authors, series, series_index) from the epub's OPF, or None."""
    try:
        with zipfile.ZipFile(path) as zf:
            opf_names = [n for n in zf.namelist() if n.lower().endswith(".opf")]
            if not opf_names:
                return None
            # Prefer content.opf, else the first .opf
            opf_name = next((n for n in opf_names if "content.opf" in n.lower()), opf_names[0])
            raw = zf.read(opf_name)
    except Exception:
        return None

    try:
        root = ET.fromstring(raw)
    except Exception:
        return None

    def dc_text(tag):
        el = root.find(f".//dc:{tag}", NS)
        return el.text.strip() if el is not None and el.text and el.text.strip() else None

    title = dc_text("title")
    creators = [el.text.strip() for el in root.findall(".//dc:creator", NS)
                if el.text and el.text.strip()]
    # series from calibre meta tags: <meta name="calibre:series" content="...">
    series = None
    series_index = None
    for meta in root.findall(".//opf:meta", NS):
        name = meta.get("name", "")
        if name == "calibre:series":
            series = meta.get("content")
        elif name == "calibre:series_index":
            series_index = meta.get("content")

    if not title:
        return None
    return title, creators, series, series_index


# ---------------------------------------------------------------------------
# Filename heuristics (fallback for PDFs / metadata-less files)
# ---------------------------------------------------------------------------

STRIP_RE = re.compile(
    r"\(?(z-lib(?:rary)?(?:\.org)?|z_library(?:_sk)?(?:_\d+lib_sk)?(?:_z_lib(?:_sk)?)?"
    r"|1lib\.sk|zlibrary|Z-Library)\)?"
    r"|·\s*vers[aã]o\s*\d+(?:\s*\(\d+\))?"
    r"|[-–—_]\s*PT\b|[-–—_]\s*PT[-–_]PT\b|\bPT[-–_]PT\b|\bptpt\b|\(ptpt\)"
    r"|\(?\d+\)?$",
    re.IGNORECASE,
)

# z-lib style suffixes: cut at the first explicit marker, keep everything
# before it (e.g. "Sete_Breves_..._Carlo_R_z_library_sk,_1lib_sk," -> title part).
ZLIB_CUT_RE = re.compile(r"(?:z[-_]?lib(?:rary)?|1lib|zlibrary)", re.IGNORECASE)

# Titles that are actually watermarks/notices, not book titles
JUNK_TITLE_RE = re.compile(
    r"disponibilizado|consulta|propriedade|watermark|documento|for (personal|review)|"
    r"licensed|review copy|advance copy",
    re.IGNORECASE,
)

UNDERSCORE_SPLIT = re.compile(r"[_]{2,}|\s{2,}")


def cut_zlib(s: str) -> str:
    """Cut a string at the first z-lib marker, keeping the part before it.
    Also swallows an unbalanced '(' right before the marker, and any
    trailing '(' / ',' / '_' left over."""
    m = ZLIB_CUT_RE.search(s)
    if m:
        cut = m.start()
        if cut > 0 and s[cut - 1] == "(":
            cut -= 1
        s = s[:cut]
    s = s.rstrip(" (,;_")
    return s


def parse_filename(stem: str):
    """Heuristic parse of 'Title - Author' / 'Author - Title' / 'Title (Author)'
    / underscore styles. Returns (title, author_or_None)."""
    s = stem.strip()
    s = STRIP_RE.sub(" ", s).strip()
    s = cut_zlib(s).strip()
    s = re.sub(r"\s+", " ", s)

    # 'Title (Author)' — but beware '(Series #N)' and '(Livro 3)'
    m = re.search(r"\(([^()]*)\)\s*$", s)
    if m:
        inner = m.group(1).strip()
        if re.search(r"#?\d|livro|saga|book|vol", inner, re.I) and not re.search(r"[A-Z]\.\s?[A-Z]", inner):
            pass  # it's a series marker, not author
        else:
            title = s[: m.start()].strip(" -–—")
            return title, inner

    # 'Title - Author' with multiple dashes: author = last dash segment.
    # Also tolerate ')-Author' (title ends with series in parens).
    s2 = s.replace(")-", ") - ")
    parts = re.split(r"\s+[-–—]\s+", s2)
    if len(parts) >= 2:
        title = " - ".join(parts[:-1]).strip(" -–—")
        author = parts[-1].strip(" -–—")
        return title, author

    # Underscore style 'Title_Author' / 'Author_Title' (z-lib names)
    parts = [p.strip() for p in s.split("_") if p.strip() and any(c.isalnum() for c in p)]
    if len(parts) >= 2:
        # Author is the trailing run of capitalized words (up to 3),
        # stopping at lowercase particles like 'de/da/dos/e/em/para'.
        idx = len(parts) - 1
        while idx >= 0 and parts[idx][:1].isupper():
            idx -= 1
        author_parts = parts[idx + 1:]
        if len(author_parts) >= 1 and len(author_parts) <= 3:
            author = " ".join(author_parts)
            title = " ".join(parts[:idx + 1])
            return title, author
        author = parts[-1]
        title = " ".join(parts[:-1])
        return title, author

    return s, None


def clean_title(title: str) -> str:
    t = title.strip()
    t = STRIP_RE.sub(" ", t).strip()
    t = cut_zlib(t).strip()
    t = re.sub(r"\s+", " ", t)
    t = re.sub(r"^[\d\s.\-–—]+", "", t)  # leading series numbers
    t = t.strip(" -–—")
    # collapse repeated spaces/dots
    t = re.sub(r"\s{2,}", " ", t)
    if JUNK_TITLE_RE.search(t):
        return None
    return t or None


def safe_name(name: str) -> str:
    name = name.replace("/", "_").replace("\\", "_").replace("\n", " ").replace("\r", " ")
    name = re.sub(r"\s+", " ", name).strip()
    return name or "Unknown"


# ---------------------------------------------------------------------------
# Author normalization: merge spellings of the same author into one folder
# ---------------------------------------------------------------------------

JUNK_AUTHOR_RE = re.compile(
    r"MT Color|Diseño S\.L|Diseño SL|Editora|Porto Editora|z[-_]lib|1lib|"
    r"watermark|propriedade|www\.|\.com|\.org|documento|tradu|Trad\.",
    re.IGNORECASE,
)

# Targeted corrections for known typos baked into epub metadata
AUTHOR_FIXUPS = {
    "F.eist": "Feist",
    "M.aas": "Maas",
    "Killmore": "Kilmore",
}

# Known books whose filenames truncate/mangle the author name (matched on
# normalized filename without extension). Value is (title, author).
STEM_FIXUPS = {
    # Keys are accent-free, title-only stems from the organized library.
    "a mais bela maldicao": ("A Mais Bela Maldicao", "Rui Couceiro"),
    "a medica de familia": ("A Médica de Família", "J. M. Dalgliesh"),
    "a rapariga no abismo maddie ives": ("A Rapariga no Abismo (Maddie Ives)", "Charlie Gallagher"),
    "iliada": ("Ilíada", "Frederico Lourenço"),
    "o pecador": ("O Pecador", "J. R. Ward"),
    "o principe nabo": ("O Principe Nabo", "Ilse Losa"),
    "sete breves licoes de fisica": ("Sete Breves Lições de Física", "Carlo Rovelli"),
    "ulisses": ("Ulisses", "Maria Alberta Meneres"),
    "um piano para cavalos altos": ("Um Piano para Cavalos Altos", "Sandro William Junqueira"),
    "victoria": ("Victoria", "Paloma Sánchez-Garnica"),
}


def normalize_author(author: str) -> str:
    """Normalize one author name: case, spacing, Lastname,Firstname flip,
    and drop obvious non-author junk appended after ' & '."""
    a = author.strip()
    if not a:
        return None

    # "Maria Inês Almeida | Catarina Bakker" -> "Maria Inês Almeida & Catarina Bakker"
    a = re.sub(r"\s*\|\s*", " & ", a)

    for bad, good in AUTHOR_FIXUPS.items():
        a = a.replace(bad, good)

    # strip junk collaborators: "Katherine Garbera & MT Color & Diseño S.L." -> "Katherine Garbera"
    a = re.split(r"\s*&\s*", a)[0].strip()
    if JUNK_AUTHOR_RE.search(a):
        return None

    # Portuguese "com" (with) -> " & " : "MIEP GIES com Alison Leslie Gold" -> "MIEP GIES & Alison Leslie Gold"
    a = re.sub(r"\s+com\s+", " & ", a, flags=re.IGNORECASE)

    # Multi-author lists: "Jørn Lier Horst, Thomas Enger" (first part multi-word)
    # vs "Lastname, Firstname" (first part single word). Flip only the latter.
    if "," in a:
        parts = [p.strip() for p in a.split(",")]
        if len(parts) == 2 and parts[0] and parts[1]:
            if " " not in parts[0]:
                a = f"{parts[1]} {parts[0]}"  # Lastname, Firstname -> Firstname Lastname
            else:
                a = " & ".join(p for p in parts if p)  # two authors

    # ALL-CAPS (or mostly) -> title case (HARLAN COBEN -> Harlan Coben)
    if a == a.upper():
        a = a.title()
    # Mixed case but with an all-caps word like MIEP GIES -> title-case whole
    elif re.search(r"\b[A-ZÀ-Ý]{4,}\b", a):
        a = a.title()

    # Fix spacing around initials: "J.R.Ward" -> "J. R. Ward" (dot before
    # an uppercase letter gains a space). Must NOT touch "Sarah J. Maas".
    a = re.sub(r"\.(?=[A-Z])", ". ", a)
    # "J. R Ward" -> "J. R. Ward" (single uppercase initial missing its dot
    # before a capitalized surname)
    a = re.sub(r"\b([A-Z]) (?=[A-Z][a-zà-ý])", r"\1. ", a)
    a = re.sub(r"\s+", " ", a).strip()

    # trailing dot cleanup (J. R. Ward. -> J. R. Ward)
    a = re.sub(r"\.$", "", a).strip()
    return a or None


def normalize_author_list(authors) -> str:
    """Join multiple creators into one folder name, normalizing each."""
    seen = []
    for raw in authors:
        n = normalize_author(raw)
        if n and n not in seen:
            seen.append(n)
    if not seen:
        return None
    if len(seen) == 1:
        return seen[0]
    return " & ".join(seen[:2])


# ---------------------------------------------------------------------------
# Organizer
# ---------------------------------------------------------------------------

def collect(path: Path):
    """Yield (file, ext, metadata_or_None) for every book under the library,
    skipping the _duplicates staging dir and any dotfolders."""
    for p in sorted(path.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(path)
        if rel.parts and rel.parts[0] in ("_duplicates", "_Uncategorized", "Unknown"):
            continue
        ext = p.suffix.lower()
        if ext not in (".epub", ".pdf"):
            continue
        meta = epub_metadata(p) if ext == ".epub" else None
        yield p, ext, meta


def plan_organization(src_dir: Path, dry_run: bool):
    """Compute moves/dedupes; print plan. Returns list of actions."""
    files = list(collect(src_dir))
    by_md5 = {}
    for p, ext, meta in files:
        by_md5.setdefault(md5_of(p), []).append((p, ext, meta))

    actions = []  # (kind, src, dst)  kind in {move, duplicate, keep}
    planned_dirs = set()

    for digest, group in sorted(by_md5.items(), key=lambda kv: kv[1][0][0].name):
        if len(group) > 1:
            # keep the one with the best name (longest, cleanest) — first sorted
            group.sort(key=lambda item: (-len(item[0].stem), item[0].stem))
            keeper = group[0]
            for dup in group[1:]:
                actions.append(("duplicate", dup[0], None))
        else:
            keeper = group[0]

        p, ext, meta = keeper
        title, author, series, sindex = None, None, None, None
        # Known-filename fixups take precedence (truncated/mangled authors)
        stem_clean = cut_zlib(STRIP_RE.sub(" ", p.stem)).strip()
        stem_key = unicodedata.normalize("NFKD", stem_clean)
        stem_key = "".join(c for c in stem_key if not unicodedata.combining(c))
        stem_key = re.sub(r"[^a-z0-9 ]", "", stem_key.lower()).strip()
        if stem_key in STEM_FIXUPS:
            fix_title, fix_author = STEM_FIXUPS[stem_key]
            title, author = fix_title, fix_author
            meta = None
        if meta:
            title, creators, series, sindex = meta
            title = clean_title(title)
            if creators:
                author = normalize_author_list(creators)
        # Filename fallback: full override when metadata missing/junk,
        # or just the author when metadata had no usable creator.
        if not title:
            title, parsed_author = parse_filename(p.stem)
            title = clean_title(title) or "Unknown"
            if not author and parsed_author:
                author = normalize_author(parsed_author)
        elif not author:
            _, parsed_author = parse_filename(p.stem)
            if parsed_author:
                # Filename may be "Title - Author" OR "Author - Title".
                # Use the metadata title to decide: if the metadata title
                # appears in the LAST dash segment, the first segment is
                # the author (e.g. "Frederico Lourenço - Ilíada Homero").
                segments = re.split(r"\s+[-–—]\s+", p.stem.replace(")-", ") - "))
                if len(segments) >= 2 and title:
                    t_norm = re.sub(r"[^a-z0-9à-ÿ]", "", title.lower())
                    last_norm = re.sub(r"[^a-z0-9à-ÿ]", "", segments[-1].lower())
                    first_norm = re.sub(r"[^a-z0-9à-ÿ]", "", segments[0].lower())
                    if t_norm and (t_norm in last_norm or last_norm in t_norm):
                        parsed_author = segments[0]
                author = normalize_author(parsed_author)

        title = safe_name(title or p.stem)
        author = safe_name(author or "_Uncategorized")

        if series:
            idx = f" #{sindex}" if sindex else ""
            title = f"{title} ({series}{idx})"

        dst_dir = src_dir / author
        planned_dirs.add(dst_dir)
        target = dst_dir / f"{title}{p.suffix.lower()}"
        # Preserve an already-organized '(2)' edition when its clean base name
        # is not present; the executor uses the same collision convention.
        if p.parent == dst_dir and not target.exists():
            target = p
        if target == p:
            actions.append(("keep", p, None))
        else:
            # Plan the same collision destination that execution will use.
            if target.exists() and target != p:
                target = target.with_name(target.stem + " (2)" + target.suffix)
            actions.append(("keep", p, None) if target == p else ("move", p, target))

    # print plan
    moves = [a for a in actions if a[0] == "move"]
    dups = [a for a in actions if a[0] == "duplicate"]
    print(f"Library: {src_dir}")
    print(f"Files scanned: {len(files)}  |  moves: {len(moves)}  |  duplicates: {len(dups)}")
    print()
    print("Author folders to create:")
    for d in sorted(planned_dirs):
        if d != src_dir:
            print(f"  {d.relative_to(src_dir)}/")
    print()
    print("First 25 moves:")
    for kind, src, dst in actions[:25]:
        if kind == "move":
            print(f"  {src.name}  ->  {dst.parent.name}/{dst.name}")
        elif kind == "duplicate":
            print(f"  [DUP] {src.name}")
        elif kind == "keep":
            print(f"  [keep] {src.name}")
    if len(actions) > 25:
        print(f"  ... and {len(actions) - 25} more actions")
    print()
    if not dry_run:
        print("EXECUTING (dry_run off)...")
        dup_dir = src_dir / "_duplicates"
        for kind, src, dst in actions:
            if kind == "move":
                dst.parent.mkdir(parents=True, exist_ok=True)
                if dst.exists():
                    dst = dst.with_name(dst.stem + " (2)" + dst.suffix)
                shutil.move(str(src), str(dst))
            elif kind == "duplicate":
                dup_dir.mkdir(parents=True, exist_ok=True)
                shutil.move(str(src), str(dup_dir / src.name))
        print("Done.")
    return actions


def main():
    ap = argparse.ArgumentParser(description="Organize ebook library into Author/ folders")
    ap.add_argument("--dir", default="/Users/imma/Downloads/ebook-library/PT",
                    help="library root to organize")
    ap.add_argument("--execute", action="store_true",
                    help="actually move files (default: dry-run plan only)")
    args = ap.parse_args()

    src = Path(args.dir).expanduser()
    if not src.is_dir():
        print(f"[error] not a directory: {src}")
        sys.exit(1)

    plan_organization(src, dry_run=not args.execute)


if __name__ == "__main__":
    main()
