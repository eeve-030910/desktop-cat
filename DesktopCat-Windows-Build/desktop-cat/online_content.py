"""Trusted HTTPS metadata, version gate and data-only free character packages."""
import hashlib
import io
import json
import re
import shutil
import tempfile
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler
import zipfile

APP_VERSION = "0.4.5"
FILES = {*(f"cat_{i}.png" for i in range(4)), "cat_sleep.png"}


def version(value):
    if not isinstance(value, str) or not re.fullmatch(r"\d{1,5}\.\d{1,5}\.\d{1,5}", value):
        raise ValueError("バージョンの形式が不正です")
    return tuple(map(int, value.split(".")))


def allowed_url(url, hosts):
    p = urlsplit(url)
    if (p.scheme != "https" or not p.hostname or p.hostname not in hosts
            or p.username or p.password or p.port not in (None, 443) or p.fragment):
        raise ValueError("許可されたHTTPS配布先ではありません")
    return url


class TrustedRedirects(HTTPRedirectHandler):
    def __init__(self, hosts):
        super().__init__()
        self.hosts = hosts

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        allowed_url(newurl, self.hosts)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch(url, hosts, limit=262144):
    allowed_url(url, hosts)
    opener = build_opener(TrustedRedirects(hosts))
    req = Request(url, headers={"User-Agent": f"DesktopCat/{APP_VERSION}",
                                "Cache-Control": "no-cache"})
    with opener.open(req, timeout=8) as response:
        allowed_url(response.url, hosts)
        data = response.read(limit + 1)
    if len(data) > limit:
        raise ValueError("配布データが上限を超えています")
    return data


def check_policy(policy, hosts, current=APP_VERSION):
    if not isinstance(policy, dict) or policy.get("schema") != 1:
        raise ValueError("更新情報の形式が不正です")
    minimum = version(policy["minimum_version"])
    latest = version(policy["latest_version"])
    if latest < minimum:
        raise ValueError("最新版と最低対応版の設定が矛盾しています")
    allowed_url(policy["download_url"], hosts)
    allowed_url(policy["catalog_url"], hosts)
    return version(current) >= minimum


def load_policy(config):
    hosts = config.get("allowed_hosts", [])
    if not config.get("policy_url") or not hosts:
        raise ValueError("更新サーバーが未設定です。配布者がオンライン設定を行う必要があります。")
    policy = json.loads(fetch(config["policy_url"], hosts))
    return policy, check_policy(policy, hosts)


def catalog_entries(data, hosts, current=APP_VERSION):
    if not isinstance(data, dict) or data.get("schema") != 1:
        raise ValueError("キャラ一覧の形式が不正です")
    entries = data.get("characters")
    if not isinstance(entries, list) or len(entries) > 100:
        raise ValueError("キャラ一覧の件数が不正です")
    result = []
    seen = set()
    for item in entries:
        ident = item.get("id", "")
        if not re.fullmatch(r"[a-z0-9_-]{1,48}", ident) or ident in seen or ident == "tabby_cat":
            raise ValueError("キャラIDが不正または重複しています")
        seen.add(ident)
        if not isinstance(item.get("name"), str) or not 1 <= len(item["name"]) <= 50:
            raise ValueError("キャラ名が不正です")
        if item.get("free") is not True:
            raise ValueError("このアプリでは無料キャラだけを配布します")
        if version(item["minimum_app_version"]) > version(current):
            continue
        allowed_url(item["url"], hosts)
        if not re.fullmatch(r"[a-f0-9]{64}", item.get("sha256", "")):
            raise ValueError("素材の検証情報が不正です")
        result.append(item)
    return result


def install_character(item, raw, root):
    if len(raw) > 10*1024*1024 or hashlib.sha256(raw).hexdigest() != item["sha256"]:
        raise ValueError("素材のハッシュ検証に失敗しました")
    ident = item["id"]
    if not re.fullmatch(r"[a-z0-9_-]{1,48}", ident):
        raise ValueError("キャラIDが不正です")
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    destination = root / (ident + "-" + item["sha256"][:16])
    with tempfile.TemporaryDirectory(dir=root) as temporary:
        staging = Path(temporary) / "package"
        staging.mkdir()
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            names = archive.namelist()
            if len(names) != len(FILES) or set(names) != FILES:
                raise ValueError("素材ZIPには指定のPNG画像5枚だけを含めてください")
            for info in archive.infolist():
                if info.file_size > 2*1024*1024 or info.flag_bits & 1:
                    raise ValueError("画像が大きすぎるか暗号化されています")
                # Never extract archive paths; write only fixed allowlisted names.
                image_data = archive.read(info)
                if not image_data.startswith(b"\x89PNG\r\n\x1a\n"):
                    raise ValueError("PNG以外の素材は利用できません")
                from PySide6.QtGui import QImage
                image = QImage.fromData(image_data, "PNG")
                if image.isNull() or image.width() != 128 or image.height() != 96:
                    raise ValueError("素材画像は128×96のPNGにしてください")
                (staging / info.filename).write_bytes(image_data)
        (staging / "character.json").write_text(
            json.dumps({"id": ident, "name": item["name"]}, ensure_ascii=False), encoding="utf-8")
        if not destination.exists():
            shutil.move(str(staging), str(destination))
    return destination
