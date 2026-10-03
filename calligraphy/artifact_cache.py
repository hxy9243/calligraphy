"""Versioned SQLite storage for portable JSON geometry snapshots.

Snapshots keep their original schema and provenance. Importing a legacy artifact
never claims it was fitted by the current engine. Explicit content IDs select
versions, so importing startup seeds cannot overwrite a locally fitted revision.
"""
import argparse
from contextlib import closing
from hashlib import sha256
import json
from pathlib import Path
import sqlite3


def encoded(document):
    if not isinstance(document, dict) or not isinstance(document.get('schemaVersion'), (str, int)):
        raise ValueError('Artifact must be a JSON object with schemaVersion')
    return json.dumps(document, sort_keys=True, ensure_ascii=False, allow_nan=False, indent=2) + '\n'


class ArtifactCache:
    def __init__(self, path, snapshots=()):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute('''CREATE TABLE IF NOT EXISTS geometry_artifacts (
                name TEXT NOT NULL, content_id TEXT NOT NULL, document_json TEXT NOT NULL,
                PRIMARY KEY (name, content_id))''')
        # Startup imports are idempotent and additive. Missing/bad seeds fail visibly.
        for name, snapshot in snapshots:
            self.import_json(name, snapshot)

    def put(self, name, document):
        if not isinstance(name, str) or not name.strip():
            raise ValueError('Artifact name must be nonempty')
        payload = encoded(document)
        content_id = sha256(payload.encode()).hexdigest()
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute('INSERT OR IGNORE INTO geometry_artifacts VALUES (?, ?, ?)',
                       (name, content_id, payload))
        return content_id

    def get(self, name, content_id=None):
        with closing(sqlite3.connect(self.path)) as db, db:
            if content_id is None:
                rows = db.execute('SELECT content_id, document_json FROM geometry_artifacts WHERE name=?', (name,)).fetchall()
                if len(rows) > 1:
                    raise ValueError('Multiple artifact versions; supply content_id')
                row = rows[0] if rows else None
            else:
                row = db.execute('SELECT content_id, document_json FROM geometry_artifacts WHERE name=? AND content_id=?',
                                 (name, content_id)).fetchone()
        if row is None:
            raise KeyError(name)
        if sha256(row[1].encode()).hexdigest() != row[0]:
            raise ValueError('Artifact checksum mismatch')
        return json.loads(row[1])

    def import_json(self, name, path):
        return self.put(name, json.loads(Path(path).read_text()))

    def export_json(self, name, path, content_id=None):
        Path(path).write_text(encoded(self.get(name, content_id)), encoding='utf-8')

    def list_versions(self):
        with closing(sqlite3.connect(self.path)) as db, db:
            return [dict(zip(('name', 'content_id'), row)) for row in
                    db.execute('SELECT name, content_id FROM geometry_artifacts ORDER BY name, content_id')]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', required=True)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('list')
    for action in ('import', 'export'):
        item = sub.add_parser(action)
        item.add_argument('name')
        item.add_argument('path')
        if action == 'export':
            item.add_argument('--content-id')
    args = parser.parse_args()
    cache = ArtifactCache(args.db)
    if args.command == 'import':
        print(cache.import_json(args.name, args.path))
    elif args.command == 'export':
        cache.export_json(args.name, args.path, args.content_id)
    else:
        print(json.dumps(cache.list_versions(), indent=2))


if __name__ == '__main__':
    main()
