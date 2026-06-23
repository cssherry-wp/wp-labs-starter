import { describe, expect, it } from "vitest";
import { greet } from "./greeting.js";

describe("greet", () => {
  it("greets a name", () => {
    expect(greet("Ada")).toBe("Hello, Ada!");
  });

  it("trims surrounding whitespace", () => {
    expect(greet("  Ada  ")).toBe("Hello, Ada!");
  });

  it("rejects an empty name", () => {
    expect(() => greet("   ")).toThrow("name must not be empty");
  });
});
