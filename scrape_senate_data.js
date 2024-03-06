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
import { getOutFolderSenate } from "./custom_helpers_js/getPaths.js";
import { readFileSync, writeFileSync } from "fs";

const main = async () => {
  // Process input arguments
  const argv = yargs(hideBin(process.argv)).argv;
  let { year, skipGetInfoList, skipDownloadDocs, downloadStartIndex } = argv;
  if (!year) {
    console.log("Invalid inputs");
    process.exit(1);
  }
  year = parseInt(year);

  // File paths
  const INFO_LIST_FILE_PATH = join(
    getOutFolderSenate(),
    year + "-info-list.json"
  );
  const DOCUMENTS_FOLDER_PATH = join(getOutFolderSenate(), "documents");
  const ERROR_DOWNLOAD_FILE_PATH = join(
    getOutFolderSenate(),
    year + "-download-errors.json"
  );

  // Run constants
  const NAV_TIMEOUT = 30 * 1000;
  const SIZE_SET_DELAY = 2 * 1000;
  const NEXT_PAGE_DELAY = 2 * 1000;
  const PAGE_SIZE = 100;

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
    await page.setDefaultNavigationTimeout(NAV_TIMEOUT);
    page.on("request", (request) => {
      if (request.resourceType() === "image") {
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
  });

  if (!skipGetInfoList) {
    const SEARCH_PAGE_URL = "https://efdsearch.senate.gov/search/";
    await page.goto(SEARCH_PAGE_URL);

    // Click agree
    await page.click('input#agree_statement[value="1"]');

    // Select PTR
    const ptrSelector = 'input#reportTypes[value="11"]';
    await page.waitForSelector(ptrSelector);
    await page.click(ptrSelector);

    // Input years
    const startDateStr = new Date(year, 0, 1).toLocaleString("en-US", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
    });
    const endDateStr = new Date(year, 11, 31).toLocaleString("en-US", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
    });
    await page.type("input#fromDate", startDateStr);
    await page.type("input#toDate", endDateStr);

    // Start search
    await page.click('button.btn.btn-primary[type="submit"]');

    // Wait for selector
    const anyResultSelector = "tbody tr td a";
    await page.waitForSelector(anyResultSelector);

    // Set size
    const filedReportsSelectSelector = 'select[name="filedReports_length"]';
    await page.select(filedReportsSelectSelector, PAGE_SIZE + "");
    await timeoutPromise(SIZE_SET_DELAY);

    // See how many pages to sift through
    const filedReportsInfo = await page.evaluate(() => {
      const infoDiv = document.querySelector("div#filedReports_info");
      return infoDiv.innerText;
    });
    const numEntries = parseInt(
      filedReportsInfo
        .split("of")[1]
        .replace("entries", "")
        .replace(/\,/g, "")
        .trim()
    );
    const numPages = Math.ceil(numEntries / PAGE_SIZE);

    // Sift through pages
    const infoList = [];
    for (let i = 0; i < numPages; i++) {
      console.log(
        "Processing page",
        i,
        getPercentageString(i + 1, 0, numPages)
      );
      const processedResults = await page.evaluate(evaluateResults);
      processedResults.forEach((obj) => {
        infoList.push(obj);
      });

      if (i !== numPages - 1) {
        await page.click("a#filedReports_next");
        await timeoutPromise(NEXT_PAGE_DELAY);
      }
    }

    writeFileSync(INFO_LIST_FILE_PATH, JSON.stringify(infoList));
  }

  process.exit();
};

const evaluateResults = () => {
  const rowElList = document.querySelectorAll("tbody tr");
  const resultList = [];
  rowElList.forEach((rowEl) => {
    const rowInfoList = [];
    rowEl.querySelectorAll("td").forEach((cellEl) => {
      rowInfoList.push(cellEl.innerText);
    });
    const docUrl = rowEl.querySelector("a").getAttribute("href");
    const toAdd = {
      firstName: rowInfoList[0],
      lastName: rowInfoList[1],
      office: rowInfoList[2],
      dateFiled: rowInfoList[4],
      docUrl,
    };
    resultList.push(toAdd);
  });
  return resultList;
};

main();
