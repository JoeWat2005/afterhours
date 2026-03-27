import { useAuth } from "@clerk/expo";
import { useEffect, useState } from "react";

type ConvexAuthState = {
  hasConvexToken: boolean;
  checked: boolean;
};

export function useConvexTokenAvailability(): ConvexAuthState {
  const { isLoaded, isSignedIn, getToken } = useAuth();
  const [hasConvexToken, setHasConvexToken] = useState(false);
  const [checked, setChecked] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function checkToken() {
      if (!isLoaded || !isSignedIn) {
        if (!cancelled) {
          setHasConvexToken(false);
          setChecked(isLoaded);
        }
        return;
      }

      try {
        const token = await getToken({ template: "convex" });
        if (!cancelled) {
          setHasConvexToken(Boolean(token));
        }
      } catch {
        if (!cancelled) {
          setHasConvexToken(false);
        }
      } finally {
        if (!cancelled) {
          setChecked(true);
        }
      }
    }

    void checkToken();
    return () => {
      cancelled = true;
    };
  }, [isLoaded, isSignedIn]);

  return { hasConvexToken, checked };
}
