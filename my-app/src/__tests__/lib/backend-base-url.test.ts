describe("getBackendBaseUrl", () => {
  const orig = process.env.NEXT_PUBLIC_API_URL;

  afterEach(() => {
    if (orig === undefined) {
      delete process.env.NEXT_PUBLIC_API_URL;
    } else {
      process.env.NEXT_PUBLIC_API_URL = orig;
    }
  });

  it("defaults to http://localhost:8000 when unset", () => {
    delete process.env.NEXT_PUBLIC_API_URL;
    jest.isolateModules(() => {
      const { getBackendBaseUrl } = require("@/lib/backend-base-url");
      expect(getBackendBaseUrl()).toBe("http://localhost:8000");
    });
  });

  it("coerces https localhost to http", () => {
    process.env.NEXT_PUBLIC_API_URL = "https://localhost:8000";
    jest.isolateModules(() => {
      const { getBackendBaseUrl } = require("@/lib/backend-base-url");
      expect(getBackendBaseUrl()).toBe("http://localhost:8000");
    });
  });

  it("preserves https for non-localhost hosts", () => {
    process.env.NEXT_PUBLIC_API_URL = "https://api.example.com";
    jest.isolateModules(() => {
      const { getBackendBaseUrl } = require("@/lib/backend-base-url");
      expect(getBackendBaseUrl()).toBe("https://api.example.com");
    });
  });
});
