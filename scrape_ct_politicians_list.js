import puppeteer from "puppeteer-extra";
import StealthPlugin from "puppeteer-extra-plugin-stealth";
import { timeoutPromise } from "./custom_helpers_js/utilities.js";
import { registerGracefulExit } from "./custom_helpers_js/gracefulExit.js";
import { join } from "path";
import UserAgent from "user-agents";
import { getOutFolderCapitolTrades } from "./custom_helpers_js/getPaths.js";
import { writeFileSync } from "fs";

const main = async () => {
  // File paths
  const OUT_FILE_PATH = join(
    getOutFolderCapitolTrades(),
    "politician_list.json"
  );

  // Run constants
  const NEXT_PAGE_DELAY = 2 * 1000;
  const PAGE_LOAD_DELAY = 5 * 1000;

  // Puppeteer initializers
  const initializeBrowser = async () => {
    return await puppeteer.launch({ headless: "new" });
  };

  const initializePage = async (browser) => {
    const page = await browser.newPage();
    const userAgent = new UserAgent().toString();
    await page.setUserAgent(userAgent);
    await page.setViewport({
      width: 1920,
      height: 1080,
      deviceScaleFactor: 1,
    });
    await page.setRequestInterception(true);

    const blockResourceType = [
      "font",
      "image",
      "imageset",
      "media",
      "stylesheet",
    ];

    const blockResourceName = [
      "adition",
      "adzerk",
      "analytics",
      "cdn.api.twitter",
      "clicksor",
      "clicktale",
      "doubleclick",
      "exelator",
      "facebook",
      "fontawesome",
      "google",
      "google-analytics",
      "googletagmanager",
      "mixpanel",
      "optimizely",
      "quantserve",
      "sharethrough",
      "tiqcdn",
      "zedo",
    ];

    page.on("request", (request) => {
      const requestUrl = request._url ? request._url.split("?")[0] : "";
      if (
        request.resourceType() in blockResourceType ||
        blockResourceName.some((resource) => requestUrl.includes(resource))
      ) {
        request.abort();
      } else {
        request.continue();
      }
    });
    return page;
  };

  // Initialize browser and page
  puppeteer.use(StealthPlugin());
  let browser = await initializeBrowser();
  let page = await initializePage(browser);

  // Register graceful exit
  let forcedStop = false;
  registerGracefulExit(() => {
    forcedStop = true;
    browser.close();
    process.exit();
  });

  // Get necessary cookies and states for page

  const numPages = 3;

  let dataToSave = [];

  for (let i = 0; i < numPages; i++) {
    let pageParam = "";
    if (i > 0) {
      pageParam = "&page=" + (i + 1);
    }

    const PAGE_URL =
      "https://www.capitoltrades.com/politicians?per_page=96" + pageParam;

    console.log(PAGE_URL);

    await page.goto(PAGE_URL);

    await timeoutPromise(PAGE_LOAD_DELAY);

    const pageResults = await page.evaluate(evaluatePage);

    console.log(pageResults.length);
    dataToSave = [...dataToSave, ...pageResults];

    await timeoutPromise(NEXT_PAGE_DELAY);
  }

  writeFileSync(OUT_FILE_PATH, JSON.stringify(dataToSave, null, 4), {
    encoding: "utf-8",
  });
  process.exit();
};

function evaluatePage() {
  const cardElList = document.querySelectorAll("a.index-card-link");
  const toReturn = [];
  cardElList.forEach((card) => {
    const politicianPageLink = card.href;
    const politicianId = politicianPageLink.split("/")[4];

    const fullName = card.querySelector("h2").innerText;

    let party = "";
    const partyEl = card.querySelector("h3 span.party");
    if (partyEl) party = partyEl.innerText;

    let state = "";
    const stateEl = card.querySelector("h3 span.us-state-full");
    if (stateEl) state = stateEl.innerText;

    let trades = "";
    const tradesEl = card.querySelector("div.cell--count-trades div.q-value");
    if (tradesEl) trades = tradesEl.innerText;

    let issuers = "";
    const issuersEl = card.querySelector("div.cell--count-issuers div.q-value");
    if (issuersEl) issuers = issuersEl.innerText;

    let volume = "";
    const volumeEl = card.querySelector("div.cell--volume div.q-value");
    if (volumeEl) volume = volumeEl.innerText;

    let lastTraded = "";
    const lastTradedEl = card.querySelector(
      "div.cell--last-traded div.q-value"
    );
    if (lastTradedEl) lastTraded = lastTradedEl.innerText;

    const toAdd = {
      politicianPageLink,
      politicianId,
      fullName,
      party,
      state,
      trades,
      issuers,
      volume,
      lastTraded,
    };

    toReturn.push(toAdd);
  });

  return toReturn;
}

main();
