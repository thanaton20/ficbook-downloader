/* Build txt, FB2, and EPUB files from a parsed story.
 * A port of src/ficbook_dl/formats; the output matches the desktop app.
 * `t(key)` returns an interface label (Author, Series, ...) in the chosen language.
 */
(function (root) {
  "use strict";

  const STYLE = `body { font-family: Georgia, "Times New Roman", serif; line-height: 1.45; margin: 1em; }
h1 { font-size: 1.4em; text-align: center; margin: 1.2em 0 1em; page-break-before: always; }
p { margin: 0.35em 0; text-indent: 1.15em; }
p.note { font-style: italic; text-indent: 0; }
.cover { text-align: center; margin: 0; text-indent: 0; }
.cover img { max-width: 100%; height: auto; }
`;

  function renderTxt(story, t) {
    const lines = [story.title, `${t("author")}: ${story.author}`, story.url];
    if (story.translators.length) lines.push(`${t("translator")}: ` + story.translators.join(", "));
    if (story.series_name) {
      const number = story.series_index ? ` (${story.series_index})` : "";
      lines.push(`${t("series")}: ${story.series_name}${number}`);
    }
    if (story.fandoms.length) lines.push(`${t("fandom")}: ` + story.fandoms.join(", "));
    if (story.directions.length) lines.push(`${t("direction")}: ` + story.directions.join(", "));
    if (story.pairings.length) lines.push(`${t("characters")}: ` + story.pairings.join(", "));
    if (story.rating || story.status) lines.push([story.rating, story.status].filter(Boolean).join(" · "));
    if (story.tags.length) lines.push(`${t("tags")}: ` + story.tags.join(", "));
    lines.push("");
    if (story.description) lines.push(story.description, "");
    if (story.dedication) lines.push(`${t("dedication")}: ${story.dedication}`, "");
    if (story.notes) lines.push(`${t("notes")}: ${story.notes}`, "");
    story.chapters.forEach((chapter, index) => {
      if (index) lines.push("");
      lines.push(chapter.title, "", chapterBody(chapter));
    });
    return lines.join("\n").replace(/\s+$/, "") + "\n";
  }

  function chapterBody(chapter) {
    return chapter.paragraphs
      .map((paragraph) => fragment(paragraph).textContent.trim())
      .filter(Boolean)
      .join("\n\n");
  }

  function buildFb2(story, t, { version = "", cover = null, today = isoToday() } = {}) {
    const authors = (story.authors.length ? story.authors : [story.author]).map((name) => person("author", name)).join("\n");
    const translators = story.translators.map((name) => person("translator", name)).join("\n");
    let sequence = "";
    if (story.series_name) {
      const number = story.series_index ? ` number="${story.series_index}"` : "";
      sequence = `<sequence name="${attr(story.series_name)}"${number}/>`;
    }
    const keywords = [...story.fandoms, ...story.directions, ...story.pairings, ...story.tags, story.rating, story.status]
      .filter(Boolean)
      .join(", ");
    let coverTag = "";
    let binary = "";
    if (cover) {
      coverTag = '<coverpage><image l:href="#cover.jpg"/></coverpage>';
      const encoded = toBase64(cover);
      const wrapped = encoded.match(/.{1,76}/g).join("\n");
      binary = `<binary id="cover.jpg" content-type="image/jpeg">${wrapped}</binary>`;
    }
    const sections = story.chapters.map((chapter) => section(chapter.title, chapter.paragraphs)).join("\n");
    return `<?xml version="1.0" encoding="utf-8"?>
<FictionBook xmlns="http://www.gribuser.ru/xml/fictionbook/2.0" xmlns:l="http://www.w3.org/1999/xlink">
  <description>
    <title-info>
      <genre>fanfiction</genre>
      ${authors}
      ${translators}
      <book-title>${xml(story.title)}</book-title>
      ${fb2Annotation(story, t)}
      ${coverTag}
      ${sequence}
      <keywords>${xml(keywords)}</keywords>
      <lang>${xml(story.language)}</lang>
      <src-lang>${xml(story.language)}</src-lang>
    </title-info>
    <document-info>
      <author><nickname>ficbook-downloader</nickname></author>
      <program-used>ficbook-downloader ${version}</program-used>
      <date value="${today}">${today}</date>
      <src-url>${xml(story.url)}</src-url>
      <id>${xml(story.url)}</id>
    </document-info>
    <publish-info>
      <book-name>${xml(story.title)}</book-name>
      <publisher>ficbook.net</publisher>
    </publish-info>
  </description>
  <body>
    ${sections}
  </body>
  ${binary}
</FictionBook>
`;
  }

  function fb2Annotation(story, t) {
    const paragraphs = plainParagraphs(story.description);
    if (story.dedication) paragraphs.push(`${t("dedication")}: ` + story.dedication);
    paragraphs.push(...plainParagraphs(story.notes));
    if (!paragraphs.length) return "";
    return `<annotation>\n${paragraphs.map((paragraph) => `<p>${xml(paragraph)}</p>`).join("\n")}\n</annotation>`;
  }

  function section(title, paragraphs) {
    const body = paragraphs
      .filter((paragraph) => paragraph.trim())
      .map((paragraph) => `<p>${fb2Inline(paragraph)}</p>`)
      .join("\n");
    return `<section>
      <title><p>${xml(title)}</p></title>
      ${body}
    </section>`;
  }

  function person(tag, name) {
    const parts = name.split(/\s+/).filter(Boolean);
    if (parts.length === 2 && parts.every((part) => /^[\p{L}'-]+$/u.test(part))) {
      return `<${tag}><first-name>${xml(parts[0])}</first-name><last-name>${xml(parts[1])}</last-name></${tag}>`;
    }
    return `<${tag}><nickname>${xml(name)}</nickname></${tag}>`;
  }

  function fb2Inline(markup) {
    const walk = (node) => {
      let out = "";
      for (const child of node.childNodes) {
        if (child.nodeType === 3) {
          out += xml(child.nodeValue);
          continue;
        }
        if (child.nodeType !== 1) continue;
        const name = child.tagName.toLowerCase();
        if (name === "i" || name === "em") out += `<emphasis>${walk(child)}</emphasis>`;
        else if (name === "b" || name === "strong") out += `<strong>${walk(child)}</strong>`;
        else out += walk(child);
      }
      return out;
    };
    return walk(fragment(markup)).trim();
  }

  async function buildEpub(story, t, { cover = null } = {}) {
    const entries = [
      ["mimetype", "application/epub+zip", false],
      ["META-INF/container.xml", CONTAINER, true],
      ["OEBPS/style.css", STYLE, true],
      ["OEBPS/nav.xhtml", nav(story), true],
      ["OEBPS/toc.ncx", ncx(story), true],
    ];
    if (cover) {
      entries.push(["OEBPS/cover.jpg", cover, true]);
      entries.push(["OEBPS/cover.xhtml", coverPage(story), true]);
    }
    story.chapters.forEach((chapter, index) => {
      entries.push([`OEBPS/chapter-${pad(index + 1)}.xhtml`, chapterPage(chapter.title, chapter.paragraphs), true]);
    });
    entries.push(["OEBPS/content.opf", opf(story, t, Boolean(cover)), true]);
    return zip(entries);
  }

  const CONTAINER = `<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>
`;

  function opf(story, t, hasCover) {
    const creators = [];
    (story.authors.length ? story.authors : [story.author]).forEach((name, i) => {
      creators.push(`<dc:creator id="author-${i + 1}">${xml(name)}</dc:creator>`);
      creators.push(`<meta refines="#author-${i + 1}" property="role" scheme="marc:relators">aut</meta>`);
    });
    story.translators.forEach((name, i) => {
      creators.push(`<dc:contributor id="translator-${i + 1}">${xml(name)}</dc:contributor>`);
      creators.push(`<meta refines="#translator-${i + 1}" property="role" scheme="marc:relators">trl</meta>`);
    });
    const subjects = [...story.fandoms, ...story.directions, ...story.pairings, ...story.tags]
      .filter(Boolean)
      .map((value) => `<dc:subject>${xml(value)}</dc:subject>`);
    let series = "";
    if (story.series_name) {
      series =
        `<meta property="belongs-to-collection" id="series">${xml(story.series_name)}</meta>` +
        '<meta refines="#series" property="collection-type">series</meta>' +
        `<meta name="calibre:series" content="${attr(story.series_name)}"/>`;
      if (story.series_index) {
        series +=
          `<meta refines="#series" property="group-position">${story.series_index}</meta>` +
          `<meta name="calibre:series_index" content="${story.series_index}"/>`;
      }
    }
    const coverMeta = hasCover ? '<meta name="cover" content="cover-image"/>' : "";
    const coverItem = hasCover
      ? '<item id="cover-image" href="cover.jpg" media-type="image/jpeg" properties="cover-image"/>' +
        '<item id="cover" href="cover.xhtml" media-type="application/xhtml+xml"/>'
      : "";
    const coverSpine = hasCover ? '<itemref idref="cover"/>' : "";
    const manifest = story.chapters.map(
      (_, i) => `<item id="chapter-${i + 1}" href="chapter-${pad(i + 1)}.xhtml" media-type="application/xhtml+xml"/>`
    );
    const spine = story.chapters.map((_, i) => `<itemref idref="chapter-${i + 1}"/>`);
    const parts = [story.description];
    if (story.dedication) parts.push(`${t("dedication")}: ` + story.dedication);
    if (story.notes) parts.push(story.notes);
    const description = parts.filter(Boolean).join("\n\n");
    return `<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" unique-identifier="bookid" version="3.0" xml:lang="${xml(story.language)}">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:identifier id="bookid">${xml(story.url)}</dc:identifier>
    <dc:title>${xml(story.title)}</dc:title>
    ${creators.join("\n")}
    <dc:language>${xml(story.language)}</dc:language>
    <dc:description>${xml(description)}</dc:description>
    <dc:source>${xml(story.url)}</dc:source>
    <dc:publisher>ficbook.net</dc:publisher>
    ${subjects.join("\n")}
    ${series}
    ${coverMeta}
  </metadata>
  <manifest>
    <item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>
    <item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>
    <item id="style" href="style.css" media-type="text/css"/>
    ${coverItem}
    ${manifest.join("\n")}
  </manifest>
  <spine toc="ncx">
    ${coverSpine}
    ${spine.join("\n")}
  </spine>
</package>
`;
  }

  function nav(story) {
    const items = story.chapters.map((chapter, i) => `<li><a href="chapter-${pad(i + 1)}.xhtml">${xml(chapter.title)}</a></li>`);
    return `<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="${xml(story.language)}">
  <head><title>${xml(story.title)}</title></head>
  <body>
    <nav epub:type="toc" id="toc">
      <h1>${xml(story.title)}</h1>
      <ol>
        ${items.join("\n")}
      </ol>
    </nav>
  </body>
</html>
`;
  }

  function ncx(story) {
    const points = story.chapters.map(
      (chapter, i) => `<navPoint id="chapter-${i + 1}" playOrder="${i + 1}">
      <navLabel><text>${xml(chapter.title)}</text></navLabel>
      <content src="chapter-${pad(i + 1)}.xhtml"/>
    </navPoint>`
    );
    return `<?xml version="1.0" encoding="UTF-8"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
  <head>
    <meta name="dtb:uid" content="${attr(story.url)}"/>
    <meta name="dtb:depth" content="1"/>
    <meta name="dtb:totalPageCount" content="0"/>
    <meta name="dtb:maxPageNumber" content="0"/>
  </head>
  <docTitle><text>${xml(story.title)}</text></docTitle>
  <navMap>
    ${points.join("\n")}
  </navMap>
</ncx>
`;
  }

  function coverPage(story) {
    return `<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="${xml(story.language)}">
  <head>
    <title>${xml(story.title)}</title>
    <link rel="stylesheet" type="text/css" href="style.css"/>
  </head>
  <body>
    <p class="cover"><img src="cover.jpg" alt="${attr(story.title)}"/></p>
  </body>
</html>
`;
  }

  function chapterPage(title, paragraphs) {
    const blocks = [`<h1>${xml(title)}</h1>`];
    for (const paragraph of paragraphs) {
      if (paragraph.trim()) blocks.push(epubParagraph(paragraph));
    }
    return `<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
  <head>
    <title>${xml(title)}</title>
    <link rel="stylesheet" type="text/css" href="style.css"/>
  </head>
  <body>
    ${blocks.join("\n")}
  </body>
</html>
`;
  }

  /* A paragraph must be well-formed XML inside an EPUB; fall back to its plain text. */
  function epubParagraph(markup) {
    const wrapped = `<p>${markup}</p>`;
    const parsed = new root.DOMParser().parseFromString(`<body>${wrapped}</body>`, "application/xml");
    if (!parsed.getElementsByTagName("parsererror").length) return wrapped;
    return `<p>${escapeHtml(fragment(markup).textContent)}</p>`;
  }

  /* A minimal ZIP writer: deflate where the web view supports it, stored otherwise. */
  async function zip(entries) {
    const encoder = new TextEncoder();
    const locals = [];
    const centrals = [];
    let offset = 0;
    for (const [name, content, compress] of entries) {
      const raw = typeof content === "string" ? encoder.encode(content) : content;
      let data = raw;
      let method = 0;
      if (compress && typeof root.CompressionStream === "function") {
        data = await deflate(raw);
        method = 8;
      }
      const nameBytes = encoder.encode(name);
      const crc = crc32(raw);
      const local = new DataView(new ArrayBuffer(30));
      local.setUint32(0, 0x04034b50, true);
      local.setUint16(4, 20, true);
      local.setUint16(6, 0x0800, true);
      local.setUint16(8, method, true);
      local.setUint16(10, 0, true);
      local.setUint16(12, 33, true);
      local.setUint32(14, crc, true);
      local.setUint32(18, data.length, true);
      local.setUint32(22, raw.length, true);
      local.setUint16(26, nameBytes.length, true);
      locals.push(new Uint8Array(local.buffer), nameBytes, data);
      const central = new DataView(new ArrayBuffer(46));
      central.setUint32(0, 0x02014b50, true);
      central.setUint16(4, 20, true);
      central.setUint16(6, 20, true);
      central.setUint16(8, 0x0800, true);
      central.setUint16(10, method, true);
      central.setUint16(12, 0, true);
      central.setUint16(14, 33, true);
      central.setUint32(16, crc, true);
      central.setUint32(20, data.length, true);
      central.setUint32(24, raw.length, true);
      central.setUint16(28, nameBytes.length, true);
      central.setUint32(42, offset, true);
      centrals.push(new Uint8Array(central.buffer), nameBytes);
      offset += 30 + nameBytes.length + data.length;
    }
    const centralSize = centrals.reduce((sum, part) => sum + part.length, 0);
    const end = new DataView(new ArrayBuffer(22));
    end.setUint32(0, 0x06054b50, true);
    end.setUint16(8, entries.length, true);
    end.setUint16(10, entries.length, true);
    end.setUint32(12, centralSize, true);
    end.setUint32(16, offset, true);
    return concat([...locals, ...centrals, new Uint8Array(end.buffer)]);
  }

  async function deflate(bytes) {
    const stream = new Blob([bytes]).stream().pipeThrough(new root.CompressionStream("deflate-raw"));
    return new Uint8Array(await new Response(stream).arrayBuffer());
  }

  const CRC_TABLE = (() => {
    const table = new Uint32Array(256);
    for (let n = 0; n < 256; n++) {
      let c = n;
      for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
      table[n] = c >>> 0;
    }
    return table;
  })();

  function crc32(bytes) {
    let crc = 0xffffffff;
    for (let i = 0; i < bytes.length; i++) crc = CRC_TABLE[(crc ^ bytes[i]) & 0xff] ^ (crc >>> 8);
    return (crc ^ 0xffffffff) >>> 0;
  }

  function concat(parts) {
    const out = new Uint8Array(parts.reduce((sum, part) => sum + part.length, 0));
    let at = 0;
    for (const part of parts) {
      out.set(part, at);
      at += part.length;
    }
    return out;
  }

  function fragment(markup) {
    const template = root.document.createElement("template");
    template.innerHTML = markup;
    return template.content;
  }

  function plainParagraphs(value) {
    return (value || "")
      .split(/\r\n|[\n\r\v\f\x1c-\x1e\x85\u2028\u2029]/)
      .map((line) => line.trim())
      .filter(Boolean);
  }

  function toBase64(bytes) {
    let binary = "";
    for (let i = 0; i < bytes.length; i += 0x8000) binary += String.fromCharCode(...bytes.subarray(i, i + 0x8000));
    return root.btoa(binary);
  }

  function fromBase64(value) {
    const binary = root.atob(value);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
    return bytes;
  }

  function isoToday() {
    const now = new Date();
    return [now.getFullYear(), String(now.getMonth() + 1).padStart(2, "0"), String(now.getDate()).padStart(2, "0")].join("-");
  }

  function pad(n) {
    return String(n).padStart(3, "0");
  }

  function xml(value) {
    return String(value || "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  function attr(value) {
    return escapeHtml(value || "");
  }

  function escapeHtml(value) {
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#x27;");
  }

  const api = { renderTxt, buildFb2, buildEpub, chapterBody, toBase64, fromBase64 };
  root.FicbookBooks = api;
  if (typeof module === "object" && module.exports) module.exports = api;
})(typeof globalThis !== "undefined" ? globalThis : this);
