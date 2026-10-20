
import io
import json
import threading
import time
import zipfile
from urllib.parse import urlparse

import requests
from PyQt5.QtCore import QThread, pyqtSignal

from data import convert

BASE = "https://cricsheet.org/downloads/"
HEADERS = {"User-Agent": "DSA-Project1-CricketLoader/1.0 (student project)"}
YEARS = range(2026, 2000, -1)     
DELAY = 1.0                      
BATCH = 250                       


class _Stopped(Exception):
    pass


def _name(v):
    """Event can be a dict {'name':..} or a plain string in some files."""
    if isinstance(v, dict):
        return v.get("name", "")
    return v or ""


def parse_match(match_id, d):
    """Turn one Cricsheet JSON match into a 17-value row (None if unusable).
    Fields that do not exist in the source stay empty / 0 - nothing is invented."""
    info = d.get("info") or {}
    dates = info.get("dates") or []
    teams = info.get("teams") or []
    if not dates or len(teams) < 2:
        return None
    toss = info.get("toss") or {}
    outcome = info.get("outcome") or {}
    by = outcome.get("by") or {}

    margin, mtype = 0, ""
    if "runs" in by:
        margin, mtype = by["runs"], "runs"
    elif "wickets" in by:
        margin, mtype = by["wickets"], "wickets"
    elif outcome.get("result"):                 
        mtype = outcome["result"]
    elif outcome.get("eliminator") or outcome.get("bowl_out"):
        mtype = "super over" if outcome.get("eliminator") else "bowl out"

    pom = info.get("player_of_match") or []
    return [
        match_id,
        convert(dates[0], "str"),
        convert(info.get("match_type", ""), "str"),
        convert(info.get("gender", ""), "str"),
        convert(_name(info.get("event")), "str"),
        convert(info.get("venue", ""), "str"),
        convert(info.get("city", ""), "str"),
        convert(teams[0], "str"),
        convert(teams[1], "str"),
        convert(toss.get("winner", ""), "str"),
        convert(toss.get("decision", ""), "str"),
        convert(outcome.get("winner", ""), "str"),
        convert(margin, "int"),
        mtype,
        convert(", ".join(pom), "str"),
        convert(info.get("season", ""), "str"),
        convert(info.get("overs", 0), "int"),
    ]


class ScraperThread(QThread):
    batch = pyqtSignal(list)      
    status = pyqtSignal(str)     
    done = pyqtSignal(str)       

    def __init__(self, existing_keys, needed, url=""):
        super().__init__()
        self.seen = set(existing_keys)
        self.needed = needed
        self.url = url.strip()
        self._running = threading.Event()
        self._running.set()
        self._stop = False

    
    def pause(self):
        self._running.clear()

    def resume(self):
        self._running.set()

    def stop(self):
        self._stop = True
        self._running.set()

    
    def _check(self):
        """Block while paused; raise _Stopped if stop was requested."""
        while not self._running.is_set() and not self._stop:
            self._running.wait(0.2)
        if self._stop:
            raise _Stopped()

    def _sources(self):
        if self.url:
            p = urlparse(self.url)
            if not (p.scheme == "https" and p.netloc == "cricsheet.org"
                    and p.path.startswith("/downloads/") and p.path.endswith(".zip")):
                raise ValueError("Unsupported URL. Only Cricsheet zip files are supported, e.g. "
                                 "https://cricsheet.org/downloads/2024_json.zip "
                                 "(pick one from https://cricsheet.org/downloads/ - JSON column).")
            return [self.url]
        return [f"{BASE}{y}_json.zip" for y in YEARS]

    def _download(self, url):
        """Return a BytesIO with the zip, or None after 3 failed attempts."""
        for attempt in range(3):
            self._check()
            try:
                buf = io.BytesIO()
                with requests.get(url, headers=HEADERS, timeout=(10, 60), stream=True) as r:
                    r.raise_for_status()
                    for chunk in r.iter_content(65536):
                        self._check()
                        buf.write(chunk)
                buf.seek(0)
                return buf
            except _Stopped:
                raise
            except Exception as e:     
                self.status.emit(f"Download failed ({e}); retry {attempt + 1}/3")
                time.sleep(2 * (attempt + 1))
        return None

    def run(self):
        try:
            sources = self._sources()
        except ValueError as e:
            self.done.emit(f"Error: {e}")
            return
        got = 0
        rows = []                                   
        try:
            for url in sources:
                fname = url.rsplit("/", 1)[-1]
                self.status.emit(f"Downloading {fname} ...")
                buf = self._download(url)
                if buf is None:
                    self.status.emit(f"Skipped {fname}: download failed after 3 tries.")
                    continue
                try:
                    zf = zipfile.ZipFile(buf)
                except zipfile.BadZipFile:
                    self.status.emit(f"Skipped {fname}: not a valid zip file.")
                    continue
                new_here, rows = 0, []
                with zf:
                    for n in zf.namelist():
                        if not n.endswith(".json"):
                            continue
                        self._check()
                        mid = n.rsplit("/", 1)[-1][:-5]
                        if mid in self.seen:            # duplicate detection
                            continue
                        try:
                            row = parse_match(mid, json.loads(zf.read(n)))
                        except ValueError:
                            self.status.emit(f"Skipped unreadable file {n}")
                            continue
                        if row is None:
                            continue
                        self.seen.add(mid)
                        rows.append(row)
                        got += 1
                        new_here += 1
                        if len(rows) >= BATCH or got >= self.needed:
                            self.batch.emit(rows)
                            rows = []
                        if got >= self.needed:
                            self.done.emit(f"Target reached. {got} new matches saved.")
                            return
                if rows:
                    self.batch.emit(rows)
                rows = []                            
                self.status.emit(f"{fname}: +{new_here} new matches · {got} total this run")
                time.sleep(DELAY)
        except _Stopped:
            if rows:                                 
                self.batch.emit(rows)
            self.done.emit(f"Stopped. {got} new matches saved.")
            return
        self.done.emit(f"Finished all sources. {got} new matches saved. "
                       "(If this is below your target, the source has no more matches.)")