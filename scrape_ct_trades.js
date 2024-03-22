import puppeteer from "puppeteer-extra";
import StealthPlugin from "puppeteer-extra-plugin-stealth";
import {
  getDateAsFileName,
  timeoutPromise,
} from "./custom_helpers_js/utilities.js";
import { registerGracefulExit } from "./custom_helpers_js/gracefulExit.js";
import { join } from "path";
import UserAgent from "user-agents";
import { getOutFolderCapitolTrades } from "./custom_helpers_js/getPaths.js";
import { writeFileSync } from "fs";
import yargs from "yargs/yargs";
import { hideBin } from "yargs/helpers";
import { endianness } from "os";

const main = async () => {
  // Process input arguments
  const argv = yargs(hideBin(process.argv))
    .scriptName("scrape individual politicians")
    .option("startPage", {
      alias: "s",
      type: "number",
      default: 1,
    })
    .option("endPage", {
      alias: "e",
      type: "number",
      default: 0,
    }).argv;

  let { startPage, endPage } = argv;

  // File paths
  const OUT_FOLDER_PATH = join(getOutFolderCapitolTrades(), "trade_scrapes");

  // Run constants
  const NEXT_PAGE_DELAY = 2 * 1000;
  const PAGE_LOAD_DELAY = 5 * 1000;

  const MAX_PAGES = 397;

  // Puppeteer initializers
  const initializeBrowser = async () => {
    return await puppeteer.launch({ headless: "new" });
  };

  const initializePage = async (browser) => {
    const page = await browser.newPage();
    const userAgent = new UserAgent({ deviceCategory: "desktop" }).toString();
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

  if (endPage < 2) {
    endPage = MAX_PAGES + 1;
  }

  const BASE_FILE_NAME = getDateAsFileName();
  for (let i = startPage; i < endPage; i++) {
    let pageParam = "";
    if (i > 1) {
      pageParam = "&page=" + i;
    }

    console.log("Scraping page", i);

    const PAGE_URL =
      "https://www.capitoltrades.com/trades?per_page=96" + pageParam;

    await page.goto(PAGE_URL);

    await timeoutPromise(PAGE_LOAD_DELAY);

    const pageResults = await page.evaluate(evaluatePage);

    console.log("Retrieved", pageResults.length);

    const toWrite = {
      todayDate: new Date().toISOString(),
      dataList: pageResults,
    };

    const OUT_FILE_PATH = join(
      OUT_FOLDER_PATH,
      BASE_FILE_NAME + "_" + i + ".json"
    );
    writeFileSync(OUT_FILE_PATH, JSON.stringify(toWrite, null, 4), {
      encoding: "utf-8",
    });
    await timeoutPromise(NEXT_PAGE_DELAY);
  }

  process.exit();
};

function evaluatePage() {
  const rowElList = document.querySelectorAll(
    "table.trades-table tbody tr.q-tr"
  );

  const toReturn = [];
  rowElList.forEach((row) => {
    const toAdd = {};
    const politicianTd = row.querySelector("td.q-column--politician");
    if (politicianTd) {
      const nameEl = politicianTd.querySelector("h3 a");
      const pageLink = nameEl.href;
      const id = pageLink.split("/")[4];
      const fullName = nameEl.innerText;
      toAdd.politician = {
        fullName,
        id,
        pageLink,
      };
    }

    const issuerTd = row.querySelector("td.q-column--issuer");
    if (issuerTd) {
      const nameEl = issuerTd.querySelector("h3 a");
      const pageLink = nameEl.href;
      const id = pageLink.split("/")[4];
      const issuerName = nameEl.innerText;
      const tickerEl = issuerTd.querySelector("span.issuer-ticker");
      let ticker = "";
      if (tickerEl) {
        ticker = tickerEl.innerText;
      }

      toAdd.issuer = {
        issuerName,
        ticker,
        id,
        pageLink,
      };
    }

    const pubDateTd = row.querySelector("td.q-column--pubDate");
    if (pubDateTd) {
      const value = pubDateTd.querySelector("div.q-value").innerText;
      const label = pubDateTd.querySelector("div.q-label").innerText;

      toAdd.pubDate = {
        value,
        label,
      };
    }

    const txDateTd = row.querySelector("td.q-column--txDate");
    if (txDateTd) {
      const value = txDateTd.querySelector("div.q-value").innerText;
      const label = txDateTd.querySelector("div.q-label").innerText;

      toAdd.txDate = {
        value,
        label,
      };
    }

    const reportingGapTd = row.querySelector("td.q-column--reportingGap");
    if (reportingGapTd) {
      const value = reportingGapTd.querySelector("div.q-value").innerText;
      const label = reportingGapTd.querySelector("div.q-label").innerText;

      toAdd.reportingGap = value + " " + label;
    }

    const ownerTd = row.querySelector("td.q-column--owner");
    if (ownerTd) {
      const label = ownerTd.querySelector("span.q-label").innerText;
      toAdd.owner = label;
    }

    const txTypeTd = row.querySelector("td.q-column--txType");
    if (txTypeTd) {
      toAdd.txType = txTypeTd.innerText;
    }

    const valueTd = row.querySelector("td.q-column--value");
    if (valueTd) {
      toAdd.value = valueTd.querySelector("span.q-label").innerText;
    }

    const priceTd = row.querySelector("td.q-column--price");
    if (priceTd) {
      toAdd.price = priceTd.innerText;
    }

    const txIdTd = row.querySelector("td.q-column--_txId");
    if (txIdTd) {
      toAdd.txId = txIdTd.querySelector("a").href;
    }

    toReturn.push(toAdd);
  });

  return toReturn;
}

main();
