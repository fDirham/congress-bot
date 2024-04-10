import puppeteer from "puppeteer-extra";
import StealthPlugin from "puppeteer-extra-plugin-stealth";
import {
  getDateAsFileName,
  timeoutPromise,
} from "./custom_helpers_js/utilities.js";
import { registerGracefulExit } from "./custom_helpers_js/gracefulExit.js";
import { join } from "path";
import UserAgent from "user-agents";
import { getOutFolder } from "./custom_helpers_js/getPaths.js";
import { writeFileSync } from "fs";
import yargs from "yargs/yargs";
import { hideBin } from "yargs/helpers";

const main = async () => {
  // Process input arguments
  const argv = yargs(hideBin(process.argv))
    .scriptName("scrape individual politicians")
    .option("startPage", {
      alias: "s",
      type: "number",
      default: 0,
    })
    .option("endPage", {
      alias: "e",
      type: "number",
      default: 0,
    }).argv;

  let { startPage, endPage } = argv;

  // File paths
  const OUT_FOLDER_PATH = join(getOutFolder(), "trendspider", "scrapes");

  // Run constants
  const NEXT_PAGE_DELAY = 2 * 1000;
  const PAGE_LOAD_DELAY = 5 * 1000;

  const MAX_PAGES = 870;

  // Puppeteer initializers
  const initializeBrowser = async () => {
    return await puppeteer.launch({ headless: false });
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

  if (endPage < 2) {
    endPage = MAX_PAGES + 1;
  }

  const PAGE_URL = "https://trendspider.com/markets/congress-trading/";

  await page.goto(PAGE_URL);

  const BASE_FILE_NAME = getDateAsFileName();
  for (let i = 0; i < endPage; i++) {
    if (i < startPage) {
      await page.click("a.next");
      await timeoutPromise(NEXT_PAGE_DELAY);
      continue;
    }

    console.log("Scraping page", i);

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

    await page.click("a.next");
    await timeoutPromise(NEXT_PAGE_DELAY);
  }

  process.exit();
};

function evaluatePage() {
  const rowElList = document.querySelectorAll("tbody>tr");

  const toReturn = [];
  rowElList.forEach((row) => {
    let ticker = "";
    let assetName = "";
    const stock = row.querySelector("td.-stock").innerText;
    if (stock) {
      ticker = stock.split("\n")[0];
      assetName = stock.split("\n")[1];
    }

    let politicianName = "";
    let party = "";
    let chamber = "";
    const politician = row.querySelector("td.-politician").innerText;
    if (politician) {
      const politicianLines = politician.split("\n");
      politicianName = politicianLines[0];
      const rest = politicianLines[1];
      party = rest[0];
      if (rest.endsWith("Senate")) {
        chamber = "S";
      } else {
        chamber = "H";
      }
    }

    let txType = "";
    let amount = "";
    const transaction = row.querySelector("td.-transaction").innerText;
    if (transaction) {
      const txLines = transaction.split("\n");
      txType = txLines[0];
      amount = txLines[1];
    }

    const excessReturn = row.querySelector("td.-excess-return").innerText;
    const traded = row.querySelector("td.-traded").innerText;
    const filed = row.querySelector("td.-filed").innerText;

    toReturn.push({
      ticker,
      assetName,
      politicianName,
      party,
      chamber,
      txType,
      amount,
      excessReturn,
      traded,
      filed,
    });
  });

  return toReturn;
}

main();
