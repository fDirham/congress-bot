import axios from "axios";
import yargs from "yargs/yargs";
import { hideBin } from "yargs/helpers";
import * as cheerio from "cheerio";
import { readFileSync, writeFileSync } from "fs";
import { join } from "path";
import { getOutFolderHouse } from "./custom_helpers_js/getPaths.js";
import { downloadFile } from "./custom_helpers_js/downloaders.js";
import {
  cleanTextNonAscii,
  getPercentageString,
  timeoutPromise,
} from "./custom_helpers_js/utilities.js";

const main = async () => {
  // Process input arguments
  const argv = yargs(hideBin(process.argv)).argv;
  let { year, skipGetInfoList, downloadStartIndex } = argv;

  if (!year) {
    console.log("Invalid inputs");
    process.exit(1);
  }

  const INFO_LIST_FILE_PATH = join(
    getOutFolderHouse(),
    year + "-info-list.json"
  );
  const DOCUMENTS_FOLDER_PATH = join(getOutFolderHouse(), "documents");
  const ERROR_DOWNLOAD_FILE_PATH = join(
    getOutFolderHouse(),
    year + "-download-errors.json"
  );
  const BASE_URL = "https://disclosures-clerk.house.gov/";
  const API_URL = BASE_URL + "FinancialDisclosure/ViewMemberSearchResult";

  let infoList = [];
  if (!skipGetInfoList) {
    const form = new FormData();
    form.append("FilingYear", parseInt(year));
    const getRes = await axios.post(API_URL, form);

    const $ = cheerio.load(getRes.data);

    $("tr").each(function () {
      const toAdd = {};

      // Get url
      const docUrl = $(this).find("a").attr("href");
      if (!docUrl) {
        return;
      }

      const values = [];
      $(this)
        .find("td")
        .each(function () {
          const val = $(this).text().replace(/\n/g, " ").trim();
          values.push(val);
        });

      toAdd.listedName = values[0];
      toAdd.office = values[1];
      toAdd.filingYear = values[2];
      toAdd.filingType = values[3];

      if (!toAdd.filingType.includes("PTR")) {
        return;
      }

      // Split last name first name
      let newName = toAdd.listedName;
      newName = newName.replace("Hon..", "");
      newName = newName.replace("HON.", "");
      const nameParts = newName.split(",");
      toAdd.lastName = nameParts[0].trim();
      toAdd.firstName = nameParts[1].trim();

      // Get doc id
      let docId = docUrl;
      const slashIdx = docId.lastIndexOf("/");
      const dotIdx = docId.lastIndexOf(".");
      docId = docId.substring(slashIdx + 1, dotIdx);
      toAdd.docId = docId;

      infoList.push(toAdd);
    });

    writeFileSync(INFO_LIST_FILE_PATH, JSON.stringify(infoList), {
      encoding: "utf-8",
    });
  } else {
    const infoListFileContents = readFileSync(INFO_LIST_FILE_PATH, {
      encoding: "utf-8",
    });
    infoList = JSON.parse(infoListFileContents);
  }

  // Download pdfs
  const DOWNLOAD_DELAY = 500;

  function getDocFileName(obj) {
    let { firstName, lastName, office, filingYear, docId } = obj;

    firstName = cleanTextNonAscii(firstName);
    lastName = cleanTextNonAscii(lastName);

    return [filingYear, office, lastName, firstName, docId].join("_") + ".pdf";
  }

  function getUrlFromObj(obj) {
    return BASE_URL + `public_disc/ptr-pdfs/${year}/${obj.docId}.pdf`;
  }

  let startIndex = 0;
  if (downloadStartIndex) {
    startIndex = parseInt(downloadStartIndex) || 0;
  }

  const failedList = [];
  for (let i = startIndex; i < infoList.length; i++) {
    const obj = infoList[i];
    const toDownloadUrl = getUrlFromObj(obj);
    const savePath = join(DOCUMENTS_FOLDER_PATH, getDocFileName(obj));

    console.log("Downloading", i, toDownloadUrl);

    try {
      await downloadFile(toDownloadUrl, savePath);
      console.log(
        "Finished",
        i,
        getPercentageString(i + 1, startIndex, infoList.length)
      );
      console.log(savePath);
      if (DOWNLOAD_DELAY) {
        await timeoutPromise(DOWNLOAD_DELAY);
      }
    } catch (error) {
      console.error(error);
      console.error("ERROR", i, toDownloadUrl);
      failedList.push({
        runIndex: i,
        toDownloadUrl,
      });
    }
  }

  if (failedList.length) {
    writeFileSync(ERROR_DOWNLOAD_FILE_PATH, JSON.stringify(failedList));
  }
};

main();
