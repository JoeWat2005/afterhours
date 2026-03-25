import type { CanonicalReportCategory } from "../../lib/api";

export type ConvexReportCategory =
  | "crime"
  | "lighting"
  | "unpaved"
  | "sketchy"
  | "other";

type ReportCategoryMapping = {
  canonical: CanonicalReportCategory;
  convex: ConvexReportCategory;
};

const CATEGORY_MAPPING_BY_UI_LABEL: Record<string, ReportCategoryMapping> = {
  crime: {
    canonical: "suspicious activity",
    convex: "crime",
  },
  "break in / burglary": {
    canonical: "theft",
    convex: "crime",
  },
  harassment: {
    canonical: "harassment",
    convex: "crime",
  },
  "unsafe area": {
    canonical: "suspicious activity",
    convex: "sketchy",
  },
  "poor lighting": {
    canonical: "poor lighting",
    convex: "lighting",
  },
  "road hazard / potholes": {
    canonical: "hazard",
    convex: "unpaved",
  },
  "anti-social behaviour": {
    canonical: "harassment",
    convex: "crime",
  },
  other: {
    canonical: "other",
    convex: "other",
  },
};

function normalizeKey(value: string) {
  return value.trim().toLowerCase();
}

export function mapUiIssueToCategories(value: string): ReportCategoryMapping {
  const mapping = CATEGORY_MAPPING_BY_UI_LABEL[normalizeKey(value)];
  if (mapping) {
    return mapping;
  }
  return {
    canonical: "other",
    convex: "other",
  };
}

export function mapCanonicalToConvexCategory(
  category: CanonicalReportCategory,
): ConvexReportCategory {
  switch (category) {
    case "poor lighting":
      return "lighting";
    case "hazard":
      return "unpaved";
    case "suspicious activity":
      return "sketchy";
    case "assault":
    case "robbery":
    case "harassment":
    case "theft":
      return "crime";
    default:
      return "other";
  }
}
