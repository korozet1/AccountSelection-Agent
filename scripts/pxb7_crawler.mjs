import { chromium } from "playwright";

const url = process.argv[2];
const requestedMaxItems = Number(process.argv[3] || 60);
const maxItems = Math.min(Math.max(requestedMaxItems || 60, 1), 200);
const minPrice = process.argv[4] ? Number(process.argv[4]) : null;
const maxPrice = process.argv[5] ? Number(process.argv[5]) : null;
const chromePath = process.env.CHROME_PATH || "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";

if (!url) {
  console.error(JSON.stringify({ success: false, error: "missing url" }));
  process.exit(2);
}

function normalizeItems(items) {
  return items.filter(isInBudget).slice(0, maxItems).map((item, index) => ({
    index: index + 1,
    product_id: item.productId || item.product_id || item.id || "",
    product_unique_no: item.productUniqueNo || item.product_unique_no || item.uniqueNo || "",
    game_name: item.gameName || item.game_name || "",
    price: typeof item.price === "number" ? item.price / 100 : null,
    title: item.showTitle || item.productName || item.title || item.name || "",
    attr_names: item.attrNameList || item.attr_names || item.tags || [],
    url: (item.productId || item.product_id || item.id)
      ? `https://www.pxb7.com/product/${item.productId || item.product_id || item.id}`
      : "",
    image: item.mainImageUrl || item.image || item.cover || "",
    hot_count_text: item.hotCountText || item.hot_count_text || "",
    shelve_up_time_text: item.shelveUpTimeText || item.shelve_up_time_text || "",
  }));
}

function itemPrice(item) {
  return typeof item.price === "number" ? item.price / 100 : null;
}

function isInBudget(item) {
  const price = itemPrice(item);
  if (price === null) return false;
  if (minPrice !== null && Number.isFinite(minPrice) && price < minPrice) return false;
  if (maxPrice !== null && Number.isFinite(maxPrice) && price > maxPrice) return false;
  return true;
}

function looksLikeProduct(item) {
  if (!item || typeof item !== "object" || Array.isArray(item)) return false;
  const hasId = item.productId || item.productUniqueNo || item.product_id || item.uniqueNo || item.id;
  const hasTitle = item.showTitle || item.productName || item.title || item.name;
  return Boolean(hasId && (hasTitle || typeof item.price === "number"));
}

function extractItems(json) {
  if (!json || typeof json !== "object") return [];
  const directArrays = [
    json.data,
    json.data?.list,
    json.data?.records,
    json.data?.rows,
    json.list,
    json.records,
  ];
  for (const value of directArrays) {
    if (Array.isArray(value) && value.some(looksLikeProduct)) {
      return value.filter(looksLikeProduct);
    }
  }

  const found = [];
  const seen = new Set();
  const visit = (value) => {
    if (!value || typeof value !== "object") return;
    if (seen.has(value)) return;
    seen.add(value);

    if (Array.isArray(value)) {
      if (value.some(looksLikeProduct)) {
        found.push(...value.filter(looksLikeProduct));
        return;
      }
      for (const item of value) visit(item);
      return;
    }

    for (const child of Object.values(value)) visit(child);
  };
  visit(json);
  return found;
}

function isLikelyProductResponse(responseUrl) {
  try {
    const parsed = new URL(responseUrl);
    if (!parsed.hostname.includes("pxb7.com")) return false;
    const path = parsed.pathname.toLowerCase();
    return (
      path.includes("/api/") &&
      (path.includes("product") ||
        path.includes("goods") ||
        path.includes("search") ||
        path.includes("list"))
    );
  } catch {
    return false;
  }
}

async function collectScrollableTargets(page) {
  return await page.evaluate(() => {
    const documentElement = document.documentElement;
    const body = document.body;
    const selectors = [];
    const candidates = [documentElement, body, ...document.querySelectorAll("*")];

    for (const element of candidates) {
      const style = window.getComputedStyle(element);
      const canScroll =
        element.scrollHeight > element.clientHeight + 80 &&
        !["hidden", "clip"].includes(style.overflowY);
      if (!canScroll) continue;

      if (element === documentElement || element === body) {
        selectors.push({ type: "window", distance: element.scrollHeight - element.clientHeight });
      } else if (element.id) {
        selectors.push({ type: "selector", selector: `#${CSS.escape(element.id)}`, distance: element.scrollHeight - element.clientHeight });
      } else {
        const className = Array.from(element.classList || []).slice(0, 2).map((name) => `.${CSS.escape(name)}`).join("");
        if (className) selectors.push({ type: "selector", selector: `${element.tagName.toLowerCase()}${className}`, distance: element.scrollHeight - element.clientHeight });
      }
    }

    return selectors
      .sort((a, b) => b.distance - a.distance)
      .filter((target, index, array) => array.findIndex((item) => item.type === target.type && item.selector === target.selector) === index)
      .slice(0, 8);
  });
}

async function scrollForLazyLoad(page, targets, round) {
  await page.mouse.wheel(0, 700 + round * 80);
  await wait(300);

  for (const target of targets) {
    if (target.type === "window") {
      await page.evaluate(() => {
        window.scrollBy({ top: Math.max(window.innerHeight * 0.85, 600), behavior: "instant" });
      });
    } else {
      await page.locator(target.selector).first().evaluate((element) => {
        element.scrollTop = Math.min(
          element.scrollTop + Math.max(element.clientHeight * 0.85, 500),
          element.scrollHeight,
        );
      }).catch(() => {});
    }
  }

  await page.evaluate(() => {
    window.dispatchEvent(new Event("scroll"));
    document.dispatchEvent(new Event("scroll", { bubbles: true }));
  });
}

async function wait(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function main() {
  const browser = await chromium.launch({
    headless: true,
    executablePath: chromePath,
    args: [
      "--disable-blink-features=AutomationControlled",
      "--no-sandbox",
      "--disable-dev-shm-usage",
    ],
  });

  const context = await browser.newContext({
    viewport: { width: 1366, height: 900 },
    userAgent:
      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 " +
      "Chrome/120.0.0.0 Safari/537.36",
  });

  // Anti-detection: hide Playwright automation markers
  await context.addInitScript(() => {
    Object.defineProperty(navigator, "webdriver", { get: () => false });
    Object.defineProperty(navigator, "plugins", { get: () => [1, 2, 3, 4, 5] });
    Object.defineProperty(navigator, "languages", { get: () => ["zh-CN", "zh", "en"] });
    window.chrome = { runtime: {} };
  });

  const page = await context.newPage();

  const responses = [];
  const itemMap = new Map();

  page.on("response", async (response) => {
    const responseUrl = response.url();
    if (!isLikelyProductResponse(responseUrl)) return;
    try {
      const text = await response.text();
      if (responses.length < 30) {
        responses.push({ url: responseUrl, status: response.status(), preview: text.slice(0, 200) });
      }
      if (!text.trim().startsWith("{")) return; // anti-bot challenge (HTML), skip
      const json = JSON.parse(text);
      for (const item of extractItems(json)) {
        const key =
          item.productId ||
          item.productUniqueNo ||
          item.product_id ||
          item.uniqueNo ||
          item.id ||
          JSON.stringify(item).slice(0, 120);
        if (!itemMap.has(key)) itemMap.set(key, item);
      }
    } catch {
      // WAF / interrupted reads — expected, keep listening
    }
  });

  // Use networkidle to wait for JS to execute and anti-bot challenges to resolve
  await page.goto(url, { waitUntil: "networkidle", timeout: 90000 });

  // Wait a bit more for the anti-bot cookie to be set and first API calls to fire
  await wait(3000);

  // Initial collection before scrolling
  let initialCount = itemMap.size;
  console.error(`[crawler] Initial items after page load: ${initialCount}`);

  const maxScrolls = Math.min(Math.max(Math.ceil(maxItems / 6) + 12, 16), 60);
  const scrollTargets = await collectScrollableTargets(page);
  console.error(`[crawler] Scroll targets: ${scrollTargets.length}`);
  let staleRounds = 0;
  let lastCount = initialCount;

  for (let round = 0; round < maxScrolls; round += 1) {
    await scrollForLazyLoad(page, scrollTargets, round);
    await wait(1800);

    const current = itemMap.size;
    console.error(`[crawler] Scroll ${round + 1}: ${current} items collected`);
    if (current <= lastCount) {
      staleRounds += 1;
    } else {
      staleRounds = 0;
    }
    lastCount = current;

    if (staleRounds >= 6) break;
    if (normalizeItems(Array.from(itemMap.values())).length >= maxItems) break;
  }

  const items = Array.from(itemMap.values());
  const filteredItems = normalizeItems(items);

  if (!items.length || !filteredItems.length) {
    const bodyText = await page.locator("body").innerText().catch(() => "");
    await browser.close();
    console.log(
      JSON.stringify(
        {
          success: false,
          error: items.length
            ? "抓到了商品，但预算区间内没有匹配账号。"
            : "未能从螃蟹列表页抓到商品接口数据，可能需要登录、验证码或平台反爬校验。",
          responses,
          total_collected: items.length,
          budget: { min_price: minPrice, max_price: maxPrice },
          page_text_preview: bodyText.slice(0, 1000),
        },
        null,
        2,
      ),
    );
    process.exit(1);
  }

  await browser.close();
  console.log(
    JSON.stringify(
      {
        success: true,
        items: filteredItems,
        total_collected: items.length,
        total_after_budget: filteredItems.length,
        max_items: maxItems,
        budget: { min_price: minPrice, max_price: maxPrice },
      },
      null,
      2,
    ),
  );
}

main().catch((error) => {
  console.error(JSON.stringify({ success: false, error: error.message }, null, 2));
  process.exit(1);
});
