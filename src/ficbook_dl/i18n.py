"""Interface strings for English, Russian, and Ukrainian."""

from __future__ import annotations

import locale
from pathlib import Path

TEXT: dict[str, dict[str, str | tuple[str, str, str]]] = {
    "en": {
        "window_title": "Ficbook Downloader",
        "menu_edit": "Edit",
        "menu_undo": "Undo",
        "menu_cut": "Cut",
        "menu_copy": "Copy",
        "menu_paste": "Paste",
        "menu_select_all": "Select All",
        "paste": "Paste",
        "clear": "Clear",
        "open_folder": "Open folder",
        "links_count": ("{n} link", "{n} links", "{n} links"),
        "downloading_n": "Downloading {i} of {n}…",
        "shortcut_hint": "{keys} to start",
        "library_empty": "Paste an author link above and press Show books.",
        "nav_settings": "Settings",
        "open_files": "Open saved files",
        "share": "Share",
        "saved_files": "Saved files",
        "check_title": "Check on ficbook",
        "check_body": "Finish the check on this page. Downloading continues on its own.",
        "age_body": "Confirm your age on this page, then tap Continue.",
        "continue": "Continue",
        "cancel": "Cancel",
        "load_failed": "Couldn't open {url}. Check your connection and try again.",
        "files_location_ios": "Files are saved in Files › On My iPhone › Ficbook.",
        "files_location_android": "Files are saved in Downloads › Ficbook.",
        "details_log": "Details",
        "about_body_phone": "A small app for saving stories from ficbook.net on your phone as txt, EPUB, or FB2.",
        "language": "Language",
        "story_links": "Story links",
        "one_per_line": "one link per line",
        "hint": "Paste story links here, one per line\nhttps://ficbook.net/readfic/…",
        "save_to": "Save to",
        "browse": "Browse",
        "formats": "Formats",
        "pause": "Pause (seconds)",
        "download": "Download",
        "downloaded": "Downloaded",
        "saving": "Saving…",
        "stop": "Stop",
        "status_idle": "Paste one or more story links.",
        "need_link": "Paste at least one story link.",
        "need_format": "Choose at least one format.",
        "pause_number": "Pause must be a number.",
        "pause_negative": "Pause cannot be negative.",
        "downloading": "Downloading…",
        "saving_to": "Saving {formats} to {folder}",
        "stopped": "Stopped.",
        "error_line": "error: {message}",
        "saved_path": "saved {path}",
        "saved_line": "saved {path} ({count} chapters)",
        "saved_stories": ("Saved {n} story.", "Saved {n} stories.", "Saved {n} stories."),
        "failed_stories": ("{n} failed.", "{n} failed.", "{n} failed."),
        "author": "Author",
        "translator": "Translator",
        "series": "Series",
        "fandom": "Fandom",
        "direction": "Direction",
        "characters": "Characters",
        "tags": "Tags",
        "dedication": "Dedication",
        "notes": "Notes",
        "chapter": "Chapter",
        "empty_link": "Pass a ficbook story link, like https://ficbook.net/readfic/12345.",
        "not_ficbook": "Not a ficbook story link: {value}",
        "age_check": "Ficbook is showing an age check instead of the text for {url}",
        "missing_story": "No chapters or text found at {url}",
        "missing_chapter": "No chapter text at {url}",
        "security_check": "Ficbook returned a security check instead of the story page.",
        "cli_description": "Save ficbook.net stories as txt, EPUB, and FB2 files.",
        "cli_links": "Story links or ids, for example https://ficbook.net/readfic/12345",
        "cli_out": "Directory for the files (default: stories)",
        "cli_delay": "Seconds to wait between requests (default: 1.5)",
        "cli_format": "Comma-separated formats: txt, epub, fb2 (default: all three)",
        "cli_gui": "Open the Mac and Windows window",
        "cli_lang": "Interface language: en, ru, or uk",
        "cli_need_link": "pass at least one story link, or use --gui",
        "cli_bad_format": "Formats are txt, epub, and fb2.",
        "nav_download": "Download",
        "nav_library": "Library",
        "nav_about": "About",
        "library_title": "An author's books",
        "library_hint": "https://ficbook.net/authors/…",
        "show_books": "Show books",
        "preview": "Preview",
        "close": "Close",
        "no_series": "Not part of a series",
        "no_cover": "No cover",
        "loading": "Loading…",
        "books_count": "{n} books",
        "need_author": "Paste an author link, like https://ficbook.net/authors/2.",
        "not_author": "Not a ficbook author link: {value}",
        "about_role": "Creator of this app",
        "about_body": "A small app for saving stories from ficbook.net on a Mac or a Windows PC.",
        "open_github": "Open GitHub",
        "creator_name": "Yaroslau Hatalski",
    },
    "ru": {
        "window_title": "Ficbook Downloader",
        "menu_edit": "Правка",
        "menu_undo": "Отменить",
        "menu_cut": "Вырезать",
        "menu_copy": "Копировать",
        "menu_paste": "Вставить",
        "menu_select_all": "Выбрать всё",
        "paste": "Вставить",
        "clear": "Очистить",
        "open_folder": "Открыть папку",
        "links_count": ("{n} ссылка", "{n} ссылки", "{n} ссылок"),
        "downloading_n": "Скачивание: {i} из {n}…",
        "shortcut_hint": "{keys} — начать",
        "library_empty": "Вставьте ссылку на автора выше и нажмите «Показать книги».",
        "nav_settings": "Настройки",
        "open_files": "Открыть сохранённые",
        "share": "Поделиться",
        "saved_files": "Сохранённые файлы",
        "check_title": "Проверка на ficbook",
        "check_body": "Пройдите проверку на этой странице. Скачивание продолжится само.",
        "age_body": "Подтвердите возраст на этой странице и нажмите «Продолжить».",
        "continue": "Продолжить",
        "cancel": "Отмена",
        "load_failed": "Не удалось открыть {url}. Проверьте подключение и попробуйте ещё раз.",
        "files_location_ios": "Файлы сохраняются в «Файлы › На iPhone › Ficbook».",
        "files_location_android": "Файлы сохраняются в «Загрузки › Ficbook».",
        "details_log": "Подробности",
        "about_body_phone": "Небольшое приложение, чтобы сохранять работы с ficbook.net на телефон в txt, EPUB или FB2.",
        "language": "Язык",
        "story_links": "Ссылки на работы",
        "one_per_line": "по одной ссылке в строке",
        "hint": "Вставьте ссылки на работы, по одной в строке\nhttps://ficbook.net/readfic/…",
        "save_to": "Сохранить в",
        "browse": "Обзор",
        "formats": "Форматы",
        "pause": "Пауза (секунды)",
        "download": "Скачать",
        "downloaded": "Скачано",
        "saving": "Сохраняю…",
        "stop": "Стоп",
        "status_idle": "Вставьте одну или несколько ссылок.",
        "need_link": "Вставьте хотя бы одну ссылку на работу.",
        "need_format": "Выберите хотя бы один формат.",
        "pause_number": "Пауза должна быть числом.",
        "pause_negative": "Пауза не может быть отрицательной.",
        "downloading": "Скачивание…",
        "saving_to": "Сохраняю {formats} в {folder}",
        "stopped": "Остановлено.",
        "error_line": "ошибка: {message}",
        "saved_path": "сохранено {path}",
        "saved_line": "сохранено {path} ({count} глав)",
        "saved_stories": ("Сохранена {n} работа.", "Сохранено {n} работы.", "Сохранено {n} работ."),
        "failed_stories": ("{n} ошибка.", "{n} ошибки.", "{n} ошибок."),
        "author": "Автор",
        "translator": "Переводчик",
        "series": "Серия",
        "fandom": "Фэндом",
        "direction": "Направленность",
        "characters": "Персонажи",
        "tags": "Метки",
        "dedication": "Посвящение",
        "notes": "Примечания",
        "chapter": "Глава",
        "empty_link": "Нужна ссылка на работу, например https://ficbook.net/readfic/12345.",
        "not_ficbook": "Это не ссылка на работу ficbook: {value}",
        "age_check": "Вместо текста ficbook показывает проверку возраста: {url}",
        "missing_story": "На странице нет частей и текста: {url}",
        "missing_chapter": "На странице нет текста части: {url}",
        "security_check": "Ficbook вернул проверку безопасности вместо страницы работы.",
        "cli_description": "Сохраняет работы с ficbook.net в txt, EPUB и FB2.",
        "cli_links": "Ссылки или номера работ, например https://ficbook.net/readfic/12345",
        "cli_out": "Папка для файлов (по умолчанию stories)",
        "cli_delay": "Пауза между запросами в секундах (по умолчанию 1.5)",
        "cli_format": "Форматы через запятую: txt, epub, fb2 (по умолчанию все три)",
        "cli_gui": "Открыть окно для macOS и Windows",
        "cli_lang": "Язык интерфейса: en, ru или uk",
        "cli_need_link": "передайте хотя бы одну ссылку или используйте --gui",
        "cli_bad_format": "Доступные форматы: txt, epub и fb2.",
        "nav_download": "Скачать",
        "nav_library": "Библиотека",
        "nav_about": "Об авторе",
        "library_title": "Книги автора",
        "library_hint": "https://ficbook.net/authors/…",
        "show_books": "Показать книги",
        "preview": "Превью",
        "close": "Закрыть",
        "no_series": "Не входит в серию",
        "no_cover": "Нет обложки",
        "loading": "Загрузка…",
        "books_count": "Книг: {n}",
        "need_author": "Вставьте ссылку на автора, например https://ficbook.net/authors/2.",
        "not_author": "Это не ссылка на автора ficbook: {value}",
        "about_role": "Создатель этой программы",
        "about_body": "Небольшая программа, чтобы сохранять рассказы с ficbook.net на Mac или Windows.",
        "open_github": "Открыть GitHub",
        "creator_name": "Yaroslau Hatalski",
    },
    "uk": {
        "window_title": "Ficbook Downloader",
        "menu_edit": "Правка",
        "menu_undo": "Скасувати",
        "menu_cut": "Вирізати",
        "menu_copy": "Копіювати",
        "menu_paste": "Вставити",
        "menu_select_all": "Вибрати все",
        "paste": "Вставити",
        "clear": "Очистити",
        "open_folder": "Відкрити теку",
        "links_count": ("{n} посилання", "{n} посилання", "{n} посилань"),
        "downloading_n": "Завантаження: {i} з {n}…",
        "shortcut_hint": "{keys} — почати",
        "library_empty": "Вставте посилання на автора вище й натисніть «Показати книги».",
        "nav_settings": "Налаштування",
        "open_files": "Відкрити збережені",
        "share": "Поділитися",
        "saved_files": "Збережені файли",
        "check_title": "Перевірка на ficbook",
        "check_body": "Пройдіть перевірку на цій сторінці. Завантаження продовжиться саме.",
        "age_body": "Підтвердіть вік на цій сторінці й натисніть «Продовжити».",
        "continue": "Продовжити",
        "cancel": "Скасувати",
        "load_failed": "Не вдалося відкрити {url}. Перевірте з'єднання і спробуйте ще раз.",
        "files_location_ios": "Файли зберігаються у «Файли › На iPhone › Ficbook».",
        "files_location_android": "Файли зберігаються в «Завантаження › Ficbook».",
        "details_log": "Подробиці",
        "about_body_phone": "Невеликий застосунок, щоб зберігати роботи з ficbook.net на телефон у txt, EPUB або FB2.",
        "language": "Мова",
        "story_links": "Посилання на роботи",
        "one_per_line": "по одному посиланню в рядку",
        "hint": "Вставте посилання на роботи, по одному в рядок\nhttps://ficbook.net/readfic/…",
        "save_to": "Зберегти в",
        "browse": "Огляд",
        "formats": "Формати",
        "pause": "Пауза (секунди)",
        "download": "Завантажити",
        "downloaded": "Завантажено",
        "saving": "Зберігаю…",
        "stop": "Зупинити",
        "status_idle": "Вставте одне або кілька посилань.",
        "need_link": "Вставте хоча б одне посилання на роботу.",
        "need_format": "Оберіть хоча б один формат.",
        "pause_number": "Пауза має бути числом.",
        "pause_negative": "Пауза не може бути від'ємною.",
        "downloading": "Завантаження…",
        "saving_to": "Зберігаю {formats} до {folder}",
        "stopped": "Зупинено.",
        "error_line": "помилка: {message}",
        "saved_path": "збережено {path}",
        "saved_line": "збережено {path} ({count} розділів)",
        "saved_stories": ("Збережено {n} роботу.", "Збережено {n} роботи.", "Збережено {n} робіт."),
        "failed_stories": ("{n} помилка.", "{n} помилки.", "{n} помилок."),
        "author": "Автор",
        "translator": "Перекладач",
        "series": "Серія",
        "fandom": "Фендом",
        "direction": "Спрямованість",
        "characters": "Персонажі",
        "tags": "Мітки",
        "dedication": "Присвята",
        "notes": "Примітки",
        "chapter": "Розділ",
        "empty_link": "Потрібне посилання на роботу, наприклад https://ficbook.net/readfic/12345.",
        "not_ficbook": "Це не посилання на роботу ficbook: {value}",
        "age_check": "Замість тексту ficbook показує перевірку віку: {url}",
        "missing_story": "На сторінці немає частин і тексту: {url}",
        "missing_chapter": "На сторінці немає тексту частини: {url}",
        "security_check": "Ficbook повернув перевірку безпеки замість сторінки роботи.",
        "cli_description": "Зберігає роботи з ficbook.net у txt, EPUB і FB2.",
        "cli_links": "Посилання або номери робіт, наприклад https://ficbook.net/readfic/12345",
        "cli_out": "Тека для файлів (типово stories)",
        "cli_delay": "Пауза між запитами в секундах (типово 1.5)",
        "cli_format": "Формати через кому: txt, epub, fb2 (типово всі три)",
        "cli_gui": "Відкрити вікно для macOS і Windows",
        "cli_lang": "Мова інтерфейсу: en, ru або uk",
        "cli_need_link": "передайте хоча б одне посилання або скористайтеся --gui",
        "cli_bad_format": "Доступні формати: txt, epub і fb2.",
        "nav_download": "Завантажити",
        "nav_library": "Бібліотека",
        "nav_about": "Про автора",
        "library_title": "Книги автора",
        "library_hint": "https://ficbook.net/authors/…",
        "show_books": "Показати книги",
        "preview": "Перегляд",
        "close": "Закрити",
        "no_series": "Не входить до серії",
        "no_cover": "Немає обкладинки",
        "loading": "Завантаження…",
        "books_count": "Книг: {n}",
        "need_author": "Вставте посилання на автора, наприклад https://ficbook.net/authors/2.",
        "not_author": "Це не посилання на автора ficbook: {value}",
        "about_role": "Творець цієї програми",
        "about_body": "Невелика програма, щоб зберігати твори з ficbook.net на Mac або Windows.",
        "open_github": "Відкрити GitHub",
        "creator_name": "Yaroslau Hatalski",
    },
}

CHOICES = (("en", "English"), ("ru", "Русский"), ("uk", "Українська"))
_ALIASES = {"ua": "uk", "eng": "en", "english": "en", "russian": "ru", "ukrainian": "uk"}
_PREF = Path.home() / ".config" / "ficbook-downloader" / "language"


def t(language: str, key: str, **params) -> str:
    value = _catalog(language).get(key) or TEXT["en"][key]
    if not isinstance(value, str):
        raise KeyError(key)
    return value.format(**params) if params else value


def tn(language: str, key: str, n: int, **params) -> str:
    forms = _catalog(language).get(key) or TEXT["en"][key]
    if not isinstance(forms, tuple):
        raise KeyError(key)
    if _code(language) == "en":
        form = forms[0] if n == 1 else forms[1]
    else:
        form = forms[_slavic_index(n)]
    return form.format(n=n, **params)


def saved_status(language: str, saved: int, failed: int) -> str:
    text = tn(language, "saved_stories", saved)
    if failed:
        text = f"{text} {tn(language, 'failed_stories', failed)}"
    return text


def preferred_language() -> str:
    try:
        saved = _PREF.read_text(encoding="utf-8").strip().lower()
    except OSError:
        saved = ""
    if saved in TEXT:
        return saved
    return system_language()


def save_language(language: str) -> None:
    code = _code(language)
    try:
        _PREF.parent.mkdir(parents=True, exist_ok=True)
        _PREF.write_text(code, encoding="utf-8")
    except OSError:
        return


def normalize_language(value: str | None) -> str:
    if not value:
        return preferred_language()
    code = _ALIASES.get(value.lower(), value.lower())
    return code if code in TEXT else "en"


def system_language() -> str:
    try:
        raw = (locale.getlocale()[0] or "").lower().replace("-", "_")
    except Exception:
        raw = ""
    if raw.startswith(("uk", "ua")):
        return "uk"
    if raw.startswith("ru"):
        return "ru"
    return "en"


def choice_label(language: str) -> str:
    code = _code(language)
    return next(label for lang, label in CHOICES if lang == code)


def code_for_label(label: str) -> str:
    return next(lang for lang, name in CHOICES if name == label)


def _catalog(language: str) -> dict[str, str | tuple[str, str, str]]:
    return TEXT[_code(language)]


def _code(language: str) -> str:
    return language if language in TEXT else "en"


def _slavic_index(n: int) -> int:
    n = abs(n) % 100
    if 11 <= n <= 14:
        return 2
    last = n % 10
    if last == 1:
        return 0
    if 2 <= last <= 4:
        return 1
    return 2
