import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { TextField } from "./TextField";

describe("TextField", () => {
  it("labels the input", () => {
    render(<TextField label="Search by name or ID" />);

    expect(screen.getByLabelText("Search by name or ID")).toBeInTheDocument();
  });

  it("describes the input with its hint", () => {
    render(<TextField label="Title" hint="Shown in citations." />);

    expect(screen.getByLabelText("Title")).toHaveAccessibleDescription("Shown in citations.");
  });

  it("marks the input invalid and shows the error instead of the hint", () => {
    render(<TextField label="Question" hint="Be specific." error="Too short." />);

    const input = screen.getByLabelText("Question");
    expect(input).toHaveAttribute("aria-invalid", "true");
    expect(input).toHaveAccessibleDescription("Too short.");
    expect(screen.queryByText("Be specific.")).not.toBeInTheDocument();
  });
});
