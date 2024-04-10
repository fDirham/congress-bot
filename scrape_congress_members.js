import puppeteer from "puppeteer-extra";
import StealthPlugin from "puppeteer-extra-plugin-stealth";
import { timeoutPromise } from "./custom_helpers_js/utilities.js";
import { join } from "path";
import UserAgent from "user-agents";
import { getOutFolder } from "./custom_helpers_js/getPaths.js";
import { writeFileSync } from "fs";
import yargs from "yargs/yargs";
import { hideBin } from "yargs/helpers";

const main = async () => {
  const argv = yargs(hideBin(process.argv))
    .scriptName("scrape individual politicians")
    .option("endIndex", {
      alias: "e",
      type: "number",
      default: 10,
    }).argv;
  let { endIndex } = argv;

  // File paths
  const OUT_FILE_PATH = join(getOutFolder(), "congress_members", "list.json");

  // Run constants
  const NEXT_PAGE_DELAY = 2 * 1000;

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

  await page.goto(
    "https://www.congress.gov/members?q=%7B%22congress%22%3A%5B118%2C%22117%22%2C%22116%22%2C%22115%22%2C%22114%22%2C%22113%22%5D%7D"
  );

  const toSave = [];
  for (let i = 0; i < endIndex; i++) {
    console.log("starting page", i);
    const pageResults = await page.evaluate(evaluatePage);
    pageResults.forEach((obj) => {
      toSave.push(obj);
    });
    console.log("done", i);
    if (i != 9) {
      await page.click("a.next");
      await timeoutPromise(NEXT_PAGE_DELAY);
    }
  }

  writeFileSync(OUT_FILE_PATH, JSON.stringify(toSave, null, 3));
  process.exit();
};

function evaluatePage() {
  const toReturn = [];
  const cardList = document.querySelectorAll("div#main>ol>li.expanded");
  for (let i = 0; i < cardList.length; i++) {
    const cardEl = cardList[i];
    let heading = "";
    const headingEl = cardEl.querySelector("span.visualIndicator");
    if (headingEl) {
      heading = headingEl.innerText;
    }

    let name = "";
    let chamber = "";
    const nameEl = cardEl.querySelector("span.result-heading a");
    if (nameEl) {
      const text = nameEl.innerText.split(" - ");
      name = text[0];
      chamber = text[1];
    }

    let state = "";
    let district = "";
    let party = "";
    let served = "";

    const profileEl = cardEl.querySelector("div.member-profile");
    if (profileEl) {
      const profileLines = profileEl.innerText.split("\n");
      profileLines.forEach((line) => {
        const components = line.split(":");
        let val = components[1];
        if (val) {
          val = val.trim();

          switch (components[0]) {
            case "State":
              state = val;
              break;
            case "District":
              district = val;
              break;
            case "Party":
              party = val;
              break;
            default:
              break;
          }
        }
      });
      const servedEl = profileEl.querySelector("ul.member-served");
      if (servedEl) {
        served = JSON.stringify(servedEl.innerText.split("\n"));
      }
    }

    const toAdd = {
      heading,
      name,
      chamber,
      state,
      district,
      party,
      served,
    };

    toReturn.push(toAdd);
  }

  return toReturn;
}

main();
