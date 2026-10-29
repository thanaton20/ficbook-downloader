// Run the shared web core under jsdom for tests/parity.py. Reads cases as JSON on stdin.
const fs = require("fs");
const path = require("path");
const { JSDOM } = require("jsdom");

const web = path.join(__dirname, "..", "shared", "web");
const parse = require(path.join(web, "parse.js"));
const books = require(path.join(web, "books.js"));

async function main() {
  const cases = JSON.parse(fs.readFileSync(0, "utf8"));
  const results = [];
  for (const item of cases) {
    const dom = new JSDOM(item.html || "<html></html>", { url: item.url || "https://ficbook.net/" });
    globalThis.document = dom.window.document;
    globalThis.DOMParser = dom.window.DOMParser;
    if (item.kind === "books") {
      const t = (key) => item.labels[key];
      const cover = item.cover ? books.fromBase64(item.cover) : null;
      results.push({
        txt: books.renderTxt(item.story, t),
        fb2: books.buildFb2(item.story, t, { version: item.version, cover, today: item.today }),
        epub: books.toBase64(await books.buildEpub(item.story, t, { cover })),
        stem: parse.fileStem(item.story),
      });
    } else if (item.kind === "canonical") {
      results.push(item.values.map((value) => {
        try {
          return { ok: true, data: parse[item.fn](value) };
        } catch (error) {
          return { ok: false, error: error.code };
        }
      }));
    } else {
      results.push(parse.run(item.kind, item.args, dom.window.document));
    }
  }
  process.stdout.write(JSON.stringify(results));
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
