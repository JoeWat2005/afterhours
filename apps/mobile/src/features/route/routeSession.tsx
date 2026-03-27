import type { PropsWithChildren } from "react";
import { createContext, useCallback, useContext, useMemo, useState } from "react";

import type { Coordinates, RankedRoute } from "../../lib/api";

export type WalkStatus = "active" | "paused" | "completed" | "cancelled";

export type ActiveRouteSession = {
  journeyId: string | null;
  origin: Coordinates;
  destination: Coordinates;
  selectedRouteId: string;
  rankedRoutes: RankedRoute[];
  activeRoute: RankedRoute;
  status: WalkStatus;
  progressRatio: number;
  remainingDistanceMetres: number;
  remainingDurationSeconds: number;
  distanceFromRouteMetres: number;
  currentStepIndex: number;
  offRouteSamples: number;
  rerouting: boolean;
  lastLocation: Coordinates | null;
};

export type MapFocusTarget = {
  latitude: number;
  longitude: number;
  label?: string | null;
};

type RouteSessionContextValue = {
  session: ActiveRouteSession | null;
  mapFocusTarget: MapFocusTarget | null;
  startSession: (params: {
    journeyId: string | null;
    origin: Coordinates;
    destination: Coordinates;
    selectedRouteId: string;
    rankedRoutes: RankedRoute[];
  }) => void;
  replaceActiveRoute: (params: {
    selectedRouteId: string;
    rankedRoutes: RankedRoute[];
  }) => void;
  setWalkStatus: (status: WalkStatus) => void;
  clearSession: () => void;
  updateProgress: (params: {
    progressRatio: number;
    remainingDistanceMetres: number;
    remainingDurationSeconds: number;
    distanceFromRouteMetres: number;
    currentStepIndex: number;
    lastLocation: Coordinates;
  }) => void;
  incrementOffRouteSamples: () => void;
  resetOffRouteSamples: () => void;
  setRerouting: (value: boolean) => void;
  setMapFocusTarget: (target: MapFocusTarget | null) => void;
};

const RouteSessionContext = createContext<RouteSessionContextValue | null>(null);

function findSelectedRoute(selectedRouteId: string, rankedRoutes: RankedRoute[]) {
  return (
    rankedRoutes.find((route) => route.candidate_id === selectedRouteId) ??
    rankedRoutes[0] ??
    null
  );
}

export function RouteSessionProvider({ children }: PropsWithChildren) {
  const [session, setSession] = useState<ActiveRouteSession | null>(null);
  const [mapFocusTarget, setMapFocusTarget] = useState<MapFocusTarget | null>(null);

  // all actions use functional setSession so they never depend on the
  // current session value, keeping their references stable across renders
  const startSession = useCallback(
    ({ journeyId, origin, destination, selectedRouteId, rankedRoutes }: {
      journeyId: string | null;
      origin: Coordinates;
      destination: Coordinates;
      selectedRouteId: string;
      rankedRoutes: RankedRoute[];
    }) => {
      const activeRoute = findSelectedRoute(selectedRouteId, rankedRoutes);
      if (!activeRoute) return;
      setSession({
        journeyId,
        origin,
        destination,
        selectedRouteId,
        rankedRoutes,
        activeRoute,
        status: "active",
        progressRatio: 0,
        remainingDistanceMetres: activeRoute.distance_metres,
        remainingDurationSeconds: activeRoute.duration_seconds,
        distanceFromRouteMetres: 0,
        currentStepIndex: 0,
        offRouteSamples: 0,
        rerouting: false,
        lastLocation: null,
      });
    },
    [],
  );

  const replaceActiveRoute = useCallback(
    ({ selectedRouteId, rankedRoutes }: { selectedRouteId: string; rankedRoutes: RankedRoute[] }) => {
      setSession((prev) => {
        if (!prev) return prev;
        const activeRoute = findSelectedRoute(selectedRouteId, rankedRoutes);
        if (!activeRoute) return prev;
        return {
          ...prev,
          selectedRouteId,
          rankedRoutes,
          activeRoute,
          progressRatio: 0,
          remainingDistanceMetres: activeRoute.distance_metres,
          remainingDurationSeconds: activeRoute.duration_seconds,
          distanceFromRouteMetres: 0,
          currentStepIndex: 0,
          offRouteSamples: 0,
          rerouting: false,
        };
      });
    },
    [],
  );

  const setWalkStatus = useCallback((status: WalkStatus) => {
    setSession((prev) => (prev ? { ...prev, status } : prev));
  }, []);

  const clearSession = useCallback(() => setSession(null), []);

  const updateProgress = useCallback(
    (params: {
      progressRatio: number;
      remainingDistanceMetres: number;
      remainingDurationSeconds: number;
      distanceFromRouteMetres: number;
      currentStepIndex: number;
      lastLocation: Coordinates;
    }) => {
      setSession((prev) => (prev ? { ...prev, ...params } : prev));
    },
    [],
  );

  const incrementOffRouteSamples = useCallback(() => {
    setSession((prev) => (prev ? { ...prev, offRouteSamples: prev.offRouteSamples + 1 } : prev));
  }, []);

  const resetOffRouteSamples = useCallback(() => {
    setSession((prev) => {
      if (!prev || prev.offRouteSamples === 0) return prev;
      return { ...prev, offRouteSamples: 0 };
    });
  }, []);

  const setRerouting = useCallback((rerouting: boolean) => {
    setSession((prev) => (prev ? { ...prev, rerouting } : prev));
  }, []);

  const value = useMemo<RouteSessionContextValue>(
    () => ({
      session,
      mapFocusTarget,
      startSession,
      replaceActiveRoute,
      setWalkStatus,
      clearSession,
      updateProgress,
      incrementOffRouteSamples,
      resetOffRouteSamples,
      setRerouting,
      setMapFocusTarget,
    }),
    [mapFocusTarget, session],
  );

  return (
    <RouteSessionContext.Provider value={value}>
      {children}
    </RouteSessionContext.Provider>
  );
}

export function useRouteSession() {
  const context = useContext(RouteSessionContext);
  if (!context) {
    throw new Error("useRouteSession must be used within RouteSessionProvider");
  }
  return context;
}
