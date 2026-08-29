export type PurposeReportType = "business_trip" | "representative_expenses" | "gifts";

export type SavedPurposes = {
  business_trip: string;
  gifts: string;
};

export function switchReportPurpose(
  currentType: PurposeReportType,
  nextType: PurposeReportType,
  currentPurpose: string,
  savedPurposes: SavedPurposes,
  defaultGiftPurpose: string,
): { purpose: string; savedPurposes: SavedPurposes } {
  const nextSavedPurposes = { ...savedPurposes };
  if (currentType === "business_trip" || currentType === "gifts") {
    nextSavedPurposes[currentType] = currentPurpose;
  }
  const purpose = nextType === "business_trip"
    ? nextSavedPurposes.business_trip
    : nextType === "gifts"
      ? nextSavedPurposes.gifts || defaultGiftPurpose
      : "";
  return { purpose, savedPurposes: nextSavedPurposes };
}
