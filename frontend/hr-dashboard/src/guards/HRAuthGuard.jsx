"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { jwtDecode } from "jwt-decode";

// TODO: Wrap HR routes with this guard once
// frontend/hr-dashboard/src/pages/ routes are available.
// Example usage:
// <HRAuthGuard>
//   <HRDashboard />
// </HRAuthGuard>

export default function HRAuthGuard({ children }) {
    const router = useRouter();
    const [isAuthorized, setIsAuthorized] = useState(false);

    useEffect(() => {
        const token = localStorage.getItem("api_token");

        if (!token) {
            router.push("/login");
            return;
        }

        try {
            const decodedToken = jwtDecode(token);
            const currentTime = Date.now() / 1000;

            if (currentTime > decodedToken.exp) {
                router.push("/session-expired");
                return;
            }

            if (decodedToken.role !== "hr") {
                router.push("/403");
                return;
            }

            // Authentication successful
            setIsAuthorized(true);

        } catch {
            localStorage.removeItem("api_token");
            router.push("/login");
        }

    }, [router]);

    if (!isAuthorized) {
        return null;
    }

    return children;
}

