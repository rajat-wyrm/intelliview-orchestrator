/**
 * @module ui
 *
 * Shared UI component library for the IntelliView Orchestrator dashboard.
 * Import from this barrel instead of individual files:
 *
 *   import { Button, Input, Table, Th, Td, Shimmer, Spinner } from "@/components/ui";
 */

// Button
export { Button } from "./Button";
export { default as ButtonDefault } from "./Button";

// Input
export { Input, SearchInput } from "./Input";

// Table
export {
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
} from "./Table";

// Loader
export { Shimmer, Spinner, PageLoader } from "./Loader";
