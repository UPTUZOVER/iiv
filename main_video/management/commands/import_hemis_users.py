import json
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, Iterable, Optional

import requests
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


# ====== HEMIS CONFIG (env shart emas) ======
BASE_URL = "http://172.16.223.205:8088/api"
LOGIN = "superadmin"
PASSWORD = "12345"

STUDENTS_ENDPOINT = "/hemis/students"
TEACHERS_ENDPOINT = "/hemis/teacher"

TIMEOUT = 300
PAGE_SIZE_STUDENTS = 200
PAGE_SIZE_TEACHERS = 200

GREEN = "\033[92m"
RED = "\033[91m"
RESET = "\033[0m"


def _json_loads_maybe(value: Any) -> Optional[Dict[str, Any]]:
    """HEMIS image fields can be JSON-string, dict, '', or '\"\"'."""
    if value is None:
        return None
    if isinstance(value, dict):
        return value
    if not isinstance(value, str):
        return None
    s = value.strip()
    if not s or s == '""':
        return None
    try:
        obj = json.loads(s)
        return obj if isinstance(obj, dict) else None
    except Exception:
        return None


def _build_img_url(img_obj: Optional[Dict[str, Any]]) -> Optional[str]:
    """base_url + '/' + path -> full URL"""
    if not img_obj:
        return None
    base_url = (img_obj.get("base_url") or "").strip()
    path = (img_obj.get("path") or "").strip()
    if not base_url or not path:
        return None
    return f"{base_url.rstrip('/')}/{path.lstrip('/')}"


def _safe_decimal(v: Any) -> Decimal:
    if v is None or v == "":
        return Decimal("0")
    try:
        return Decimal(str(v))
    except (InvalidOperation, ValueError):
        return Decimal("0")


def _fio(first: str, second: str, third: str) -> str:
    parts = [(second or "").strip(), (first or "").strip(), (third or "").strip()]
    fio = " ".join([p for p in parts if p])
    return fio.strip() or "NO_NAME"


class Command(BaseCommand):
    help = "Import HEMIS Students/Teachers into local Users. Prints ✅ / ❌ per record."

    def add_arguments(self, parser):
        parser.add_argument("--only", choices=["students", "teachers", "both"], default="both")
        parser.add_argument("--reset-passwords", action="store_true", help="existing userlarda ham passwordni set qiladi")
        parser.add_argument("--dry-run", action="store_true", help="DBga yozmaydi, faqat log")

    # ---------- HTTP ----------
    def _api_login(self, session: requests.Session) -> str:
        url = f"{BASE_URL}/auth/login"
        r = session.post(url, params={"login": LOGIN, "password": PASSWORD}, headers={"accept": "*/*"}, timeout=TIMEOUT)
        r.raise_for_status()
        token = r.json().get("token")
        if not token:
            raise RuntimeError("HEMIS login: token qaytmadi")
        return token

    def _fetch_pages(self, session: requests.Session, url: str, headers: Dict[str, str], page_size: int) -> Iterable[Dict[str, Any]]:
        curr = 1
        total = None
        while True:
            r = session.get(
                url,
                headers=headers,
                params={"currPage": curr, "size": page_size, "descending": "false", "order_by_": "id"},
                timeout=TIMEOUT,
            )
            r.raise_for_status()
            payload = r.json()

            if total is None:
                total = int(payload.get("total") or 0)

            rows = payload.get("rows") or []
            if not rows:
                break

            for row in rows:
                if isinstance(row, dict):
                    yield row

            if curr * page_size >= total:
                break
            curr += 1

    # ---------- CORE UPSERT ----------
    def _upsert(
        self,
        *,
        User,
        hemis_id: str,
        role: str,
        group: Optional[str],
        first_name: Optional[str],
        last_name: Optional[str],
        third_name: Optional[str],
        kurs: Optional[str],
        avg_mark: Optional[Decimal],
        img_url: Optional[str],
        reset_passwords: bool,
        dry_run: bool,
    ):
        """
        Important fixes:
        - username UNIQUE -> username = hemis_id
        - USERNAME_FIELD = hemis_id -> create is fine, but username must be unique too
        """
        user = User.objects.filter(hemis_id=hemis_id).first()
        created = user is None
        if created:
            user = User(hemis_id=hemis_id)

        # MUST: unique username
        user.username = hemis_id

        # only your model fields:
        user.role = role
        user.group = (group[:30] if group else None)
        user.first_name = first_name or None
        user.last_name = last_name or None
        user.third_name = third_name or None

        if role == "student":
            user.kurs = kurs or None
            user.avg_mark = avg_mark if avg_mark is not None else Decimal("0")

        # imgage URL saqlanadi (model: URLField/CharField bo‘lishi shart)
        if img_url:
            user.imgage = img_url

        if created or reset_passwords:
            user.set_password(hemis_id)

        if not dry_run:
            user.save()

        return created

    def handle(self, *args, **options):
        only = options["only"]
        reset_passwords = options["reset_passwords"]
        dry_run = options["dry_run"]

        User = get_user_model()
        session = requests.Session()
        token = self._api_login(session)
        headers = {"accept": "*/*", "Authorization": f"Bearer {token}"}

        created_count = 0
        updated_count = 0
        error_count = 0
        skipped_count = 0

        # ---------- STUDENTS ----------
        if only in ("students", "both"):
            url = f"{BASE_URL}{STUDENTS_ENDPOINT}"
            for row in self._fetch_pages(session, url, headers, PAGE_SIZE_STUDENTS):
                hemis_id = (row.get("student_id_number") or "").strip()
                fio = _fio(row.get("first_name"), row.get("second_name"), row.get("third_name"))

                if not hemis_id:
                    skipped_count += 1
                    print(f"{RED}✗{RESET} [student] SKIP(no hemis_id) {fio}")
                    continue

                try:
                    img_obj = _json_loads_maybe(row.get("image"))
                    img_url = _build_img_url(img_obj)

                    created = self._upsert(
                        User=User,
                        hemis_id=hemis_id,
                        role="student",
                        group=(row.get("group_name") or "").strip(),
                        first_name=(row.get("first_name") or "").strip(),
                        last_name=(row.get("second_name") or "").strip(),
                        third_name=(row.get("third_name") or "").strip(),
                        kurs=(row.get("course") or "").strip(),
                        avg_mark=_safe_decimal(row.get("avg_mark")),
                        img_url=img_url,
                        reset_passwords=reset_passwords,
                        dry_run=dry_run,
                    )

                    if created:
                        created_count += 1
                        print(f"{GREEN}✓{RESET} [student][CREATED] {fio} | hemis_id={hemis_id}")
                    else:
                        updated_count += 1
                        print(f"{GREEN}✓{RESET} [student][UPDATED] {fio} | hemis_id={hemis_id}")

                except Exception as e:
                    error_count += 1
                    print(f"{RED}✗{RESET} [student][ERROR] {fio} | hemis_id={hemis_id} | {e}")

        # ---------- TEACHERS ----------
        if only in ("teachers", "both"):
            url = f"{BASE_URL}{TEACHERS_ENDPOINT}"
            for row in self._fetch_pages(session, url, headers, PAGE_SIZE_TEACHERS):
                raw = row.get("employee_id_number")
                hemis_id = raw.strip() if isinstance(raw, str) else ""
                fio = _fio(row.get("first_name"), row.get("second_name"), row.get("third_name"))

                if not hemis_id:
                    skipped_count += 1
                    print(f"{RED}✗{RESET} [teacher] SKIP(no hemis_id) {fio}")
                    continue

                try:
                    img_obj = _json_loads_maybe(row.get("employee_img"))
                    img_url = _build_img_url(img_obj)

                    created = self._upsert(
                        User=User,
                        hemis_id=hemis_id,
                        role="teacher",
                        group=(row.get("department_name") or "").strip(),
                        first_name=(row.get("first_name") or "").strip(),
                        last_name=(row.get("second_name") or "").strip(),
                        third_name=(row.get("third_name") or "").strip(),
                        kurs=None,
                        avg_mark=None,
                        img_url=img_url,
                        reset_passwords=reset_passwords,
                        dry_run=dry_run,
                    )

                    if created:
                        created_count += 1
                        print(f"{GREEN}✓{RESET} [teacher][CREATED] {fio} | hemis_id={hemis_id}")
                    else:
                        updated_count += 1
                        print(f"{GREEN}✓{RESET} [teacher][UPDATED] {fio} | hemis_id={hemis_id}")

                except Exception as e:
                    error_count += 1
                    print(f"{RED}✗{RESET} [teacher][ERROR] {fio} | hemis_id={hemis_id} | {e}")

        print("\n==== SUMMARY ====")
        print(f"Created: {created_count}")
        print(f"Updated: {updated_count}")
        print(f"Skipped: {skipped_count}")
        print(f"Errors:  {error_count}")
        if dry_run:
            print("DRY-RUN: DBga yozilmadi.")
