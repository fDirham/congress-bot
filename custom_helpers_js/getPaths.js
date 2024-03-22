import "dotenv/config";
import { join } from "path";

export function getOutFolderHouse() {
  return join(getOutFolder(), "house");
}

export function getOutFolderSenate() {
  return join(getOutFolder(), "senate");
}

export function getOutFolderAnalysis() {
  return join(getOutFolder(), "analysis");
}

export function getOutFolderCapitolTrades() {
  return join(getOutFolder(), "capitol_trades");
}

export function getOutFolder() {
  return process.env.OUT_FOLDER;
}
