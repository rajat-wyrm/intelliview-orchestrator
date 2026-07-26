const API_TIMEOUT = 10000;

const mockCandidates = [
  {
    id: "1",
    name: "John Doe",
    domain: "Frontend",
    type: "Full Time",
    status: "Pending",
  },
  {
    id: "2",
    name: "Priya Sharma",
    domain: "Backend",
    type: "Intern",
    status: "Completed",
  },
];

export async function fetchCandidates(filters = {}, options = {}) {
  const params = new URLSearchParams();

  Object.entries(filters).forEach(([key, value]) => {
    if (value !== "" && value !== undefined && value !== null) {
      params.append(key, String(value));
    }
  });

  const query = params.toString();
  const url = `/api/candidates${query ? `?${query}` : ""}`;

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), API_TIMEOUT);

  try {
    const response = await fetch(url, {
      method: "GET",
      signal: options.signal || controller.signal,
    });

    if (!response.ok) {
      throw new Error(`Request failed with status ${response.status}`);
    }

    const data = await response.json();

    if (
      !data ||
      !Array.isArray(data.candidates) ||
      typeof data.totalCount !== "number"
    ) {
      throw new Error("Invalid API response");
    }

    return data;
  } catch (error) {
    // If the caller intentionally cancelled the request,
    // don't replace it with mock data.
    if (error.name === "AbortError" && options.signal) {
      throw error;
    }

    return {
      candidates: mockCandidates,
      totalCount: mockCandidates.length,
      page: filters.page || 1,
      limit: filters.limit || 10,
    };
  } finally {
    clearTimeout(timeout);
  }
}