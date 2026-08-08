#!/usr/bin/env python3
"""
Pull the GenAITS quiz knowledge base (question / correct answer / rubric) from
Cloud Firestore and write items.csv for the red-team harness.

SAFETY: use a READ-ONLY service account (roles/datastore.viewer). This script only
reads the collection you name; it never writes and never touches other collections.
Point it only at the quiz/question store, NOT the student-interaction (PII) store.

Step 1 - discover structure (find the right collection and field names):
  python3 fetch_items_firestore.py --key .firestore_key.json --discover

Step 2 - export items.csv once you know the collection + fields:
  python3 fetch_items_firestore.py --key .firestore_key.json \
      --collection quiz_questions \
      --map question=questionText,correct_answer=answer,rubric=rubric,subject=courseCode \
      --out items.csv
"""
import argparse, csv, json, os, sys

def load_db(key_path):
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.path.abspath(key_path)
    from google.cloud import firestore
    with open(key_path, encoding="utf-8") as f:
        project = json.load(f).get("project_id")
    return firestore.Client(project=project)

def trunc(v, n=70):
    s = v if isinstance(v, str) else json.dumps(v, default=str)
    s = s.replace("\n", " ")
    return s[:n] + ("..." if len(s) > n else "")

def discover(db, sample=2):
    print("Top-level collections (name : approx sample, field names):\n")
    for col in db.collections():
        docs = list(col.limit(sample).stream())
        print(f"[{col.id}]  ({len(docs)}+ docs sampled)")
        for d in docs:
            data = d.to_dict() or {}
            print(f"  doc {d.id}: fields = {list(data.keys())}")
            for k, v in data.items():
                print(f"      {k}: {trunc(v)}")
            # surface subcollections if any
            subs = [s.id for s in d.reference.collections()]
            if subs:
                print(f"      (subcollections: {subs})")
        print()
    print("Next: pick the collection holding questions and map its fields with --map.")

def _s(v):
    if v in (None, ""): return ""
    return v if isinstance(v, str) else json.dumps(v, default=str)

def export(db, path, mapping, out, array_field=None, exclude_subject=None):
    """mapping keys: question, correct_answer, rubric, subject, item_id.
    In array mode, field names refer to keys inside each array element, except
    values prefixed 'parent.' which refer to the parent document."""
    fields = dict(kv.split("=", 1) for kv in mapping.split(","))
    for req in ("question", "correct_answer", "rubric"):
        if req not in fields:
            sys.exit(f"--map must include {req}=<field>")
    excl = set((exclude_subject or "").split(",")) - {""}
    rows = []
    for d in db.collection(path).stream():
        data = d.to_dict() or {}
        elements = (data.get(array_field) or []) if array_field else [data]
        for idx, el in enumerate(elements):
            def get(key):
                fv = fields.get(key, "")
                if fv.startswith("parent."):
                    return _s(data.get(fv[len("parent."):]))
                src = el if array_field else data
                return _s(src.get(fv)) if fv else ""
            subj = get("subject")
            if subj in excl:
                continue
            iid = (f"{d.id}#{el.get('id', idx)}" if array_field else (get("item_id") or d.id))
            rows.append({"item_id": iid, "subject": subj, "question": get("question"),
                         "correct_answer": get("correct_answer"), "rubric": get("rubric")})
    rows = [r for r in rows if r["question"] and r["correct_answer"]]
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["item_id", "subject", "question", "correct_answer", "rubric"])
        w.writeheader(); w.writerows(rows)
    print(f"Wrote {len(rows)} items to {out}")
    bysub = {}
    for r in rows: bysub[r["subject"]] = bysub.get(r["subject"], 0) + 1
    print("by subject:", bysub)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--key", required=True, help="path to read-only service-account JSON")
    ap.add_argument("--discover", action="store_true")
    ap.add_argument("--collection", help="collection path holding question bundles")
    ap.add_argument("--map", help="field mapping, e.g. question=question,correct_answer=answer,rubric=answer,subject=parent.subject")
    ap.add_argument("--array-field", default=None, help="doc field holding an array of questions (e.g. questions)")
    ap.add_argument("--exclude-subject", default=None, help="comma-separated subjects to drop (e.g. COMPTEST)")
    ap.add_argument("--out", default="items.csv")
    args = ap.parse_args()
    db = load_db(args.key)
    if args.discover:
        discover(db)
    elif args.collection and args.map:
        export(db, args.collection, args.map, args.out, args.array_field, args.exclude_subject)
    else:
        sys.exit("Use --discover, or provide both --collection and --map.")

if __name__ == "__main__":
    main()
