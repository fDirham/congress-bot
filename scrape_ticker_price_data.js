import puppeteer from "puppeteer-extra";
import StealthPlugin from "puppeteer-extra-plugin-stealth";
import {
  getPercentageString,
  timeoutPromise,
} from "./custom_helpers_js/utilities.js";
import { registerGracefulExit } from "./custom_helpers_js/gracefulExit.js";
import yargs from "yargs/yargs";
import { hideBin } from "yargs/helpers";
import { join } from "path";
import UserAgent from "user-agents";
import { getOutFolderAnalysis } from "./custom_helpers_js/getPaths.js";
import { readFileSync, writeFileSync, readdirSync, renameSync } from "fs";

const main = async () => {
  // Process input arguments
  const argv = yargs(hideBin(process.argv)).argv;
  let { startIndex, endIndex, skipDone } = argv;

  if (startIndex) {
    startIndex = parseInt(startIndex);
  } else {
    startIndex = 0;
  }

  if (endIndex) {
    endIndex = parseInt(endIndex);
  } else {
    endIndex = -1;
  }

  // File paths
  const TICKER_LIST_FILE_PATH = join(
    getOutFolderAnalysis(),
    "unique_ticker_df.json"
  );

  const OUT_FOLDER_PATH = join(getOutFolderAnalysis(), "ticker_prices");

  // Run constants
  const NAV_TIMEOUT = 30 * 1000;
  const DOWNLOAD_DELAY = 1000;
  const BUTTON_FOUND_TO_CLICK_DELAY = 1 * 1000;
  const BUTTON_TO_DOWNLOAD_DELAY = 1 * 1000;
  const CHECK_DOWNLOAD_DELAY = 1000;
  const NEXT_PAGE_DELAY = 3 * 1000;
  const RETRY_DELAY = 5 * 1000;
  const CHECK_BUTTON_DELAY = 500;

  // Puppeteer initializers
  const initializeBrowser = async () => {
    return await puppeteer.launch({
      headless: false,
      args: ["--window-size=500,500", "--window-position=-1920,0"],
    });
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
    await page.setDefaultNavigationTimeout(NAV_TIMEOUT);
    page.on("request", (req) => {
      if (
        // req.resourceType() == "stylesheet" ||
        req.resourceType() == "font" ||
        req.resourceType() == "image"
      ) {
        req.abort();
      } else {
        req.continue();
      }
    });
    await page._client().send("Page.setDownloadBehavior", {
      behavior: "allow",
      downloadPath: OUT_FOLDER_PATH,
    });

    return page;
  };

  // Initialize browser and page
  puppeteer.use(StealthPlugin());

  let browser = await initializeBrowser();
  let page = await initializePage(browser);

  const refreshBrowser = async () => {
    browser.close();
    browser = await initializeBrowser();
    page = await initializePage(browser);
  };

  // Register graceful exit
  let forcedStop = false;
  registerGracefulExit(() => {
    forcedStop = true;
    browser.close();
  });

  // Main logic
  const tickerListContents = readFileSync(TICKER_LIST_FILE_PATH, {
    encoding: "utf-8",
  });
  const tickerList = JSON.parse(tickerListContents);

  const alreadyDownloadedTickerList = readdirSync(OUT_FOLDER_PATH).map(
    (fileName) => fileName.replace(".csv", "")
  );
  const alreadyDownloadedSet = {};
  alreadyDownloadedTickerList.forEach((ticker) => {
    alreadyDownloadedSet[ticker.toUpperCase()] = true;
  });

  if (endIndex == -1) {
    endIndex = tickerList.length;
  }
  for (let i = startIndex; i < endIndex; i++) {
    if (forcedStop) {
      break;
    }

    let { ticker } = tickerList[i];

    if (skipDone && alreadyDownloadedSet[ticker]) {
      console.log("SKIPPING", i, ticker);
      continue;
    }

    console.log("START", i, ticker);
    const startFolderFiles = readdirSync(OUT_FOLDER_PATH);

    ticker = ticker.toLowerCase();
    const urlToScrape = `https://www.nasdaq.com/market-activity/stocks/${ticker}/historical`;

    const MAX_NAV_ATTEMPTS = 5;
    let isSuccessNav = false;
    for (let j = 0; j < MAX_NAV_ATTEMPTS; j++) {
      if (forcedStop) break;

      try {
        await page.goto(urlToScrape);
        isSuccessNav = true;
        break;
      } catch (error) {
        if (forcedStop) break;
        await refreshBrowser();
        await timeoutPromise(RETRY_DELAY);
      }
    }

    if (!isSuccessNav) {
      throw "Failed nav!";
    }
    console.log("NAVIGATED!");

    try {
      const isExists = await page.evaluate(evaluateExists);
      if (!isExists) {
        throw "Not exists";
      }

      const MAX_BUTTON_TRIES = 60;
      let buttonFound = false;
      for (let j = 0; j < MAX_BUTTON_TRIES; j++) {
        buttonFound = await page.evaluate(evaluateDownloadButton);
        if (buttonFound) break;
        await timeoutPromise(CHECK_BUTTON_DELAY);
      }
      if (!buttonFound) throw "No button";
    } catch (error) {
      console.log(ticker, "DOES NOT EXIST!", error);
      continue;
    }

    console.log("DATA EXISTS");

    // Click max
    const maxButtonSelector = 'button[data-value="y10"]';

    await page.waitForSelector(maxButtonSelector);
    await timeoutPromise(BUTTON_FOUND_TO_CLICK_DELAY);
    await page.click(maxButtonSelector);

    console.log("MAX BUTTON CLICKED");

    await timeoutPromise(BUTTON_TO_DOWNLOAD_DELAY);

    // Click download
    const downloadButtonSelector =
      "button.historical-data__controls-button--download.historical-download";
    await page.waitForSelector(downloadButtonSelector);
    await page.click(downloadButtonSelector);
    await timeoutPromise(DOWNLOAD_DELAY);

    const MAX_DOWNLOAD_LOOPS = 10;
    let newFile = "";
    let isFailed = false;
    for (let i = 0; i < MAX_DOWNLOAD_LOOPS; i++) {
      if (forcedStop) {
        break;
      }

      console.log("CHECKING DOWNLOAD", i);
      const newFolderFiles = readdirSync(OUT_FOLDER_PATH);

      newFolderFiles.forEach((fileName) => {
        if (!startFolderFiles.includes(fileName)) {
          newFile = fileName;
        }
      });

      if (newFile) {
        break;
      } else {
        if (i + 1 == MAX_DOWNLOAD_LOOPS) isFailed = true;
        await timeoutPromise(CHECK_DOWNLOAD_DELAY);
      }
    }

    // Rename file
    if (forcedStop) break;
    if (isFailed) {
      console.log("CANNOT DONWLOAD");
      continue;
    }

    const OLD_PATH = join(OUT_FOLDER_PATH, newFile);
    const NEW_PATH = join(OUT_FOLDER_PATH, ticker + ".csv");
    renameSync(OLD_PATH, NEW_PATH);

    console.log(
      "DOWNLOADED!",
      ticker,
      getPercentageString(i + 1, startIndex, endIndex)
    );

    await timeoutPromise(NEXT_PAGE_DELAY);
  }

  process.exit();
};

function evaluateExists() {
  const h2 = document.querySelector("h2.alert__heading");
  if (h2 && h2.innerText.includes("is currently not")) {
    return false;
  }

  if (!h2) {
    return true;
  }
  return false;
}

function evaluateDownloadButton() {
  const buttonEl = document.querySelector(
    "button.historical-data__controls-button--download.historical-download"
  );

  if (!buttonEl) {
    return false;
  }

  const cursor = window.getComputedStyle(buttonEl).cursor;
  console.log(cursor);
  if (cursor == "not-allowed") return false;
  return true;
}
main();
