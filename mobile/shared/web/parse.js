/* Read ficbook pages from the live DOM. A port of src/ficbook_dl/parse.py.
 *
 * The phone apps open each page in the system web view and run this inside it,
 * so the page is read exactly as a browser shows it. Results are plain objects
 * with the same field names as the Python Story dataclass.
 */
(function (root) {
  "use strict";

  const BASE = "https://ficbook.net";
  const SECURITY_TITLE = "Проверка безопасности";
  const UI_LINES = new Set(["Спойлеры", "Показать", "Скрыть", "Спойлер"]);
  const SKIPPED = new Set(["script", "style", "template", "noscript"]);
  // ficbook's scripts insert other stories' promos into the chapter text.
  const INSERTED = ["fanfic-text-promo", "js-text-insert", "js-promo-fanfic", "fanfic-promo-item"];
  const AUTHOR_PATH = /^\/authors\/[^/]+\/?$/;
  const LINE_BREAKS = /\r\n|[\n\r\v\f\x1c-\x1e\x85\u2028\u2029]/;

  class ParseError extends Error {
    constructor(code, params = {}) {
      super(code);
      this.code = code;
      this.params = params;
    }
  }

  function canonicalStoryUrl(value) {
    const raw = String(value || "").trim();
    if (!raw) throw new ParseError("empty_link");
    if (!raw.includes("://") && !raw.includes("/")) {
      if (!/^[0-9A-Za-z-]+$/.test(raw)) throw new ParseError("not_ficbook", { value });
      return `${BASE}/readfic/${raw}`;
    }
    const parsed = parseUrl(raw);
    if (!parsed || host(parsed) !== "ficbook.net") throw new ParseError("not_ficbook", { value });
    const match = /^\/readfic\/([^/]+)/.exec(parsed.pathname);
    if (!match) throw new ParseError("not_ficbook", { value });
    return `${BASE}/readfic/${match[1]}`;
  }

  function canonicalAuthorWorksUrl(value) {
    const raw = String(value || "").trim();
    if (!raw) throw new ParseError("need_author");
    if (!raw.includes("://") && !raw.includes("/") && /^[0-9A-Za-z-]+$/.test(raw)) {
      return `${BASE}/authors/${raw}/profile/works`;
    }
    const parsed = parseUrl(raw.includes("://") ? raw : `${BASE}/${raw.replace(/^\/+/, "")}`);
    if (!parsed || host(parsed) !== "ficbook.net") throw new ParseError("not_author", { value });
    const parts = parsed.pathname.split("/").filter(Boolean);
    if (parts.length < 2 || parts[0] !== "authors") throw new ParseError("not_author", { value });
    return `${BASE}/authors/${parts[1]}/profile/works`;
  }

  function parseStory(doc, pageUrl, options = {}) {
    rejectSecurityPage(doc);
    const storyUrl = canonicalStoryUrl(pageUrl);
    const storyId = storyUrl.split("/").pop();
    const header = doc.querySelector("section.chapter-info") || doc.querySelector(".fanfic-hat") || doc;
    const hat = doc.querySelector(".fanfic-hat");
    let info = null;
    for (const scope of [header, hat, doc]) {
      if (!scope) continue;
      info = scope.querySelector("div.description.word-break");
      if (info) break;
    }
    info = info || header;
    const title = text(header.querySelector("h1.heading, h1")) || text(doc.querySelector("h1")) || storyId;
    let postedBy = authors(header);
    if (!postedBy.length) postedBy = authors(hat || doc);
    const originals = splitNames(fieldText(info, "Автор оригинала:"));
    let storyAuthors = postedBy;
    let translators = [];
    if (originals.length) {
      storyAuthors = originals;
      translators = postedBy.filter((name) => !originals.includes(name));
    }

    let chapters = chapterLinks(doc, storyId);
    if (!chapters.length) {
      const paragraphs = chapterParagraphs(doc, options.notesLabel);
      if (paragraphs.length) {
        const heading = text(header.querySelector("h2") || doc.querySelector("h2")) || title;
        chapters = [{ title: heading, url: storyUrl, paragraphs }];
      } else if (doc.querySelector("#adultCoverWarning")) {
        throw new ParseError("age_check", { url: storyUrl });
      } else {
        throw new ParseError("missing_story", { url: storyUrl });
      }
    }

    const rating = text(header.querySelector("[class*='ds-label-rating-']"));
    const status = text(header.querySelector("[class*='ds-label-status-']"));
    const directions = unique(
      Array.from(header.querySelectorAll("[class*='direction']"))
        .filter((node) => text(node) && !hasAncestorClass(node, /promo|fanfic-inline/))
        .map(text)
    );
    const [seriesName, seriesUrl] = series(info);
    return {
      story_id: storyId,
      title,
      author: storyAuthors.join(", ") || "Unknown",
      url: storyUrl,
      description: fieldText(info, "Описание:"),
      details: [rating, status].filter(Boolean).join(" · "),
      chapters,
      authors: storyAuthors,
      translators,
      series_name: seriesName,
      series_index: null,
      series_url: seriesUrl,
      cover_url: coverUrl(doc),
      fandoms: fieldLinks(info, "Фэндом:"),
      pairings: fieldLinks(info, "Пэйринг и персонажи:"),
      tags: fieldLinks(info, "Метки:"),
      directions,
      rating,
      status,
      dedication: fieldText(info, "Посвящение:"),
      notes: fieldText(info, "Примечания:"),
      language: "ru",
    };
  }

  function parseChapter(doc, chapterUrl, options = {}) {
    rejectSecurityPage(doc);
    const paragraphs = chapterParagraphs(doc, options.notesLabel);
    if (paragraphs.length) {
      const title = text(doc.querySelector("h2")) || options.chapterLabel || "Chapter";
      return { title, url: chapterUrl, paragraphs };
    }
    if (doc.querySelector("#adultCoverWarning")) throw new ParseError("age_check", { url: chapterUrl });
    throw new ParseError("missing_chapter", { url: chapterUrl });
  }

  /** The 1-based position of a story on a ficbook series page. */
  function seriesIndex(doc, storyId) {
    const seen = [];
    for (const anchor of doc.querySelectorAll("a.visit-link[href*='/readfic/']")) {
      const found = readficId(anchor);
      if (found && !seen.includes(found)) seen.push(found);
    }
    const index = seen.indexOf(storyId);
    return index < 0 ? null : index + 1;
  }

  /** The author name, the books on this page, and the next page URL. */
  function parseAuthorWorks(doc, pageUrl) {
    rejectSecurityPage(doc);
    const name = text(doc.querySelector("h1")) || authorNameFromTitle(doc);
    const works = [];
    const seen = new Set();
    for (const anchor of doc.querySelectorAll("a.visit-link[href*='/readfic/']")) {
      if (anchor.classList.contains("js-promo-fanfic") || anchor.classList.contains("fanfic-promo-item")) continue;
      const storyId = readficId(anchor);
      if (!storyId || seen.has(storyId)) continue;
      seen.add(storyId);
      works.push({ story_id: storyId, title: text(anchor) || storyId, url: `${BASE}/readfic/${storyId}`, cover_url: workCover(anchor) });
    }
    return { name, works, next: nextWorksPage(doc, pageUrl), avatar: authorAvatar(doc, pageUrl) };
  }

  /** The author's profile picture on their works page, or "". */
  function authorAvatar(doc, pageUrl) {
    const page = parseUrl(pageUrl);
    const parts = page ? page.pathname.split("/").filter(Boolean) : [];
    const own = parts.length > 1 && parts[0] === "authors" ? `/authors/${parts[1]}` : "";
    const images = Array.from(doc.querySelectorAll("img")).filter((image) => imageSrc(image).includes("/avatars/"));
    for (const image of images) {
      const link = image.parentElement && image.parentElement.closest("a[href]");
      const target = link && parseUrl(link.getAttribute("href"), BASE);
      if (own && target && target.pathname.replace(/\/+$/, "") === own) return absolute(imageSrc(image));
    }
    return images.length ? absolute(imageSrc(images[0])) : "";
  }

  function workCover(anchor) {
    const card = anchor.parentElement && anchor.parentElement.closest("article");
    if (!card) return "";
    for (const image of card.querySelectorAll("img")) {
      const src = imageSrc(image);
      if (src.includes("/fanfic-covers/")) return absolute(src);
    }
    return "";
  }

  function imageSrc(image) {
    return (image.getAttribute("src") || image.getAttribute("data-src") || "").trim();
  }

  function absolute(src) {
    const parsed = parseUrl(src, BASE);
    return parsed ? parsed.href : "";
  }

  function fileStem(story) {
    const raw = `${story.title} — ${story.author}`;
    const cleaned = raw.replace(/[\\/:*?"<>|]/g, " ").replace(/\s+/g, " ").trim().replace(/\.+$/, "");
    return cleaned.slice(0, 120) || story.story_id;
  }

  /** Entry point for the native apps: never throws, always returns a plain object. */
  function run(kind, args = {}, doc = root.document) {
    try {
      const url = args.url || (root.location && root.location.href) || "";
      let data;
      if (kind === "story") data = parseStory(doc, url, args);
      else if (kind === "chapter") data = parseChapter(doc, url, args);
      else if (kind === "series") data = (rejectSecurityPage(doc), seriesIndex(doc, args.storyId));
      else if (kind === "works") data = parseAuthorWorks(doc, url);
      else throw new ParseError("unknown_kind", { kind });
      return { ok: true, data };
    } catch (error) {
      if (error instanceof ParseError) return { ok: false, error: error.code, params: error.params };
      return { ok: false, error: "script_error", params: { message: String(error && error.message) } };
    }
  }

  function rejectSecurityPage(doc) {
    if ((doc.title || "").trim().startsWith(SECURITY_TITLE)) throw new ParseError("security_check");
  }

  function chapterLinks(doc, storyId) {
    const chapters = [];
    const seen = new Set();
    for (const anchor of doc.querySelectorAll("ul.list-of-fanfic-parts a.part-link")) {
      const parsed = parseUrl(anchor.getAttribute("href") || "", BASE);
      if (!parsed) continue;
      parsed.hash = "";
      const url = parsed.href;
      if (!parsed.pathname.startsWith(`/readfic/${storyId}/`) || seen.has(url)) continue;
      seen.add(url);
      const title = text(anchor.querySelector("h3")) || text(anchor) || `Part ${chapters.length + 1}`;
      chapters.push({ title, url, paragraphs: [] });
    }
    return chapters;
  }

  function authors(scope) {
    const names = [];
    const seen = new Set();
    for (const anchor of scope.querySelectorAll("a.word-break[href*='/authors/'], a[itemprop='author']")) {
      const parsed = parseUrl(anchor.getAttribute("href") || "", BASE);
      const path = parsed ? parsed.pathname : "";
      if (!AUTHOR_PATH.test(path) || seen.has(path)) continue;
      const name = text(anchor);
      if (!name) continue;
      seen.add(path);
      names.push(name);
    }
    return names;
  }

  function series(scope) {
    const sibling = fieldNode(scope, "Серия:");
    if (!sibling) return ["", ""];
    const link = sibling.querySelector("a[href]");
    if (!link) return [text(sibling), ""];
    const parsed = parseUrl(link.getAttribute("href"), BASE);
    return [text(link), parsed ? parsed.href : ""];
  }

  function coverUrl(doc) {
    for (const meta of doc.querySelectorAll("meta[property='og:image']")) {
      const content = (meta.getAttribute("content") || "").trim();
      if (content.includes("/fanfic-covers/")) return content;
    }
    return "";
  }

  function fieldNode(scope, label) {
    for (const strong of scope.querySelectorAll("strong")) {
      if (!text(strong).startsWith(label)) continue;
      let node = strong.nextElementSibling;
      while (node && node.tagName.toLowerCase() !== "div") node = node.nextElementSibling;
      return node;
    }
    return null;
  }

  function fieldText(scope, label) {
    const node = fieldNode(scope, label);
    if (!node) return "";
    const lines = [];
    for (const line of strings(node).map((part) => part.trim()).filter(Boolean).join("\n").split(LINE_BREAKS)) {
      const cleaned = collapse(line);
      if (cleaned && !UI_LINES.has(cleaned)) lines.push(cleaned);
    }
    return lines.join("\n");
  }

  function fieldLinks(scope, label) {
    const node = fieldNode(scope, label);
    if (!node) return [];
    const names = Array.from(node.querySelectorAll("a")).map(text).filter(Boolean);
    if (names.length) return names;
    const value = fieldText(scope, label);
    return value ? [value] : [];
  }

  function chapterParagraphs(doc, notesLabel = "Notes") {
    const node = doc.querySelector("#content") || doc.querySelector(".part_text") || doc.querySelector("[itemprop='articleBody']");
    const paragraphs = [];
    const label = `<i>${escapeHtml(notesLabel)}</i>`;
    const head = noteLines(doc.querySelector("div.part-comment-top"));
    if (head.length) paragraphs.push(label, ...head);
    if (node) paragraphs.push(...htmlParagraphs(node));
    const foot = noteLines(doc.querySelector("div.part-comment-bottom"));
    if (foot.length) paragraphs.push(label, ...foot);
    return paragraphs;
  }

  function noteLines(node) {
    if (!node) return [];
    return plainLines(strings(node).join("\n")).map(escapeHtml);
  }

  function htmlParagraphs(node) {
    return inlineMarkup(node)
      .split("\n")
      .map((line) => line.trim())
      .filter(Boolean);
  }

  function inlineMarkup(node) {
    const chunks = [];
    const walk = (current) => {
      for (const child of current.childNodes) {
        if (child.nodeType === 3) {
          chunks.push(escapeHtml(child.nodeValue).replace(/\r\n/g, "\n").replace(/\r/g, "\n"));
          continue;
        }
        if (child.nodeType !== 1) continue;
        const name = child.tagName.toLowerCase();
        if (SKIPPED.has(name)) continue;
        if (INSERTED.some((cls) => child.classList.contains(cls))) {
          if (chunks.length && !chunks[chunks.length - 1].endsWith("\n")) chunks.push("\n");
          continue;
        }
        if (name === "br") {
          chunks.push("\n");
        } else if (["i", "em", "b", "strong"].includes(name)) {
          const inner = inlineMarkup(child);
          if (inner.trim()) chunks.push(balancedTag(name === "i" || name === "em" ? "i" : "b", inner));
        } else if (["p", "div", "li", "blockquote"].includes(name)) {
          if (chunks.length && !chunks[chunks.length - 1].endsWith("\n")) chunks.push("\n");
          walk(child);
          chunks.push("\n");
        } else {
          walk(child);
        }
      }
    };
    walk(node);
    return chunks.join("");
  }

  /* Keep italics and bold inside a single paragraph, as in parse.py. */
  function balancedTag(tag, inner) {
    return inner
      .replace(/\r\n/g, "\n")
      .replace(/\r/g, "\n")
      .split("\n")
      .map((line) => (line.trim() ? `<${tag}>${line.trim()}</${tag}>` : ""))
      .join("\n");
  }

  function plainLines(value) {
    return value
      .replace(/\r\n/g, "\n")
      .replace(/\r/g, "\n")
      .split("\n")
      .map(collapse)
      .filter((line) => line && !UI_LINES.has(line));
  }

  function nextWorksPage(doc, pageUrl) {
    const parsed = parseUrl(pageUrl);
    if (!parsed) return null;
    const current = parseInt(parsed.searchParams.get("p") || "1", 10) || 1;
    const pages = new Set();
    for (const anchor of doc.querySelectorAll("a[href*='/profile/works']")) {
      const link = parseUrl(anchor.getAttribute("href") || "", BASE);
      const page = link && link.searchParams.get("p");
      if (page && /^\d+$/.test(page)) pages.add(parseInt(page, 10));
    }
    if (!pages.has(current + 1)) return null;
    parsed.searchParams.set("p", String(current + 1));
    parsed.hash = "";
    return parsed.href;
  }

  function authorNameFromTitle(doc) {
    const title = collapse(doc.title || "");
    return title.split(/\s+[–—-]\s+/)[0].trim();
  }

  function readficId(anchor) {
    const parsed = parseUrl(anchor.getAttribute("href") || "", BASE);
    if (!parsed) return "";
    const match = /^\/readfic\/([^/]+)$/.exec(parsed.pathname.replace(/\/+$/, ""));
    return match ? match[1] : "";
  }

  function hasAncestorClass(node, pattern) {
    for (let parent = node.parentElement; parent; parent = parent.parentElement) {
      if (pattern.test(parent.getAttribute("class") || "")) return true;
    }
    return false;
  }

  /* Text nodes in document order, skipping scripts and styles, like bs4's get_text. */
  function strings(node) {
    const out = [];
    const walk = (current) => {
      for (const child of current.childNodes) {
        if (child.nodeType === 3) out.push(child.nodeValue);
        else if (child.nodeType === 1 && !SKIPPED.has(child.tagName.toLowerCase())) walk(child);
      }
    };
    if (node.nodeType === 3) out.push(node.nodeValue);
    else walk(node);
    return out;
  }

  function text(node) {
    if (!node) return "";
    return collapse(strings(node).map((part) => part.trim()).filter(Boolean).join(" "));
  }

  function collapse(value) {
    return value.replace(/\s+/g, " ").trim();
  }

  function splitNames(value) {
    return value.split(",").map((part) => part.trim()).filter(Boolean);
  }

  function unique(values) {
    return Array.from(new Set(values.filter(Boolean)));
  }

  function escapeHtml(value) {
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#x27;");
  }

  function parseUrl(value, base) {
    try {
      return base ? new URL(value, base) : new URL(value);
    } catch (error) {
      return null;
    }
  }

  function host(parsed) {
    return parsed.host.toLowerCase().replace(/^www\./, "");
  }

  const api = {
    ParseError,
    canonicalStoryUrl,
    canonicalAuthorWorksUrl,
    parseStory,
    parseChapter,
    seriesIndex,
    parseAuthorWorks,
    fileStem,
    escapeHtml,
    run,
  };
  root.FicbookParse = api;
  if (typeof module === "object" && module.exports) module.exports = api;
})(typeof globalThis !== "undefined" ? globalThis : this);
