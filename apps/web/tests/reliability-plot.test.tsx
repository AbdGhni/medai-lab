import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ReliabilityPlot } from "@/components/ReliabilityPlot";

describe("ReliabilityPlot", () => {
  it("sans données, ne dessine aucun point", () => {
    const { container } = render(<ReliabilityPlot label="Fiabilité" points={[]} />);
    expect(screen.getByRole("img")).toHaveAttribute("aria-label", "Fiabilité : aucune donnée");
    expect(container.querySelectorAll("circle")).toHaveLength(0);
  });
  it("décrit chaque point et en dessine un par intervalle non vide", () => {
    const points = [
      { bin: 1, n: 10, mean_prob: 0.15, observed_freq: 0.1 },
      { bin: 8, n: 40, mean_prob: 0.85, observed_freq: 0.9 },
    ];
    const { container } = render(<ReliabilityPlot label="Fiabilité" points={points} />);
    expect(container.querySelectorAll("circle")).toHaveLength(2);
    expect(screen.getByRole("img").getAttribute("aria-label")).toContain("prédit 0,85 observé 0,90 (n=40)");
  });
});
