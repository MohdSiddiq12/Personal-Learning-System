import { afterEach, describe, expect, it, vi } from "vitest";
import { apiRequest } from "./api";

describe("apiRequest connection failures", () => {
  afterEach(() => vi.restoreAllMocks());

  it("explains when the API cannot be reached", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));

    await expect(apiRequest("/api/books", "token")).rejects.toThrow(
      "Could not reach the LearnBook API.",
    );
  });
});
