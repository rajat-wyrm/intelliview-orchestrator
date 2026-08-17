const nextConfig = require("eslint-config-next");

module.exports = [
  {
    ...nextConfig[1],
    files: ["**/*.js", "**/*.jsx", "**/*.ts", "**/*.tsx"],
  },
  nextConfig[2],
];
