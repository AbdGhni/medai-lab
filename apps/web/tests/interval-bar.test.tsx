import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { IntervalBar } from "@/components/IntervalBar";

describe("IntervalBar", () => {
  it("sans estimation, ne dessine aucune forme et dit « non disponible »", () => {
    const { container } = render(<IntervalBar label="AUC ROC" mean={null} low={null} high={null} />);
    expect(screen.getByRole("img")).toHaveAttribute("aria-label", "AUC ROC : non disponible");
    expect(container.querySelectorAll("circle")).toHaveLength(0);
  });
  it("avec estimation, dessine le point et décrit l'intervalle", () => {
    const { container } = render(<IntervalBar label="AUC ROC" mean={0.9} low={0.85} high={0.95} />);
    expect(screen.getByRole("img")).toHaveAttribute("aria-label", "AUC ROC : 0,900 [0,850 ; 0,950]");
    expect(container.querySelectorAll("circle")).toHaveLength(1);
  });
});
