import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Status, readableStatus } from "./Status";

describe("Status", () => {
  it("translates internal running stages into procurement language", () => {
    render(<Status status="running" stage="verification" />);
    expect(screen.getByText("Verifying evidence")).toBeInTheDocument();
    expect(readableStatus("completed")).toBe("Ready for review");
  });
});

