import type { PropsWithChildren } from "react";
import { createContext, useContext, useEffect, useMemo, useState } from "react";
import * as SecureStore from "expo-secure-store";

export type RouteAccessibilityChoices = {
  avoid_stairs: boolean;
  step_free_access: boolean;
  lifts_available: boolean;
  ramps_available: boolean;
  escalators_available: boolean;
};

export type RouteWaitingAreaChoices = {
  safe_waiting_areas: boolean;
  well_lit_waiting_areas: boolean;
  wifi_nearby: boolean;
  staffed_venues_nearby: boolean;
  open_venues_nearby: boolean;
  safe_areas_nearby: boolean;
};

export type RouteOptionChoices = {
  accessibility: RouteAccessibilityChoices;
  waiting_areas: RouteWaitingAreaChoices;
};

type UiPreferences = {
  highContrast: boolean;
  setHighContrast: (value: boolean) => void;
  routeOptions: RouteOptionChoices;
  setAccessibilityOption: (
    option: keyof RouteAccessibilityChoices,
    value: boolean,
  ) => void;
  setWaitingAreaOption: (
    option: keyof RouteWaitingAreaChoices,
    value: boolean,
  ) => void;
  leaveNowAlerts: boolean;
  setLeaveNowAlerts: (value: boolean) => void;
  lowDataMode: boolean;
  setLowDataMode: (value: boolean) => void;
};

const STORAGE_KEYS = {
  highContrast: "ui-preferences-high-contrast",
  routeOptions: "ui-preferences-route-options",
  leaveNowAlerts: "ui-preferences-leave-now-alerts",
  lowDataMode: "ui-preferences-low-data-mode",
} as const;

const DEFAULT_ROUTE_OPTIONS: RouteOptionChoices = {
  accessibility: {
    avoid_stairs: false,
    step_free_access: false,
    lifts_available: false,
    ramps_available: false,
    escalators_available: false,
  },
  waiting_areas: {
    safe_waiting_areas: false,
    well_lit_waiting_areas: false,
    wifi_nearby: false,
    staffed_venues_nearby: false,
    open_venues_nearby: false,
    safe_areas_nearby: false,
  },
};

function sanitizeRouteOptions(raw: unknown): RouteOptionChoices {
  const defaultValue = DEFAULT_ROUTE_OPTIONS;
  if (!raw || typeof raw !== "object") {
    return defaultValue;
  }
  const candidate = raw as Partial<RouteOptionChoices>;
  const accessibility = (candidate.accessibility ?? {}) as Partial<RouteAccessibilityChoices>;
  const waitingAreas = (candidate.waiting_areas ?? {}) as Partial<RouteWaitingAreaChoices>;

  return {
    accessibility: {
      avoid_stairs: Boolean(accessibility.avoid_stairs),
      step_free_access: Boolean(accessibility.step_free_access),
      lifts_available: Boolean(accessibility.lifts_available),
      ramps_available: Boolean(accessibility.ramps_available),
      escalators_available: Boolean(accessibility.escalators_available),
    },
    waiting_areas: {
      safe_waiting_areas: Boolean(waitingAreas.safe_waiting_areas),
      well_lit_waiting_areas: Boolean(waitingAreas.well_lit_waiting_areas),
      wifi_nearby: Boolean(waitingAreas.wifi_nearby),
      staffed_venues_nearby: Boolean(waitingAreas.staffed_venues_nearby),
      open_venues_nearby: Boolean(waitingAreas.open_venues_nearby),
      safe_areas_nearby: Boolean(waitingAreas.safe_areas_nearby),
    },
  };
}

const UiPreferencesContext = createContext<UiPreferences | null>(null);

export function UiPreferencesProvider({ children }: PropsWithChildren) {
  const [highContrast, setHighContrastState] = useState(false);
  const [routeOptions, setRouteOptionsState] = useState(DEFAULT_ROUTE_OPTIONS);
  const [leaveNowAlerts, setLeaveNowAlertsState] = useState(true);
  const [lowDataMode, setLowDataModeState] = useState(false);

  useEffect(() => {
    let cancelled = false;

    Promise.all([
      SecureStore.getItemAsync(STORAGE_KEYS.highContrast),
      SecureStore.getItemAsync(STORAGE_KEYS.routeOptions),
      SecureStore.getItemAsync(STORAGE_KEYS.leaveNowAlerts),
      SecureStore.getItemAsync(STORAGE_KEYS.lowDataMode),
    ]).then((values) => {
      if (cancelled) return;

      const [highContrastValue, routeOptionsValue, leaveNowAlertsValue, lowDataModeValue] =
        values;

      if (highContrastValue === "true") {
        setHighContrastState(true);
      }
      if (routeOptionsValue) {
        try {
          const parsed = JSON.parse(routeOptionsValue);
          setRouteOptionsState(sanitizeRouteOptions(parsed));
        } catch {
          setRouteOptionsState(DEFAULT_ROUTE_OPTIONS);
        }
      }
      if (leaveNowAlertsValue === "false") {
        setLeaveNowAlertsState(false);
      }
      if (lowDataModeValue === "true") {
        setLowDataModeState(true);
      }
    });

    return () => {
      cancelled = true;
    };
  }, []);

  const persistRouteOptions = (next: RouteOptionChoices) => {
    SecureStore.setItemAsync(STORAGE_KEYS.routeOptions, JSON.stringify(next)).catch(() => {});
  };

  const setHighContrast = (value: boolean) => {
    setHighContrastState(value);
    SecureStore.setItemAsync(STORAGE_KEYS.highContrast, String(value)).catch(() => {});
  };

  const setAccessibilityOption = (
    option: keyof RouteAccessibilityChoices,
    value: boolean,
  ) => {
    setRouteOptionsState((previous) => {
      const next = {
        ...previous,
        accessibility: {
          ...previous.accessibility,
          [option]: value,
        },
      };
      persistRouteOptions(next);
      return next;
    });
  };

  const setWaitingAreaOption = (
    option: keyof RouteWaitingAreaChoices,
    value: boolean,
  ) => {
    setRouteOptionsState((previous) => {
      const next = {
        ...previous,
        waiting_areas: {
          ...previous.waiting_areas,
          [option]: value,
        },
      };
      persistRouteOptions(next);
      return next;
    });
  };

  const setLeaveNowAlerts = (value: boolean) => {
    setLeaveNowAlertsState(value);
    SecureStore.setItemAsync(STORAGE_KEYS.leaveNowAlerts, String(value)).catch(() => {});
  };

  const setLowDataMode = (value: boolean) => {
    setLowDataModeState(value);
    SecureStore.setItemAsync(STORAGE_KEYS.lowDataMode, String(value)).catch(() => {});
  };

  const contextValue = useMemo(
    () => ({
      highContrast,
      setHighContrast,
      routeOptions,
      setAccessibilityOption,
      setWaitingAreaOption,
      leaveNowAlerts,
      setLeaveNowAlerts,
      lowDataMode,
      setLowDataMode,
    }),
    [highContrast, leaveNowAlerts, lowDataMode, routeOptions],
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
