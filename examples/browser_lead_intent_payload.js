const leadIntentState = {
  pageViews: 0,
  vehiclePageEnteredAt: null,
  vehiclePageTimeSeconds: 0,
  chatInteractions: 0,
  financingInquiries: 0,
  tradeInRequests: 0,
  testDriveInterest: false,
};

export function trackVehiclePageView() {
  leadIntentState.pageViews += 1;
  leadIntentState.vehiclePageEnteredAt = Date.now();
}

export function flushVehiclePageTime() {
  if (!leadIntentState.vehiclePageEnteredAt) {
    return;
  }

  const elapsedSeconds = Math.floor((Date.now() - leadIntentState.vehiclePageEnteredAt) / 1000);
  leadIntentState.vehiclePageTimeSeconds += Math.max(elapsedSeconds, 0);
  leadIntentState.vehiclePageEnteredAt = null;
}

export function trackChatInteraction(messageText) {
  leadIntentState.chatInteractions += 1;
  const normalized = messageText.toLowerCase();

  if (normalized.includes("finance") || normalized.includes("loan") || normalized.includes("emi")) {
    leadIntentState.financingInquiries += 1;
  }
  if (normalized.includes("trade-in") || normalized.includes("trade in") || normalized.includes("exchange")) {
    leadIntentState.tradeInRequests += 1;
  }
  if (normalized.includes("test drive")) {
    leadIntentState.testDriveInterest = true;
  }
}

export function trackFinancingInquiry() {
  leadIntentState.financingInquiries += 1;
}

export function trackTradeInRequest() {
  leadIntentState.tradeInRequests += 1;
}

export function trackTestDriveInterest() {
  leadIntentState.testDriveInterest = true;
}

export function buildLeadPayload(formValues) {
  flushVehiclePageTime();

  return {
    ...formValues,
    intent_signals: {
      page_views: leadIntentState.pageViews,
      vehicle_page_time_seconds: leadIntentState.vehiclePageTimeSeconds,
      chat_interactions: leadIntentState.chatInteractions,
      financing_inquiries: leadIntentState.financingInquiries,
      trade_in_requests: leadIntentState.tradeInRequests,
      test_drive_interest: leadIntentState.testDriveInterest,
    },
  };
}

export async function submitLead(formValues, dealershipId) {
  const payload = buildLeadPayload(formValues);

  const response = await fetch("/api/v1/leads", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Dealership-ID": dealershipId,
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error(`Lead create failed with status ${response.status}`);
  }

  return response.json();
}
