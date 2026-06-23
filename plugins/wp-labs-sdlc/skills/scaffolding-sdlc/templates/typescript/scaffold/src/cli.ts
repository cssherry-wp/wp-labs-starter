#!/usr/bin/env node
import { greet } from "./greeting.js";

function main(argv: string[]): void {
  const name = argv[2] ?? "world";
  console.log(greet(name));
}

main(process.argv);
