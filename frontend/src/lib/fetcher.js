import { api } from "./api";

const swrFetcher = async (path) => {
  // Temporary delay for testing skeleton loaders
  await new Promise((resolve) => setTimeout(resolve, 3000));

  return api.get(path);
};

export {
  swrFetcher
};
