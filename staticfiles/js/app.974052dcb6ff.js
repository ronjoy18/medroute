/**
 * LabCare Global Application & Service Interceptor
 */

function handleServiceSelection(serviceId, serviceName, servicePrice) {
  const isAuthenticated = document.body.dataset.authenticated === "true";

  if (!isAuthenticated) {
    // Open the Auth Gate Modal on the homepage
    openAuthGateModal(serviceId, serviceName, servicePrice);
  } else {
    // Authenticated dispatch: route directly to patient dashboard
    window.location.href = `/dashboard/?action=order&service_id=${serviceId}`;
  }
}

function openAuthGateModal(serviceId, serviceName, servicePrice) {
  const modal = document.getElementById("auth-gate-modal");
  if (!modal) {
    // Fallback if modal container isn't rendered
    window.location.href = `/auth/?mode=register&role=patient&redirect_service=${serviceId}`;
    return;
  }

  // Populate selected service details
  document.getElementById("modal-service-name").textContent = serviceName;
  document.getElementById("modal-service-price").textContent = `$${servicePrice}`;
  
  // Set dynamic action buttons
  document.getElementById("modal-btn-login").href = `/auth/?mode=login&role=patient&redirect_service=${serviceId}`;
  document.getElementById("modal-btn-register").href = `/auth/?mode=register&role=patient&redirect_service=${serviceId}`;

  modal.style.display = "flex";
}

function closeAuthGateModal() {
  const modal = document.getElementById("auth-gate-modal");
  if (modal) modal.style.display = "none";
}

async function performDownloadReport(orderId) {
  try {
    const response = await fetch(`/api/v1/orders/${orderId}/download-report/`, {
      method: "GET"
    });
    
    if (response.status === 404) {
      alert("Validation hold: Laboratory report is still in analysis or being compiled.");
      return;
    }
    
    if (!response.ok) {
      alert("Access authorization error: Cannot access cross-profile clinical documents.");
      return;
    }
    
    const blob = await response.blob();
    const downloadUrl = window.URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = downloadUrl;
    link.download = `LabCare_Report_${orderId}.pdf`;
    document.body.appendChild(link);
    link.click();
    link.remove();
  } catch (err) {
    alert("Network connection failed during document retrieval.");
  }
}
