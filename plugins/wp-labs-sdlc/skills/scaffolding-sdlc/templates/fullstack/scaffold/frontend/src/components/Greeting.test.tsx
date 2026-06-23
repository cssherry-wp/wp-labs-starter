import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Greeting } from "./Greeting";

describe("Greeting", () => {
  it("greets the given name", () => {
    render(<Greeting name="Ada" />);
    expect(screen.getByText("Hello, Ada!")).toBeInTheDocument();
  });

  it("falls back to world for blank names", () => {
    render(<Greeting name="   " />);
    expect(screen.getByText("Hello, world!")).toBeInTheDocument();
  });
});
