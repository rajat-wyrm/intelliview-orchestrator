import { Shimmer } from "@/components/Shimmer";

export default function Loading() {
  return (
    <div className="space-y-4 p-6">
      <Shimmer className="h-10 w-1/3" />

      <Shimmer className="h-24 w-full" />
      <Shimmer className="h-24 w-full" />

      <Shimmer className="h-24 w-full" />
    </div>
  );
}