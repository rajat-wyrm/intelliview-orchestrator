import { describe, it, expect } from "vitest";

function isPermissionGranted(permission) {
  return permission === "granted";
}

describe("Notification Permission", () => {
  it("returns true when granted", () => {
    expect(isPermissionGranted("granted")).toBe(true);
  });

  it("returns false when denied", () => {
    expect(isPermissionGranted("denied")).toBe(false);
  });

  it("returns false when default", () => {
    expect(isPermissionGranted("default")).toBe(false);
  });
});