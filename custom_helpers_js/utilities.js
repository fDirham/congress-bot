export const timeoutPromise = (waitInMs) => {
  return new Promise((resolve) => setTimeout(resolve, waitInMs));
};

export const getPercentageString = (currIndex, startIndex, lastIndex) => {
  const normalizedIndex = currIndex - startIndex;
  const normalizedLastIndex = lastIndex - startIndex;
  const doneFraction = normalizedIndex / normalizedLastIndex;
  const donePercentage = doneFraction * 100;
  const donePercentageString = donePercentage.toFixed(2) + "%";
  return donePercentageString;
};

export const cleanTextNonAscii = (inText) => {
  return inText.replace(/[^a-z0-9]/gim, " ").replace(/\s+/g, "");
};

export const getDateAsFileName = (inDate) => {
  if (!inDate) inDate = new Date();
  let isoString = inDate.toISOString();
  isoString = isoString.replace(/[\:.]/g, "_");
  return isoString;
};
