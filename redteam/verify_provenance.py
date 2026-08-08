#!/usr/bin/env python3
"""
Independent verification of the interaction_events provenance finding.

Run:  python3 verify_provenance.py --key .firestore_key.json

Prints exact document IDs you can open in the Firebase console, plus counts.
Designed to be cheap on reads: uses aggregation counts, then fetches 5 examples.
If this prints zero synthetic records, my finding was wrong and the corrected
manuscript should be discarded.
"""
import argparse, json, os, sys

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--key", default=".firestore_key.json")
    ap.add_argument("--collection", default="interaction_events")
    a = ap.parse_args()
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.path.abspath(a.key)
    from google.cloud import firestore
    from google.cloud.firestore_v1.base_query import FieldFilter
    project = json.load(open(a.key)).get("project_id")
    db = firestore.Client(project=project)
    col = db.collection(a.collection)
    print(f"project = {project}   collection = {a.collection}\n")

    def count(q):
        try: return q.count().get()[0][0].value
        except Exception as e: return f"ERR {e}"

    base = col.where(filter=FieldFilter("event_type", "==", "answer_submitted"))
    total = count(base)
    print(f"answer_submitted total: {total}")
    for tag in ("synthetic_fill", "governed_enriched", "real_performance_data"):
        n = count(base.where(filter=FieldFilter("data._source", "==", tag)))
        pct = f"{n/total*100:.1f}%" if isinstance(n, int) and isinstance(total, int) and total else ""
        print(f"  data._source == {tag:22s} {n}  {pct}")

    print("\n--- example synthetic documents (open these in the console) ---")
    q = base.where(filter=FieldFilter("data._source", "==", "synthetic_fill")).limit(5)
    found = 0
    for d in q.stream():
        found += 1
        doc = d.to_dict(); inner = doc.get("data") or {}
        print(f"\nDOC ID : {d.id}")
        print(f"  console path: {a.collection}/{d.id}")
        print(f"  timestamp   : {doc.get('timestamp')}")
        print(f"  student_id  : {doc.get('student_id')}   subject: {doc.get('subject')}")
        print(f"  data._source: {inner.get('_source')!r}")
        print(f"  data.answer_text : {str(inner.get('answer_text'))[:140]!r}")
        print(f"  data.score       : {inner.get('score')}")
    if found == 0:
        print("\nNO synthetic_fill documents found. The provenance finding does NOT reproduce.")
        sys.exit(1)
    print("\n\nTo confirm in the Firebase console UI:")
    print("  1. Firestore Database > Data > interaction_events")
    print("  2. Open one of the DOC IDs above")
    print("  3. Expand the 'data' field (it is a MAP). '_source' is INSIDE it,")
    print("     not at the top level, so it is not visible until 'data' is expanded.")

if __name__ == "__main__":
    main()
