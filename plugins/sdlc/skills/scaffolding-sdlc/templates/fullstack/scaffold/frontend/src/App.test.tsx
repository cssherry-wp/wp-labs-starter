import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { AppRoutes } from "./App";

describe("AppRoutes", () => {
  it("renders the Home page at /", () => {
    render(
      <MemoryRouter initialEntries={["/"]}>
        <AppRoutes />
      </MemoryRouter>,
    );
    expect(
      screen.getByRole("heading", { name: /welcome/i }),
    ).toBeInTheDocument();
  });

  it("renders the Widgets page at /widgets", () => {
    render(
      <MemoryRouter initialEntries={["/widgets"]}>
        <AppRoutes />
      </MemoryRouter>,
    );
    expect(
      screen.getByRole("heading", { name: /widgets/i }),
    ).toBeInTheDocument();
  });
});
