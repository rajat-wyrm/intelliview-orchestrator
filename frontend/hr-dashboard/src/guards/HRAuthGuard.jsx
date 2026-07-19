"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { jwtDecode } from "jwt-decode";

export default function HRAuthGuard({ children }) {
    const router = useRouter();

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

        }
        catch{
            localStorage.removeItem("api_token");
            router.push("/login");
            return;
        }

    }, [router]);

    return children;
}