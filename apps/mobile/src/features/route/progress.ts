import type {
  GeoJSONGeometry,
  GeoJSONPosition,
  RouteNavigationStep,
} from "../../lib/api";

export type RouteCoordinate = {
  latitude: number;
  longitude: number;
};

export type RouteProgress = {
  progressRatio: number;
  distanceTravelledMetres: number;
  remainingDistanceMetres: number;
  remainingDurationSeconds: number;
  distanceFromRouteMetres: number;
  currentStepIndex: number;
};

type SegmentProjection = {
  distanceToSegmentMetres: number;
  alongSegmentMetres: number;
};

function clamp(value: number, min: number, max: number) {
  return Math.max(min, Math.min(max, value));
}

function toRadians(value: number) {
  return (value * Math.PI) / 180;
}

export function haversineMetres(a: RouteCoordinate, b: RouteCoordinate) {
  const earthRadiusMetres = 6_371_000;
  const latitudeDelta = toRadians(b.latitude - a.latitude);
  const longitudeDelta = toRadians(b.longitude - a.longitude);
  const aTerm =
    Math.sin(latitudeDelta / 2) ** 2 +
    Math.cos(toRadians(a.latitude)) *
      Math.cos(toRadians(b.latitude)) *
      Math.sin(longitudeDelta / 2) ** 2;
  return 2 * earthRadiusMetres * Math.atan2(Math.sqrt(aTerm), Math.sqrt(1 - aTerm));
}

function projectPointOntoSegment(
  point: RouteCoordinate,
  segmentStart: RouteCoordinate,
  segmentEnd: RouteCoordinate,
): SegmentProjection {
  // Project to local XY metres to keep the math simple and numerically stable.
  const latitudeScale = 110_540;
  const longitudeScale = 111_320 * Math.cos(toRadians(point.latitude));

  const startX = (segmentStart.longitude - point.longitude) * longitudeScale;
  const startY = (segmentStart.latitude - point.latitude) * latitudeScale;
  const endX = (segmentEnd.longitude - point.longitude) * longitudeScale;
  const endY = (segmentEnd.latitude - point.latitude) * latitudeScale;

  const segmentX = endX - startX;
  const segmentY = endY - startY;
  const segmentLengthSquared = segmentX * segmentX + segmentY * segmentY;

  if (segmentLengthSquared <= 0) {
    const distance = Math.sqrt(startX * startX + startY * startY);
    return {
      distanceToSegmentMetres: distance,
      alongSegmentMetres: 0,
    };
  }

  const projectionFactor = clamp(
    -(startX * segmentX + startY * segmentY) / segmentLengthSquared,
    0,
    1,
  );
  const projectedX = startX + segmentX * projectionFactor;
  const projectedY = startY + segmentY * projectionFactor;

  return {
    distanceToSegmentMetres: Math.sqrt(projectedX * projectedX + projectedY * projectedY),
    alongSegmentMetres:
      Math.sqrt(segmentLengthSquared) * projectionFactor,
  };
}

export function flattenGeometryCoordinates(
  geometry: GeoJSONGeometry | null,
): RouteCoordinate[] {
  if (!geometry) return [];
  const rawCoordinates: GeoJSONPosition[] =
    geometry.type === "LineString"
      ? geometry.coordinates
      : geometry.coordinates.flat();

  const flattened = rawCoordinates
    .filter((value) => Array.isArray(value) && value.length >= 2)
    .map((value) => ({
      longitude: Number(value[0]),
      latitude: Number(value[1]),
    }))
    .filter(
      (value) =>
        Number.isFinite(value.latitude) &&
        Number.isFinite(value.longitude) &&
        Math.abs(value.latitude) <= 90 &&
        Math.abs(value.longitude) <= 180,
    );

  if (flattened.length <= 1) {
    return flattened;
  }

  // Deduplicate adjacent repeated points.
  const deduped: RouteCoordinate[] = [flattened[0]];
  for (let index = 1; index < flattened.length; index += 1) {
    const previous = deduped[deduped.length - 1];
    const current = flattened[index];
    if (
      previous.latitude !== current.latitude ||
      previous.longitude !== current.longitude
    ) {
      deduped.push(current);
    }
  }
  return deduped;
}

function getTotalRouteLengthMetres(route: RouteCoordinate[]) {
  let total = 0;
  for (let index = 1; index < route.length; index += 1) {
    total += haversineMetres(route[index - 1], route[index]);
  }
  return total;
}

function getCurrentStepIndex(
  distanceTravelledMetres: number,
  navigationSteps: RouteNavigationStep[],
) {
  if (!navigationSteps.length) return 0;
  let cumulative = 0;
  for (let index = 0; index < navigationSteps.length; index += 1) {
    cumulative += navigationSteps[index].distance_metres;
    if (distanceTravelledMetres <= cumulative) {
      return index;
    }
  }
  return navigationSteps.length - 1;
}

export function computeRouteProgress(
  location: RouteCoordinate,
  routeCoordinates: RouteCoordinate[],
  routeDurationSeconds: number,
  navigationSteps: RouteNavigationStep[],
): RouteProgress {
  if (routeCoordinates.length < 2) {
    return {
      progressRatio: 0,
      distanceTravelledMetres: 0,
      remainingDistanceMetres: 0,
      remainingDurationSeconds: routeDurationSeconds,
      distanceFromRouteMetres: Number.POSITIVE_INFINITY,
      currentStepIndex: 0,
    };
  }

  const totalLengthMetres = getTotalRouteLengthMetres(routeCoordinates);
  let closestDistance = Number.POSITIVE_INFINITY;
  let travelledAtClosestPoint = 0;
  let cumulativeDistance = 0;

  for (let index = 1; index < routeCoordinates.length; index += 1) {
    const segmentStart = routeCoordinates[index - 1];
    const segmentEnd = routeCoordinates[index];
    const segmentLength = haversineMetres(segmentStart, segmentEnd);
    const projection = projectPointOntoSegment(location, segmentStart, segmentEnd);

    if (projection.distanceToSegmentMetres < closestDistance) {
      closestDistance = projection.distanceToSegmentMetres;
      travelledAtClosestPoint = cumulativeDistance + projection.alongSegmentMetres;
    }

    cumulativeDistance += segmentLength;
  }

  const distanceTravelledMetres = clamp(travelledAtClosestPoint, 0, totalLengthMetres);
  const remainingDistanceMetres = Math.max(0, totalLengthMetres - distanceTravelledMetres);
  const progressRatio =
    totalLengthMetres > 0
      ? clamp(distanceTravelledMetres / totalLengthMetres, 0, 1)
      : 0;
  const remainingDurationSeconds = Math.max(
    0,
    Math.round(routeDurationSeconds * (1 - progressRatio)),
  );

  return {
    progressRatio,
    distanceTravelledMetres,
    remainingDistanceMetres,
    remainingDurationSeconds,
    distanceFromRouteMetres: closestDistance,
    currentStepIndex: getCurrentStepIndex(distanceTravelledMetres, navigationSteps),
  };
}
