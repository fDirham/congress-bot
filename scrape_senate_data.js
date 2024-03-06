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
import { downloadFile } from "./custom_helpers_js/downloaders.js";

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

  // Run constants
  const NAV_TIMEOUT = 30 * 1000;
  const SIZE_SET_DELAY = 2 * 1000;
  const NEXT_PAGE_DELAY = 2 * 1000;
  const PAGE_SIZE = 100;
  const DOWNLOAD_DELAY = 500;

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

  // Get necessary cookies and states for page
  const SEARCH_PAGE_URL = "https://efdsearch.senate.gov/search/";
  await page.goto(SEARCH_PAGE_URL);

  // Click agree
  await page.click('input#agree_statement[value="1"]');

  // Wait for start
  const ptrSelector = 'input#reportTypes[value="11"]';
  await page.waitForSelector(ptrSelector);

  let infoList = [];
  if (!skipGetInfoList) {
    // Select ptr filing type
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
  } else {
    const infoListFileContents = readFileSync(INFO_LIST_FILE_PATH, {
      encoding: "utf-8",
    });
    infoList = JSON.parse(infoListFileContents);
  }

  if (!skipDownloadDocs) {
    function processNameForFile(inName) {
      inName = inName.toUpperCase();
      inName = inName.replace(/[^\w\s]/gi, "");
      inName = inName.replace(/ /g, "-");
      return inName;
    }

    const createFilenameFromObj = (obj) => {
      let { firstName, lastName, docUrl } = obj;

      firstName = processNameForFile(firstName);
      lastName = processNameForFile(lastName);

      const docId = docUrl
        .replace("/search/view/paper/", "")
        .replace("/search/view/ptr/", "")
        .replace("/", "");

      return [year, lastName, firstName, docId].join("_");
    };

    let startIndex = 0;
    if (downloadStartIndex) {
      startIndex = parseInt(downloadStartIndex) || 0;
    }

    for (let i = startIndex; i < infoList.length; i++) {
      const obj = infoList[i];
      const urlToDownload = "https://efdsearch.senate.gov" + obj.docUrl;
      const isFormattedPtr = urlToDownload.includes("/ptr/");
      console.log(
        "Downloading",
        i,
        getPercentageString(i + 1, startIndex, infoList.length)
      );
      console.log(urlToDownload);

      await page.goto(urlToDownload);
      if (isFormattedPtr) {
        await page.waitForSelector("tbody tr td");
        const ptrResults = await page.evaluate(evaluatePtrPage);
        // Save JSON
        const savePath = join(
          DOCUMENTS_FOLDER_PATH,
          createFilenameFromObj(obj) + ".json"
        );
        writeFileSync(savePath, JSON.stringify(ptrResults));
      } else {
        // Grab all image srcs
        await page.waitForSelector("img.filingImage");
        const imgUrls = await page.evaluate(evaluatePaperPage);

        // Save list
        const imageListFilepath = join(
          DOCUMENTS_FOLDER_PATH,
          createFilenameFromObj(obj) + "-z-image-list.json"
        );
        writeFileSync(imageListFilepath, JSON.stringify(imgUrls));

        // Download
        await Promise.all(
          imgUrls.map(async (url, i) => {
            try {
              const lastDotIdx = url.lastIndexOf(".");
              const extension = url.substring(lastDotIdx + 1);
              const saveFilepath = join(
                DOCUMENTS_FOLDER_PATH,
                createFilenameFromObj(obj) + "-" + i + "." + extension
              );
              await downloadFile(url, saveFilepath);
              return saveFilepath;
            } catch (error) {
              console.error(error);
              return error;
            }
          })
        );
      }

      await timeoutPromise(DOWNLOAD_DELAY);
    }
  }

  process.exit();
};

function evaluateResults() {
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
}

function evaluatePtrPage() {
  const resultList = [];
  document.querySelectorAll("tbody tr").forEach((trEl) => {
    const rowTdList = [];
    trEl.querySelectorAll("td").forEach((tdEl) => {
      rowTdList.push(tdEl.innerText);
    });
    const tickerUrlList = [];
    trEl.querySelectorAll("a").forEach((aTag) => {
      const href = aTag.getAttribute("href");
      tickerUrlList.push(href);
    });

    const toAdd = {
      transactionDate: rowTdList[1],
      owner: rowTdList[2],
      ticker: rowTdList[3],
      assetName: rowTdList[4],
      assetType: rowTdList[5],
      actionType: rowTdList[6],
      amount: rowTdList[7],
      comment: rowTdList[8],
      tickerUrlList: tickerUrlList,
    };

    resultList.push(toAdd);
  });
  return resultList;
}

function evaluatePaperPage() {
  const imgSrcList = [];
  document.querySelectorAll("img.filingImage").forEach((imgEl) => {
    imgSrcList.push(imgEl.getAttribute("src"));
  });
  return imgSrcList;
}
main();
