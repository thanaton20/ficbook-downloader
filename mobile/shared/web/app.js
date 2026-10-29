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
    renderPreviews();
    renderSaved();
    renderBooks();
    if (authorCount !== null) $("author-count").textContent = t("books_count", { n: authorCount });
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
    renderGutter();
  }

  /* Number each link line with its place in the download order. */
  function renderGutter() {
    const gutter = $("gutter");
    let number = 0;
    gutter.textContent = "";
    for (const line of $("links").value.split("\n")) {
      const row = document.createElement("div");
      if (line.trim()) row.textContent = String(++number);
      gutter.appendChild(row);
    }
    gutter.scrollTop = $("links").scrollTop;
  }

  function onLinksChanged() {
    updateLinkCount();
    clearTimeout(previewTimer);
    previewTimer = setTimeout(() => {
      renderPreviews();
      pumpPreviews();
    }, 600);
  }

  // ---- Book previews ------------------------------------------------------

  const TONES = ["#3f6b60", "#4a6378", "#7d6250", "#6b5870", "#5d6e4c", "#4f6d6d"];
  const previews = new Map(); // story URL -> { status, story, image, error, saved }
  let previewTimer = 0;
  let pumping = false;

  function linkEntries() {
    return linkLines().map((line, index) => {
      try {
        const url = FicbookParse.canonicalStoryUrl(line);
        if (!previews.has(url)) previews.set(url, { status: "waiting" });
        return { number: index + 1, line, url, entry: previews.get(url) };
      } catch (error) {
        return { number: index + 1, line, url: "", entry: { status: "failed", error } };
      }
    });
  }

  function renderPreviews() {
    const list = $("previews");
    list.textContent = "";
    for (const { number, line, url, entry } of linkEntries()) {
      const story = entry.story;
      let author = t("loading");
      if (story) author = story.author;
      else if (entry.status === "failed") author = messageFor(entry.error);
      list.appendChild(bookCard({
        number,
        saved: entry.saved,
        seed: url || line,
        title: story ? story.title : line,
        author,
        image: entry.image,
        state: entry.status,
      }));
    }
  }

  /* Load previews one story at a time, and step aside while a download runs. */
  async function pumpPreviews() {
    if (pumping) return;
    pumping = true;
    try {
      while (!busy) {
        const next = linkEntries().find((item) => item.entry.status === "waiting");
        if (!next) break;
        const entry = next.entry;
        entry.status = "loading";
        try {
          entry.story = await read(next.url, "story");
          entry.status = "done";
          renderPreviews();
          if (entry.story.cover_url) {
            const result = await callNative("image", { url: entry.story.cover_url });
            if (result.ok) entry.image = result.data;
          }
        } catch (error) {
          entry.status = "failed";
          entry.error = error;
        }
        renderPreviews();
      }
    } finally {
      pumping = false;
    }
  }

  /* A cover with the title and author under it. Without a cover image, the title is set on a coloured block. */
  function bookCard({ number, saved, seed, title, author, image, state, onOpen, action }) {
    const item = document.createElement("li");
    const waiting = state === "waiting" || state === "loading";
    item.className = `book${state === "failed" ? " failed" : waiting ? " waiting" : ""}`;
    const cover = document.createElement(onOpen ? "button" : "div");
    cover.className = "cover";
    if (onOpen) {
      cover.type = "button";
      cover.setAttribute("aria-label", title);
      cover.addEventListener("click", onOpen);
    }
    if (!waiting && state !== "failed") cover.style.setProperty("--tone", tone(seed));
    if (image) {
      cover.appendChild(coverImage(image));
    } else {
      const label = document.createElement("span");
      label.className = "cover-title";
      label.textContent = state === "failed" ? "!" : waiting ? "…" : title;
      cover.appendChild(label);
    }
    if (number) {
      const badge = document.createElement("span");
      badge.className = `badge${saved ? " done" : ""}`;
      badge.textContent = saved ? `✓ ${number}` : String(number);
      cover.appendChild(badge);
    }
    const name = document.createElement("p");
    name.className = "book-title";
    name.textContent = title;
    item.append(cover, name);
    if (author) {
      const by = document.createElement("p");
      by.className = "book-author";
      by.textContent = author;
      item.appendChild(by);
    }
    if (action) item.appendChild(action);
    return item;
  }

  function coverImage(src) {
    const img = document.createElement("img");
    img.alt = "";
    img.src = src;
    return img;
  }

  function tone(seed) {
    let hash = 0;
    for (const char of String(seed)) hash = (hash * 31 + char.codePointAt(0)) >>> 0;
    return TONES[hash % TONES.length];
  }

  async function pasteLinks() {
    const result = await callNative("clipboard");
    const text = result.ok ? (result.data || "").trim() : "";
    if (!text) return;
    const box = $("links");
    const current = box.value.replace(/\s+$/, "");
    box.value = current ? `${current}\n${text}\n` : `${text}\n`;
    onLinksChanged();
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
        const entry = previews.get(story.url);
        if (entry) {
          entry.saved = true;
          renderPreviews();
        }
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
    stopRequested = false;
    $("status").textContent = savedStatus(saved, failed);
    pumpPreviews();
  }

  function savedStatus(saved, failed) {
    let text = tn("saved_stories", saved);
    if (failed) text += " " + tn("failed_stories", failed);
    return text;
  }

  let lastRead = 0;
  let readQueue = Promise.resolve();

  /* The native reader opens one page at a time, so reads take turns. */
  function read(url, kind, extra = {}) {
    const run = readQueue.then(() => readNow(url, kind, extra));
    readQueue = run.catch(() => {});
    return run;
  }

  async function readNow(url, kind, extra) {
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
    // Reuse the page already read for the preview.
    const cached = previews.get(storyUrl);
    const story = cached && cached.story ? copy(cached.story) : await read(storyUrl, "story");
    if (!cached || !cached.story) previews.set(storyUrl, { status: "done", story: copy(story) });
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

  function copy(value) {
    return JSON.parse(JSON.stringify(value));
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
  let authorCount = null;
  const bookStates = new Map();
  const coverRequests = new Map(); // image URL -> Promise of a data URL
  const coverObserver = "IntersectionObserver" in window
    ? new IntersectionObserver(onCoverVisible, { rootMargin: "600px 0px" })
    : null;

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
    $("author-head").hidden = true;
    authorCount = null;
    works = [];
    renderBooks();
    try {
      let name = "";
      let avatar = "";
      const found = [];
      const seen = new Set();
      let page = url;
      for (let i = 0; i < 40 && page; i++) {
        const result = await read(page, "works");
        name = name || result.name;
        avatar = avatar || result.avatar;
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
      $("library-status").textContent = "";
      showAuthor(name, avatar, found.length);
      renderBooks();
    } catch (error) {
      $("library-status").textContent = messageFor(error);
    } finally {
      $("show-books").disabled = false;
    }
  }

  function showAuthor(name, avatar, count) {
    authorCount = count;
    $("author-head").hidden = false;
    $("author-name").textContent = name;
    $("author-count").textContent = t("books_count", { n: count });
    const box = $("avatar");
    box.textContent = (name || "?").trim().charAt(0).toUpperCase();
    if (!avatar) return;
    callNative("image", { url: avatar }).then((result) => {
      if (!result.ok) return;
      box.textContent = "";
      box.appendChild(coverImage(result.data));
    });
  }

  function renderBooks() {
    const list = $("books");
    list.textContent = "";
    for (const work of works) {
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
      const item = bookCard({ seed: work.url, title: work.title, onOpen: () => openPreview(work), action: download });
      if (work.cover_url) {
        item.dataset.cover = work.cover_url;
        if (coverObserver) coverObserver.observe(item);
        else showCover(item);
      }
      list.appendChild(item);
    }
  }

  /* Covers load as their rows come near the screen. */
  function onCoverVisible(entries) {
    for (const entry of entries) {
      if (!entry.isIntersecting) continue;
      coverObserver.unobserve(entry.target);
      showCover(entry.target);
    }
  }

  async function showCover(item) {
    const data = await loadImage(item.dataset.cover);
    if (!data || !item.isConnected) return;
    const box = item.querySelector(".cover");
    box.querySelector(".cover-title")?.remove();
    box.prepend(coverImage(data));
  }

  function loadImage(url) {
    if (!coverRequests.has(url)) {
      coverRequests.set(url, callNative("image", { url }).then((result) => (result.ok ? result.data : "")));
    }
    return coverRequests.get(url);
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
      const image = story.cover_url || work.cover_url;
      const data = image ? await loadImage(image) : "";
      if (data) {
        cover.textContent = "";
        cover.appendChild(coverImage(data));
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
    $("links").addEventListener("input", onLinksChanged);
    $("links").addEventListener("scroll", () => {
      $("gutter").scrollTop = $("links").scrollTop;
    });
    $("paste").addEventListener("click", pasteLinks);
    $("clear").addEventListener("click", () => {
      $("links").value = "";
      onLinksChanged();
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
