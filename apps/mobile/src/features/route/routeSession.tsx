import type { PropsWithChildren } from "react";
import { createContext, useContext, useMemo, useState } from "react";

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

  const value = useMemo<RouteSessionContextValue>(
    () => ({
      session,
      mapFocusTarget,
      startSession: ({ journeyId, origin, destination, selectedRouteId, rankedRoutes }) => {
        const activeRoute = findSelectedRoute(selectedRouteId, rankedRoutes);
        if (!activeRoute) {
          return;
        }

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
      replaceActiveRoute: ({ selectedRouteId, rankedRoutes }) => {
        setSession((previous) => {
          if (!previous) return previous;
          const activeRoute = findSelectedRoute(selectedRouteId, rankedRoutes);
          if (!activeRoute) return previous;
          return {
            ...previous,
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
      setWalkStatus: (status) => {
        setSession((previous) => {
          if (!previous) return previous;
          return {
            ...previous,
            status,
          };
        });
      },
      clearSession: () => {
        setSession(null);
      },
      updateProgress: ({
        progressRatio,
        remainingDistanceMetres,
        remainingDurationSeconds,
        distanceFromRouteMetres,
        currentStepIndex,
        lastLocation,
      }) => {
        setSession((previous) => {
          if (!previous) return previous;
          return {
            ...previous,
            progressRatio,
            remainingDistanceMetres,
            remainingDurationSeconds,
            distanceFromRouteMetres,
            currentStepIndex,
            lastLocation,
          };
        });
      },
      incrementOffRouteSamples: () => {
        setSession((previous) => {
          if (!previous) return previous;
          return {
            ...previous,
            offRouteSamples: previous.offRouteSamples + 1,
          };
        });
      },
      resetOffRouteSamples: () => {
        setSession((previous) => {
          if (!previous) return previous;
          if (previous.offRouteSamples === 0) return previous;
          return {
            ...previous,
            offRouteSamples: 0,
          };
        });
      },
      setRerouting: (value) => {
        setSession((previous) => {
          if (!previous) return previous;
          return {
            ...previous,
            rerouting: value,
          };
        });
      },
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
