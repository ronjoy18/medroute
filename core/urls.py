
from django.urls import path
from . import views

urlpatterns = [
    # Static Entry/Landing UI routes
    path("", views.home_view, name="home-page"),
    path("index/page/", views.index_view, name="index-page"),
    path("auth/", views.auth_view, name="auth-page"),
    path("portal/internal-auth/", views.internal_login_view, name="internal-auth-page"),
    path("dashboard/", views.dashboard_dispatcher, name="dashboard-dispatcher"),

    # REST Framework Endpoints
    path("api/v1/auth/register/", views.PublicRegisterAPIView.as_view(), name="api-register"),
    path("api/v1/auth/login/", views.SessionLoginAPIView.as_view(), name="api-login"),
    path("api/v1/auth/internal-login/", views.InternalSecureLoginAPIView.as_view(), name="api-internal-login"),
    path("api/v1/auth/logout/", views.SessionLogoutAPIView.as_view(), name="api-logout"),

    path("api/v1/catalog/", views.PublicCatalogAPIView.as_view(), name="api-catalog"),
    path("api/v1/doctor/onboard-patient/", views.DoctorOnboardPatientAPIView.as_view(), name="api-doctor-onboard"),
   
    path("api/v1/orders/", views.OrderListCreateAPIView.as_view(), name="api-orders"),
    path("api/v1/orders/<uuid:order_id>/download-report/", views.SecureDocumentDownloadView.as_view(), name="api-download-report"),
    path("api/v1/doctor/my-patients/", views.DoctorMyPatientsAPIView.as_view(), name="api-doctor-my-patients"),
    path("api/v1/doctor/my-patients/<uuid:patient_id>/", views.DoctorPatientDetailAPIView.as_view(), name="api-doctor-patient-detail"),
    path("api/v1/patient/me/", views.PatientProfileDetailAPIView.as_view(), name="api-patient-me"),
    path("api/v1/orders/<uuid:order_id>/pay/", views.SimulatePaymentAPIView.as_view(), name="api-simulate-pay"),
    path("orders/<uuid:order_id>/pay/", views.payment_checkout_view, name="order-payment-page"),
    path("directory/doctors/", views.global_doctor_directory_page, name="global-doctor-directory"),
    path("api/v1/global-doctors/", views.GlobalDoctorDirectoryAPIView.as_view(), name="api-global-doctors"),
    path("api/v1/global-doctors/<int:doctor_id>/connect/", views.GlobalDoctorInquiryCreateAPIView.as_view(), name="api-doctor-connect"),
    path("directory/preview/", views.global_doctor_directory_page, name="doctor-directory-alias"),
    path("api/v1/patient/global-connections/", views.PatientGlobalInquiriesAPIView.as_view(), name="api-patient-global-connections"),
    path("api/v1/doctor/global-inquiries/", views.DoctorGlobalInquiriesAPIView.as_view(), name="api-doctor-global-inquiries"),
    path("api/v1/caregiver/my-patients/", views.CareGiverMyPatientsAPIView.as_view(), name="api-caregiver-my-patients"),
    path("api/v1/caregiver/my-patients/<uuid:patient_id>/", views.CareGiverPatientDetailAPIView.as_view(), name="api-caregiverpatient-patient-detail"),
    path("api/v1/schedules/", views.CareScheduleAPIView.as_view(), name="api-schedules"), 
    path("about-us/", views.about_view, name = "about-us"),#.AboutUsAPIView.as_view(), ),
    path("connect-care-giver/", views.connectcare_view,name="api-home-care") 
]

