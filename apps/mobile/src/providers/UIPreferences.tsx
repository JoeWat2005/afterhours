import type { PropsWithChildren } from "react";
import { createContext, useContext, useEffect, useMemo, useState } from "react";
import * as SecureStore from "expo-secure-store";

type UiPreferences = {
  highContrast: boolean;
  setHighContrast: (value: boolean) => void;
};

const STORAGE_KEY = "ui-preferences-high-contrast";

const UiPreferencesContext = createContext<UiPreferences | null>(null);

export function UiPreferencesProvider({ children }: PropsWithChildren) {
  const [highContrast, setHighContrastState] = useState(false);

  useEffect(() => {
    SecureStore.getItemAsync(STORAGE_KEY).then((value) => {
      if (value === "true") {
        setHighContrastState(true);
      }
    });
  }, []);

  const setHighContrast = (value: boolean) => {
    setHighContrastState(value);
    SecureStore.setItemAsync(STORAGE_KEY, String(value)).catch(() => {});
  };

  const contextValue = useMemo(
    () => ({
      highContrast,
      setHighContrast,
    }),
    [highContrast]
  );

  return (
    <UiPreferencesContext.Provider value={contextValue}>
      {children}
    </UiPreferencesContext.Provider>
  );
}

export function useUiPreferences() {
  const context = useContext(UiPreferencesContext);

  if (!context) {
    throw new Error("useUiPreferences must be used within UiPreferencesProvider");
  }

  return context;
}