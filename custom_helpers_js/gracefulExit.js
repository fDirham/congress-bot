import { createInterface } from "readline";

export function registerGracefulExit(onExit, stopAfter = false) {
  if (process.platform === "win32") {
    let rl = createInterface({
      input: process.stdin,
      output: process.stdout,
    });

    rl.on("SIGINT", function () {
      process.emit("SIGINT");
    });
  }

  process.on("SIGINT", function () {
    onExit();
    if (stopAfter) {
      process.exit();
    }
  });
}
