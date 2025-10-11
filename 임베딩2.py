# save_to_faiss_gpu.py
import os, io, json, hashlib, argparse, time, sys
from contextlib import contextmanager
from pathlib import Path
import numpy as np
import faiss
import fitz  # PyMuPDF
from PIL import Image
import pytesseract
from dotenv import load_dotenv
from openai import OpenAI

# -------- Logger / Timer --------
def _ts():
    return time.strftime("%H:%M:%S")

def log(msg):
    print(f"[{_ts()}] {msg}", flush=True)

@contextmanager
def stage(name):
    t0 = time.time()
    log(f"▶ {name} 시작")
    try:
        yield
        log(f"✔ {name} 완료 ({time.time()-t0:.2f}s)")
    except Exception as e:
        log(f"✖ {name} 실패 ({time.time()-t0:.2f}s): {type(e).__name__}: {e}")
        raise

# -------- Helpers --------
def stable_id(s: str) -> int:
    h = hashlib.sha1(s.encode("utf-8")).digest()
    u = int.from_bytes(h[:8], "big", signed=False)  # 0..2^64-1
    u &= 0x7FFFFFFFFFFFFFFF                         # ▶ 63-bit 양수로 강제
    return u

def chunk_text(s, max_chars=1200, overlap=150, endchars=".?!\n", hard_cap=120_000):
    s = " ".join((s or "").split())
    if not s:
        return []
    if len(s) > hard_cap:
        s = s[:hard_cap]

    n = len(s)

    # ★★★ 핵심 버그픽스: 짧은 문자열은 한 번만 리턴
    if n <= max_chars:
        return [s]

    out = []
    i = 0
    while i < n:
        j = min(n, i + max_chars)
        k = -1
        for c in endchars:
            pos = s.rfind(c, i, j)
            if pos > k:
                k = pos
        cut = j if (k == -1 or k <= i + 100) else k + 1
        seg = s[i:cut].strip()
        if seg:
            out.append(seg)

        # 다음 시작 인덱스
        next_i = cut - overlap
        i = next_i if next_i > i else cut   # ← cut까지 점프(루프 종료 보장)
    return out


def extract_blocks_text(page):
    """
    페이지 전체 텍스트 기반 추출 (문단 단위 청크 생성용)
    - 기존: PyMuPDF 레이아웃 블록 단위 추출
    - 변경: 페이지 전체 텍스트 추출 → chunk_text()에서 문장/문단 단위로 처리
    """
    # 페이지 전체 텍스트를 한 문자열로 추출
    text = page.get_text("text") or ""
    text = " ".join(text.split())  # 공백 정규화
    return [text] if text else []


def page_text_or_ocr(page, dpi=300, ocr_lang="kor+eng",
                     min_text_len=60, ocr_max_pixels=12_000_000):
    """텍스트 충분하면 그대로, 아니면 OCR (초대형 페이지는 자동 다운스케일)"""
    txt = page.get_text("text", flags=0) or ""
    if len(txt.strip()) >= min_text_len:
        return txt, None

    pix = page.get_pixmap(dpi=dpi, alpha=False)
    w, h = pix.width, pix.height
    if w * h > ocr_max_pixels:
        scale = (ocr_max_pixels / (w * h)) ** 0.5
        dpi2 = max(96, int(dpi * scale))
        pix = page.get_pixmap(dpi=dpi2, alpha=False)
    img = Image.open(io.BytesIO(pix.tobytes("png")))
    txt = pytesseract.image_to_string(img, lang=ocr_lang)
    return txt, [0, 0, img.width, img.height]

def embed_texts(client, model, texts, batch=128, retries=5, backoff=1.8, dimensions=None, debug=False):
    vecs = []
    total = len(texts)
    for start in range(0, total, batch):
        payload = texts[start:start+batch]
        for t in range(retries):
            try:
                t0 = time.time()
                if debug:
                    log(f"[EMB] batch {start}-{start+len(payload)} try={t+1}")
                res = client.embeddings.create(
                    model=model,
                    input=payload,
                    **({"dimensions": dimensions} if dimensions else {})
                )
                dt = time.time() - t0
                vps = len(payload)/dt if dt > 0 else float("inf")
                log(f"[EMB] ok: {len(payload)} items in {dt:.2f}s ({vps:.1f} it/s) [{start+len(payload)}/{total}]")
                vecs.extend([e.embedding for e in res.data])
                break
            except Exception as e:
                log(f"[EMB][warn] {type(e).__name__}: {e} (try {t+1}/{retries})")
                if t == retries - 1:
                    raise
                time.sleep(backoff * (t + 1))
    X = np.array(vecs, dtype="float32")
    # 코사인/IP 대비 정규화
    X /= (np.linalg.norm(X, axis=1, keepdims=True) + 1e-12)
    return X

# ==== Index Utils (GPU 지원) ====
def _gpu_available():
    try:
        return hasattr(faiss, "get_num_gpus") and faiss.get_num_gpus() > 0
    except Exception:
        return False

def _to_gpu(index_cpu, use_fp16=True, shard_all=True):
    """CPU Index(IDMap/FlatIP) -> GPU Index"""
    res = faiss.StandardGpuResources()
    co = faiss.GpuClonerOptions()
    co.useFloat16 = use_fp16
    if shard_all and faiss.get_num_gpus() > 1:
        return faiss.index_cpu_to_all_gpus(index_cpu, co)
    else:
        return faiss.index_cpu_to_gpu(res, 0, index_cpu, co)

def _to_cpu(index_any):
    try:
        return faiss.index_gpu_to_cpu(index_any)
    except Exception:
        return index_any  # 이미 CPU

def load_or_create_index(dim, index_path, prefer_gpu=True):
    """디스크 저장은 CPU 인덱스, 메모리는 GPU 선호"""
    if os.path.exists(index_path):
        cpu_idx = faiss.read_index(index_path)
        if cpu_idx.d != dim:
            raise ValueError(f"Index dim({cpu_idx.d}) != embedding dim({dim})")
        if not isinstance(cpu_idx, (faiss.IndexIDMap, faiss.IndexIDMap2)):
            cpu_idx = faiss.IndexIDMap(cpu_idx)
    else:
        base = faiss.IndexFlatIP(dim)  # 정규화했으므로 IP=cosine
        cpu_idx = faiss.IndexIDMap(base)

    if prefer_gpu and _gpu_available():
        try:
            gpu_idx = _to_gpu(cpu_idx)
            return gpu_idx, True
        except Exception:
            pass
    return cpu_idx, False

def persist_index(index_any, index_path):
    cpu_idx = _to_cpu(index_any)
    faiss.write_index(cpu_idx, index_path)

def append_meta(meta_path, rows):
    with open(meta_path, "a", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

def already_indexed_ids(meta_path):
    if not os.path.exists(meta_path):
        return set()
    ids = set()
    with open(meta_path, "r", encoding="utf-8") as f:
        for line in f:
            try:
                obj = json.loads(line)
                if "_id" in obj:
                    ids.add(int(obj["_id"]))
            except:
                pass
    return ids

def process_pdf(pdf_path: Path, dpi=300, ocr_lang="kor+eng",
                chunk=1200, overlap=150,
                max_pages=None, text_only=False, debug=False):
    doc = fitz.open(str(pdf_path))
    blocks_meta = []
    total_pages = len(doc)
    if max_pages is not None:
        total_pages = min(total_pages, max_pages)

    log(f"[PDF] {pdf_path.name}: pages={total_pages} dpi={dpi} text_only={text_only}")
    t0 = time.time()
    for pno in range(total_pages):
        if (pno + 1) % 10 == 0:
            log(f"[PDF] progress {pno+1}/{total_pages} (elapsed {time.time()-t0:.1f}s)")

        page = doc[pno]

                # 1) 블록 기반 텍스트 우선
        raw_blocks = extract_blocks_text(page)
        log(f"[DBG] p{pno+1} raw_blocks={len(raw_blocks)} first_len={len(raw_blocks[0]) if raw_blocks else 0}")
        joined = " ".join(raw_blocks) if raw_blocks else ""
        log(f"[DBG] p{pno+1} joined_len={len(joined)}")

        # ★ 모든 블록을 하나의 문자열로 합쳐서 한 번만 chunk_text() 실행
        joined = " ".join(raw_blocks) if raw_blocks else ""
        if joined:
            page_chunks = 0
            for ci, ck in enumerate(chunk_text(joined, max_chars=chunk, overlap=overlap)):
                blocks_meta.append({
                    "doc_id": pdf_path.name,
                    "source_pdf": str(pdf_path),
                    "page": pno + 1,
                    "block_id": f"p{pno+1}_b000_{ci:03d}",  # ★ 페이지당 블록 ID 고정
                    "type": "paragraph",
                    "text": ck,
                    "bbox": None
                })
                page_chunks += 1
            if debug:
                log(f"[PAGE] {pdf_path.name}#{pno+1}: blocks_joined=1 chunks={page_chunks}")
            # ★ 텍스트를 썼으면 OCR로 내려가지 않도록 즉시 다음 페이지로
            continue


        # 2) 블록 부족/없으면 OCR fallback
        text, bbox = page_text_or_ocr(page, dpi=dpi, ocr_lang=ocr_lang)
        if not text or not text.strip():
            if debug:
                log(f"[PAGE] {pdf_path.name}#{pno+1}: empty after OCR, skip")
            continue

        cnt = 0
        for ci, ck in enumerate(chunk_text(text, max_chars=chunk, overlap=overlap)):
            blocks_meta.append({
                "doc_id": pdf_path.name,
                "source_pdf": str(pdf_path),
                "page": pno + 1,
                "block_id": f"p{pno+1}_{ci:03d}",
                "type": "paragraph",
                "text": ck,
                "bbox": bbox
            })
            cnt += 1
        if debug:
            log(f"[PAGE] {pdf_path.name}#{pno+1}: OCR chunks={cnt}")

    log(f"[PDF] {pdf_path.name}: total_chunks={len(blocks_meta)} (took {time.time()-t0:.1f}s)")
    return blocks_meta

def upsert_blocks_to_faiss(blocks, client, model, index_path, meta_path,
                           batch=128, dims=None, prefer_gpu=True, fp16=True, debug=False):
    if not blocks:
        log("[FAISS] no blocks to upsert")
        return 0

    texts = [b["text"] for b in blocks]
    log(f"[EMB] request: n_texts={len(texts)} batch={batch} dims={dims}")

    with stage("Embedding"):
        X = embed_texts(client, model, texts, batch=batch, dimensions=dims, debug=debug)

    dim = X.shape[1]
    with stage(f"Index load/create dim={dim}"):
        index, is_gpu = load_or_create_index(dim, index_path, prefer_gpu=prefer_gpu)
        log(f"[FAISS] backend={'GPU' if is_gpu else 'CPU'}")

    have = already_indexed_ids(meta_path)
    to_add_vecs, to_add_ids, to_add_meta = [], [], []
    for b, v in zip(blocks, X):
        _id = stable_id(f'{b["doc_id"]}:{b["block_id"]}:{hashlib.sha1(b["text"].encode()).hexdigest()}')
        if _id in have:
            continue
        to_add_vecs.append(v)
        to_add_ids.append(_id)
        m = dict(b)
        m["_id"] = _id
        to_add_meta.append(m)

    if not to_add_ids:
        log("[FAISS] nothing to add (all deduped)")
        return 0

    A = np.ascontiguousarray(np.vstack(to_add_vecs).astype("float32"))
    I = np.ascontiguousarray(np.array(to_add_ids, dtype=np.int64))
    log(f"[FAISS] to_add={len(I)} dim={dim}")

    with stage("FAISS add_with_ids"):
        index.add_with_ids(A, I)

    with stage("Persist index"):
        persist_index(index, index_path)
        log(f"[FAISS] saved -> {index_path}")

    append_meta(meta_path, to_add_meta)
    log(f"[META] appended {len(to_add_meta)} rows -> {meta_path}")
    return len(to_add_ids)

# -------- Main (CLI) --------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", nargs="?", default="/home/dlab5/사기설/건설안전지침", help="PDF 파일 또는 폴더 경로")
    parser.add_argument("--model", default="text-embedding-3-small")
    parser.add_argument("--dimensions", type=int, default=None, help="차원 축소 (예: 1024)")
    parser.add_argument("--dpi", type=int, default=300)
    parser.add_argument("--ocr_lang", default="kor+eng")
    parser.add_argument("--chunk", type=int, default=1200)
    parser.add_argument("--overlap", type=int, default=150)
    parser.add_argument("--batch", type=int, default=128)
    parser.add_argument("--index_path", default="index.faiss")
    parser.add_argument("--meta_path", default="meta.jsonl")
    parser.add_argument("--no_gpu", action="store_true", help="GPU 사용 비활성화 (강제 CPU)")
    parser.add_argument("--no_fp16", action="store_true", help="GPU에서 FP16 클로닝 비활성화")
    # 추가된 옵션(필요 없으면 안 써도 됨)
    parser.add_argument("--max_pages", type=int, default=None, help="처리 최대 페이지 (드라이런용)")
    parser.add_argument("--text_only", action="store_true", help="OCR 생략하고 텍스트만 사용")
    parser.add_argument("--debug", action="store_true", help="자세한 페이지/배치 로그")
    args = parser.parse_args()

    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY 환경변수(.env) 설정 필요")
    # 타임아웃 지정(네트워크 대기시 바로 표시되게)
    client = OpenAI(api_key=api_key, timeout=60.0)

    prefer_gpu = not args.no_gpu
    use_fp16 = not args.no_fp16

    if prefer_gpu and _gpu_available():
        log(f"[GPU] Using FAISS GPU (gpus={faiss.get_num_gpus()}), FP16={use_fp16}")
    else:
        log("[CPU] Using FAISS CPU (GPU unavailable or disabled)")

    p = Path(args.input)
    pdf_files = [p] if p.is_file() else sorted(list(p.rglob("*.pdf")))
    total_added = 0

    for pdf in pdf_files:
        try:
            with stage(f"Process {pdf.name}"):
                blocks = process_pdf(
                    pdf,
                    dpi=args.dpi,
                    ocr_lang=args.ocr_lang,
                    chunk=args.chunk,
                    overlap=args.overlap,
                    max_pages=args.max_pages,
                    text_only=args.text_only,
                    debug=args.debug
                )
                added = upsert_blocks_to_faiss(
                    blocks, client, args.model,
                    args.index_path, args.meta_path,
                    batch=args.batch, dims=args.dimensions,
                    prefer_gpu=prefer_gpu, fp16=use_fp16,
                    debug=args.debug
                )
                total_added += added
                log(f"[OK] {pdf.name}: +{added} chunks indexed")
        except Exception as e:
            log(f"[ERR] {pdf.name}: {type(e).__name__}: {e} (다음 파일 계속)")
            continue

    log(f"Done. Total new chunks indexed: {total_added}")

if __name__ == "__main__":
    # -u로 실행하면 출력 버퍼링 없이 즉시 찍힘
    main()
