/* The phone app: screens, the download loop, and the bridge to the native shell.
 *
 * Native calls are asynchronous. iOS receives them through
 * webkit.messageHandlers.native, Android through AndroidBridge.post, and both
 * answer with FicbookNative._resolve(id, result).
 */
(function () {
  "use strict";

  const TEXT = window.FICBOOK_TEXT;
  const FORMATS = ["txt", "epub", "fb2"];
  const MIME = { txt: "text/plain", epub: "application/epub+zip", fb2: "application/x-fictionbook+xml" };
  const GITHUB = "https://github.com/thanaton20/ficbook-downloader";
  const $ = (id) => document.getElementById(id);

  // ---- Native bridge ------------------------------------------------------

  const platform = window.webkit && window.webkit.messageHandlers && window.webkit.messageHandlers.native
    ? "ios"
    : window.AndroidBridge ? "android" : "browser";
  const pending = new Map();
  let nextId = 1;

  window.FicbookNative = {
    _resolve(id, result) {
      const resolve = pending.get(id);
      pending.delete(id);
      if (resolve) resolve(result || { ok: false, error: "script_error" });
    },
  };

  function callNative(method, args = {}) {
    return new Promise((resolve) => {
      const id = nextId++;
      pending.set(id, resolve);
      const message = { id, method, args };
      if (platform === "ios") window.webkit.messageHandlers.native.postMessage(message);
      else if (platform === "android") window.AndroidBridge.post(JSON.stringify(message));
      else window.FicbookNative._resolve(id, { ok: false, error: "script_error", params: { message: "Open this page in the Ficbook app." } });
    });
  }

  // ---- Settings and language ----------------------------------------------

  const store = {
    get(key, fallback) {
      try {
        const value = localStorage.getItem(key);
        return value === null ? fallback : JSON.parse(value);
      } catch (error) {
        return fallback;
      }
    },
    set(key, value) {
      try {
        localStorage.setItem(key, JSON.stringify(value));
      } catch (error) {
        /* Settings simply won't persist. */
      }
    },
  };

  const settings = {
    language: store.get("language", systemLanguage()),
    pause: store.get("pause", 1.5),
    formats: store.get("formats", FORMATS.slice()),
    libraryFormats: store.get("libraryFormats", FORMATS.slice()),
    saved: store.get("saved", []),
  };

  function systemLanguage() {
    const raw = (navigator.language || "en").toLowerCase();
    if (raw.startsWith("uk") || raw.startsWith("ua")) return "uk";
    if (raw.startsWith("ru")) return "ru";
    return "en";
  }

  function t(key, params = {}) {
    const value = (TEXT[settings.language] || {})[key] ?? TEXT.en[key] ?? key;
    return String(value).replace(/\{(\w+)\}/g, (match, name) => (name in params ? params[name] : match));
  }

  function tn(key, n) {
    const forms = (TEXT[settings.language] || {})[key] || TEXT.en[key];
    let form;
    if (settings.language === "en" || !TEXT[settings.language]) form = n === 1 ? forms[0] : forms[1];
    else form = forms[slavicIndex(n)];
    return form.replace("{n}", n);
  }

  function slavicIndex(n) {
    n = Math.abs(n) % 100;
    if (n >= 11 && n <= 14) return 2;
    const last = n % 10;
    if (last === 1) return 0;
    if (last >= 2 && last <= 4) return 1;
    return 2;
  }

  function messageFor(error) {
    const code = error && error.code;
    if (code === "cancelled" || code === "stopped") return t("stopped");
    if (code === "script_error") return (error.params && error.params.message) || "Error";
    if (code && TEXT.en[code]) return t(code, error.params || {});
    return String((error && error.message) || error);
  }

  class AppError extends Error {
    constructor(code, params = {}) {
      super(code);
      this.code = code;
      this.params = params;
    }
  }

  // ---- Rendering ----------------------------------------------------------

  function applyLanguage() {
    document.documentElement.lang = settings.language;
    for (const node of document.querySelectorAll("[data-t]")) node.textContent = t(node.dataset.t);
    for (const node of document.querySelectorAll("[data-t-placeholder]")) node.placeholder = t(node.dataset.tPlaceholder);
    for (const button of $("languages").children) button.setAttribute("aria-checked", String(button.dataset.lang === settings.language));
    $("files-location").textContent = t(platform === "android" ? "files_location_android" : "files_location_ios");
    $("version").textContent = `Ficbook Downloader ${window.FICBOOK_VERSION}`;
    $("download").textContent = t(busy ? "stop" : "download");
    if (!busy) $("status").textContent = t("status_idle");
    if (libraryIdle) $("library-status").textContent = t("library_empty");
    updateLinkCount();
    renderSaved();
    renderBooks();
  }

  function showPage(name) {
    for (const page of document.querySelectorAll(".page")) page.hidden = page.dataset.page !== name;
    for (const tab of document.querySelectorAll("[data-tab]")) {
      if (tab.dataset.tab === name) tab.setAttribute("aria-current", "page");
      else tab.removeAttribute("aria-current");
    }
    window.scrollTo(0, 0);
  }

  function makeChips(container, selected, onChange) {
    for (const fmt of FORMATS) {
      const chip = document.createElement("button");
      chip.type = "button";
      chip.className = "chip";
      chip.textContent = fmt.toUpperCase();
      chip.setAttribute("aria-pressed", String(selected.includes(fmt)));
      chip.addEventListener("click", () => {
        chip.setAttribute("aria-pressed", String(chip.getAttribute("aria-pressed") !== "true"));
        onChange(Array.from(container.children).filter((c) => c.getAttribute("aria-pressed") === "true").map((c) => c.textContent.toLowerCase()));
      });
      container.appendChild(chip);
    }
  }

  // ---- Download page ------------------------------------------------------

  let busy = false;
  let stopRequested = false;

  function linkLines() {
    return $("links").value.split("\n").map((line) => line.trim()).filter(Boolean);
  }

  function updateLinkCount() {
    const count = linkLines().length;
    $("link-count").textContent = count ? tn("links_count", count) : "";
  }

  async function pasteLinks() {
    const result = await callNative("clipboard");
    const text = result.ok ? (result.data || "").trim() : "";
    if (!text) return;
    const box = $("links");
    const current = box.value.replace(/\s+$/, "");
    box.value = current ? `${current}\n${text}\n` : `${text}\n`;
    updateLinkCount();
  }

  function log(line) {
    $("details").hidden = false;
    const pre = $("log");
    pre.textContent += line + "\n";
    pre.scrollTop = pre.scrollHeight;
  }

  function setProgress(fraction) {
    const bar = $("progress");
    bar.hidden = fraction === null;
    if (fraction !== null) bar.firstElementChild.style.width = `${Math.round(fraction * 100)}%`;
  }

  function setBusy(value) {
    busy = value;
    const button = $("download");
    button.className = `button wide ${value ? "danger" : "primary"}`;
    button.textContent = t(value ? "stop" : "download");
  }

  async function onDownloadPressed() {
    if (busy) {
      stopRequested = true;
      return;
    }
    const urls = linkLines();
    if (!urls.length) {
      $("status").textContent = t("need_link");
      $("links").focus();
      return;
    }
    await runDownloads(urls, settings.formats);
  }

  async function runDownloads(urls, formats, onState = () => {}) {
    if (busy) return;
    if (!formats.length) {
      $("status").textContent = t("need_format");
      return;
    }
    setBusy(true);
    stopRequested = false;
    $("log").textContent = "";
    let saved = 0;
    let failed = 0;
    for (let index = 0; index < urls.length; index++) {
      if (stopRequested) {
        log(t("stopped"));
        break;
      }
      $("status").textContent = t("downloading_n", { i: index + 1, n: urls.length });
      setProgress(index / urls.length);
      const url = urls[index];
      log(url);
      onState(url, "saving");
      try {
        const story = await downloadStory(url, (done) => setProgress((index + done) / urls.length));
        const names = await saveStory(story, formats);
        names.forEach((name) => log(t("saved_path", { path: name })));
        saved++;
        onState(url, "downloaded");
      } catch (error) {
        onState(url, "download");
        if (error.code === "stopped" || error.code === "cancelled") {
          log(t("stopped"));
          break;
        }
        failed++;
        log(t("error_line", { message: messageFor(error) }));
      }
    }
    setProgress(null);
    setBusy(false);
    $("status").textContent = savedStatus(saved, failed);
  }

  function savedStatus(saved, failed) {
    let text = tn("saved_stories", saved);
    if (failed) text += " " + tn("failed_stories", failed);
    return text;
  }

  let lastRead = 0;

  async function read(url, kind, extra = {}) {
    const wait = settings.pause * 1000 - (Date.now() - lastRead);
    if (lastRead && wait > 0) await sleep(wait);
    if (stopRequested) throw new AppError("stopped");
    lastRead = Date.now();
    const result = await callNative("read", {
      url,
      kind,
      args: { url, notesLabel: t("notes"), chapterLabel: t("chapter"), storyId: extra.storyId || "" },
      labels: { title: t("check_title"), check: t("check_body"), age: t("age_body"), continue: t("continue"), cancel: t("cancel") },
    });
    if (!result.ok) throw new AppError(result.error, result.params || {});
    return result.data;
  }

  function sleep(ms) {
    return new Promise((resolve) => {
      const started = Date.now();
      const tick = () => (stopRequested || Date.now() - started >= ms ? resolve() : setTimeout(tick, 100));
      tick();
    });
  }

  async function downloadStory(link, onProgress = () => {}) {
    let storyUrl;
    try {
      storyUrl = FicbookParse.canonicalStoryUrl(link);
    } catch (error) {
      throw new AppError(error.code, error.params);
    }
    const story = await read(storyUrl, "story");
    if (story.series_url && story.series_index == null) {
      try {
        story.series_index = await read(story.series_url, "series", { storyId: story.story_id });
      } catch (error) {
        if (error.code === "stopped" || error.code === "cancelled") throw error;
        story.series_index = null;
      }
    }
    story.cover = null;
    if (story.cover_url) {
      const cover = await callNative("cover", { url: story.cover_url });
      if (cover.ok && cover.data) story.cover = FicbookBooks.fromBase64(cover.data);
    }
    const total = story.chapters.length;
    for (let index = 0; index < total; index++) {
      const chapter = story.chapters[index];
      log(`  ${index + 1}/${total} ${chapter.title}`);
      if (!chapter.paragraphs.length) {
        const loaded = await read(chapter.url, "chapter");
        chapter.paragraphs = loaded.paragraphs;
      }
      onProgress((index + 1) / total);
    }
    return story;
  }

  async function saveStory(story, formats) {
    const label = (key) => t(key);
    const stem = FicbookParse.fileStem(story);
    const names = [];
    for (const fmt of formats) {
      let base64;
      if (fmt === "txt") base64 = utf8Base64(FicbookBooks.renderTxt(story, label));
      else if (fmt === "fb2") base64 = utf8Base64(FicbookBooks.buildFb2(story, label, { version: window.FICBOOK_VERSION, cover: story.cover }));
      else base64 = FicbookBooks.toBase64(await FicbookBooks.buildEpub(story, label, { cover: story.cover }));
      const name = `${stem}.${fmt}`;
      const result = await callNative("save", { name, base64, mime: MIME[fmt] });
      if (!result.ok) throw new AppError(result.error || "script_error", result.params || {});
      names.push(name);
      rememberSaved(name);
    }
    return names;
  }

  function utf8Base64(text) {
    return FicbookBooks.toBase64(new TextEncoder().encode(text));
  }

  function rememberSaved(name) {
    settings.saved = [name, ...settings.saved.filter((item) => item !== name)].slice(0, 60);
    store.set("saved", settings.saved);
    renderSaved();
  }

  function renderSaved() {
    const list = $("saved");
    list.textContent = "";
    $("saved-card").hidden = !settings.saved.length;
    for (const name of settings.saved) {
      const item = document.createElement("li");
      const label = document.createElement("span");
      label.className = "file-name";
      label.textContent = name;
      const share = document.createElement("button");
      share.type = "button";
      share.className = "button secondary small";
      share.textContent = t("share");
      share.addEventListener("click", async () => {
        const result = await callNative("share", { name });
        if (!result.ok) {
          settings.saved = settings.saved.filter((item) => item !== name);
          store.set("saved", settings.saved);
          renderSaved();
        }
      });
      item.append(label, share);
      list.appendChild(item);
    }
  }

  // ---- Library page -------------------------------------------------------

  let libraryIdle = true;
  let works = [];
  let libraryAuthor = "";
  const bookStates = new Map();

  async function loadAuthor(event) {
    event.preventDefault();
    if (busy) return;
    let url;
    try {
      url = FicbookParse.canonicalAuthorWorksUrl($("author").value);
    } catch (error) {
      $("library-status").textContent = messageFor(error);
      return;
    }
    libraryIdle = false;
    $("author").blur();
    $("show-books").disabled = true;
    $("library-status").textContent = t("loading");
    try {
      let name = "";
      const found = [];
      const seen = new Set();
      let page = url;
      for (let i = 0; i < 40 && page; i++) {
        const result = await read(page, "works");
        name = name || result.name;
        for (const work of result.works) {
          if (!seen.has(work.story_id)) {
            seen.add(work.story_id);
            found.push(work);
          }
        }
        page = result.next;
      }
      if (url !== libraryAuthor) {
        bookStates.clear();
        libraryAuthor = url;
      }
      works = found;
      const count = t("books_count", { n: found.length });
      $("library-status").textContent = name ? `${name} · ${count}` : count;
      renderBooks();
    } catch (error) {
      $("library-status").textContent = messageFor(error);
    } finally {
      $("show-books").disabled = false;
    }
  }

  function renderBooks() {
    const list = $("books");
    list.textContent = "";
    for (const work of works) {
      const item = document.createElement("li");
      const title = document.createElement("p");
      title.className = "title";
      title.textContent = work.title;
      const actions = document.createElement("div");
      actions.className = "actions";
      const preview = document.createElement("button");
      preview.type = "button";
      preview.className = "button secondary";
      preview.textContent = t("preview");
      preview.addEventListener("click", () => openPreview(work));
      const download = document.createElement("button");
      download.type = "button";
      paintBookButton(download, bookStates.get(work.url) || "download");
      download.addEventListener("click", () => {
        const state = bookStates.get(work.url) || "download";
        if (state !== "download" || busy) return;
        runDownloads([work.url], settings.libraryFormats, (url, next) => {
          bookStates.set(work.url, next);
          paintBookButton(download, next);
        });
      });
      actions.append(preview, download);
      item.append(title, actions);
      list.appendChild(item);
    }
  }

  function paintBookButton(button, state) {
    button.className = `button ${state === "downloaded" ? "done" : "primary"}`;
    button.disabled = state === "saving";
    button.textContent = state === "downloaded" ? `✓ ${t("downloaded")}` : t(state);
  }

  async function openPreview(work) {
    $("library-status").textContent = t("loading");
    try {
      const story = await read(work.url, "story");
      $("library-status").textContent = "";
      const cover = $("preview-cover");
      cover.textContent = t("no_cover");
      if (story.cover_url) {
        const result = await callNative("cover", { url: story.cover_url });
        if (result.ok && result.data) {
          const img = document.createElement("img");
          img.alt = story.title;
          img.src = `data:image/jpeg;base64,${result.data}`;
          cover.textContent = "";
          cover.appendChild(img);
        }
      }
      $("preview-title").textContent = story.title;
      $("preview-author").textContent = `${t("author")}: ${story.author}`;
      let series = story.series_name || t("no_series");
      if (story.series_name && story.series_index) series = `${story.series_name} (${story.series_index})`;
      $("preview-series").textContent = `${t("series")}: ${series}`;
      $("preview").showModal();
    } catch (error) {
      $("library-status").textContent = messageFor(error);
    }
  }

  // ---- Settings page ------------------------------------------------------

  function buildLanguages() {
    for (const [code, label] of [["en", "English"], ["ru", "Русский"], ["uk", "Українська"]]) {
      const button = document.createElement("button");
      button.type = "button";
      button.setAttribute("role", "radio");
      button.dataset.lang = code;
      button.textContent = label;
      button.addEventListener("click", () => {
        settings.language = code;
        store.set("language", code);
        applyLanguage();
      });
      $("languages").appendChild(button);
    }
  }

  function setPause(value) {
    const number = Math.min(30, Math.max(0, Math.round((Number(String(value).replace(",", ".")) || 0) * 2) / 2));
    settings.pause = number;
    store.set("pause", number);
    $("pause").value = String(number);
  }

  // ---- Start --------------------------------------------------------------

  function start() {
    buildLanguages();
    makeChips($("formats"), settings.formats, (value) => {
      settings.formats = value;
      store.set("formats", value);
    });
    makeChips($("library-formats"), settings.libraryFormats, (value) => {
      settings.libraryFormats = value;
      store.set("libraryFormats", value);
    });
    $("pause").value = String(settings.pause);
    $("pause").addEventListener("change", (event) => setPause(event.target.value));
    $("pause-down").addEventListener("click", () => setPause(settings.pause - 0.5));
    $("pause-up").addEventListener("click", () => setPause(settings.pause + 0.5));
    $("links").addEventListener("input", updateLinkCount);
    $("paste").addEventListener("click", pasteLinks);
    $("clear").addEventListener("click", () => {
      $("links").value = "";
      updateLinkCount();
    });
    $("download").addEventListener("click", onDownloadPressed);
    $("author-form").addEventListener("submit", loadAuthor);
    $("open-files").addEventListener("click", () => callNative("openFiles"));
    $("open-files-2").addEventListener("click", () => callNative("openFiles"));
    $("github").addEventListener("click", () => callNative("openUrl", { url: GITHUB }));
    $("preview-close").addEventListener("click", () => $("preview").close());
    $("preview").addEventListener("click", (event) => {
      if (event.target === $("preview")) $("preview").close();
    });
    for (const tab of document.querySelectorAll("[data-tab]")) tab.addEventListener("click", () => showPage(tab.dataset.tab));
    applyLanguage();
    const page = location.hash.slice(1);
    showPage(["library", "settings"].includes(page) ? page : "download");
  }

  start();
})();
