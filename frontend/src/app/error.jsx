"use client";

import { useEffect } from "react";

export default function GlobalError({ error, reset }) {
  useEffect(() => {
    console.error("Application Error:", error);
  }, [error]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-100 p-6">
      <div className="w-full max-w-md rounded-lg bg-white p-8 shadow-lg text-center">
        <h1 className="text-2xl font-bold text-red-600">
          Something went wrong
        </h1>

        <p className="mt-4 text-gray-600">
          An unexpected error occurred. Please try again.
        </p>

        {error?.digest && (
          <p className="mt-2 text-xs text-gray-400">
            Error ID: {error.digest}
          </p>
        )}

        <button
          onClick={() => reset()}
          className="mt-6 rounded-md bg-blue-600 px-4 py-2 text-white hover:bg-blue-700"
        >
          Try Again
        </button>
      </div>
    </div>
  );
}