import puppeteer from "puppeteer-extra";
import StealthPlugin from "puppeteer-extra-plugin-stealth";
import { timeoutPromise } from "./custom_helpers_js/utilities.js";
import { registerGracefulExit } from "./custom_helpers_js/gracefulExit.js";
import { join } from "path";
import UserAgent from "user-agents";
import { getOutFolderCapitolTrades } from "./custom_helpers_js/getPaths.js";
import { readFileSync, writeFileSync } from "fs";
import yargs from "yargs/yargs";
import { hideBin } from "yargs/helpers";

const main = async () => {
  // Process input arguments
  const argv = yargs(hideBin(process.argv))
    .scriptName("scrape individual politicians")
    .option("startIndex", {
      alias: "s",
      type: "number",
      default: 0,
    })
    .option("endIndex", {
      alias: "e",
      type: "number",
      default: 0,
    }).argv;

  let { startIndex, endIndex } = argv;

  // File paths
  const POLITICIAN_LIST_FILE_PATH = join(
    getOutFolderCapitolTrades(),
    "politician_list.json"
  );

  const politicianListStr = readFileSync(POLITICIAN_LIST_FILE_PATH);
  const politicianList = JSON.parse(politicianListStr);

  const OUT_FOLDER_PATH = join(getOutFolderCapitolTrades(), "politician_data");

  // Run constants
  const NEXT_PAGE_DELAY = 2 * 1000;
  const PAGE_LOAD_DELAY = 5 * 1000;

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

  if (!endIndex) {
    endIndex = politicianList.length;
  }

  for (let i = startIndex; i < endIndex; i++) {
    const obj = politicianList[i];
    console.log("Starting", obj.fullName, obj.politicianPageLink);

    await page.goto(obj.politicianPageLink);

    const pageResults = await page.evaluate(evaluatePage);

    const dataToSave = {
      fullName: obj.fullName,
      pageLink: obj.politicianPageLink,
      id: obj.id,
      ...pageResults,
    };

    const OUT_FILE_PATH = join(OUT_FOLDER_PATH, obj.politicianId + ".json");
    writeFileSync(OUT_FILE_PATH, JSON.stringify(dataToSave, null, 4), {
      encoding: "utf-8",
    });

    await timeoutPromise(NEXT_PAGE_DELAY);
  }

  process.exit();
};

function evaluatePage() {
  const cardEl = document.querySelector("article.politician-detail-card");

  const officeInfo = {};
  const partyEl = cardEl.querySelector("h2 span.party");
  if (partyEl) {
    officeInfo.party = partyEl.innerText;
  }
  const chamberEl = cardEl.querySelector("h2 span.chamber");
  if (chamberEl) {
    officeInfo.chamber = chamberEl.innerText;
  }
  const stateEl = cardEl.querySelector("h2 span.us-state-full");
  if (stateEl) {
    officeInfo.state = stateEl.innerText;
  }

  const factElList = cardEl.querySelectorAll("section div div.q-cell");
  const factDict = {};
  factElList.forEach((fact) => {
    let label = fact.firstElementChild.innerText.toLowerCase();
    label = label
      .split(" ")
      .map((tmp, i) => {
        if (i) {
          tmp = tmp.charAt(0).toUpperCase() + tmp.slice(1);
        }
        return tmp;
      })
      .join("");

    if (label != "committees") {
      const value = fact.lastElementChild.innerText;
      factDict[label] = value;
    }
  });

  const committeeElList = cardEl.querySelectorAll("ol.ol-committees li");
  const committeeList = [];
  committeeElList.forEach((com) => {
    committeeList.push(com.innerText);
  });

  const socialElList = cardEl.querySelectorAll("footer a");
  const socialList = [];
  socialElList.forEach((aTag) => {
    socialList.push(aTag.href);
  });

  const toReturn = {
    officeInfo,
    factDict,
    committeeList,
    socialList,
  };

  return toReturn;
}

main();
