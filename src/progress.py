import json
from pathlib import Path

class ProgressTracker:
    def __init__(self, log_dir):
        self.progress_file = Path(log_dir) / "progress.json"
        self.progress = self._load()

    def _load(self):
        if self.progress_file.exists():
            with open(self.progress_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {"last_processed_index": -1, "processed_urls": []}

    def save(self):
        with open(self.progress_file, 'w', encoding='utf-8') as f:
            json.dump(self.progress, f, ensure_ascii=False, indent=2)

    def get_last_index(self):
        return self.progress.get("last_processed_index", -1)

    def update_index(self, index):
        self.progress["last_processed_index"] = index
        self.save()

    def add_processed_url(self, url):
        if url not in self.progress["processed_urls"]:
            self.progress["processed_urls"].append(url)
            self.save()
