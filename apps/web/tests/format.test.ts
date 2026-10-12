import { describe, expect, it } from "vitest";
import { NOT_AVAILABLE, interval, num } from "@/lib/format";

describe("format", () => {
  it("n'invente jamais de valeur", () => {
    expect(num(null)).toBe(NOT_AVAILABLE);
    expect(num(undefined)).toBe(NOT_AVAILABLE);
    expect(num(Number.NaN)).toBe(NOT_AVAILABLE);
    expect(interval(null, 0.1, 0.9)).toBe(NOT_AVAILABLE);
  });
  it("met en forme à la française", () => {
    expect(num(0.9123)).toBe("0,912");
    expect(interval(0.9, 0.85, 0.95)).toBe("0,900 [0,850 ; 0,950]");
  });
  it("sans bornes, n'affiche que l'estimation", () => {
    expect(interval(0.5, null, null)).toBe("0,500");
  });
  it("garde zéro comme une vraie valeur", () => {
    expect(num(0)).toBe("0,000");
  });
});
