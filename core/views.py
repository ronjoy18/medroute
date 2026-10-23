from django.db.models import Q
import os
from django.utils import timezone
from django.http import FileResponse, Http404
from django.urls import reverse
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import get_object_or_404, render, redirect
from rest_framework import generics, status, views, permissions
from rest_framework.response import Response
from django.db import transaction, DatabaseError
from django.utils.dateparse import parse_datetime
import uuid
from .models import User, CareRequest,CareGiverProfile, DoctorProfile,CompanionshipScheduler, PatientProfile, LabService, Order, ReferralLedger
from .serializers import (
    UserRegistrationSerializer, LabServiceSerializer, OrderSerializer, 
    DoctorOnboardPatientSerializer, ReferralLedgerSerializer, CompanionshipSchedulerSerializer,
    CareRequestSerializer
)
from datetime import date, timedelta
from .permissions import IsInternalStaff, IsDoctorOwner, IsCareGiverOwner,IsPatientOwner, DocumentAccessPermission
from labcare import settings
from .models import GlobalDoctorInquiry, CareGiverProfile
from core import models 


# -------------------------------------------------------------
# Frontend Page Views
# -------------------------------------------------------------
def index_view(request):
    services = LabService.objects.filter(is_active=True).select_related("category")
    return render(request, "index.html", {"services": services})
def home_view(request):
        return render(request, 'home.html')
def auth_view(request):
    return render(request, "auth.html")
def connectcare_view(request):
    return render (request, 'contactus.html')
def internal_login_view(request):
    return render(request, "internal_login.html")
def about_view(request):
    return render(request, 'aboutus.html')
def info_view(request):
    return render(request, 'info.html')

def dashboard_dispatcher(request):
    if not request.user.is_authenticated:
        return redirect("auth-page")
    if request.user.role == User.Role.DOCTOR:
        return render(request, "dashboard_doctor.html")
    if request.user.role == User.Role.PATIENT:
        return render(request, "dashboard_patient.html")
    if request.user.role == User.Role.CAREGIVER:
        return render(request, "caregiver_dashboard.html")
    if request.user.is_internal():
        return redirect("/admin/")
    return redirect("index-page")


# -------------------------------------------------------------
# Authentication Endpoints
# -------------------------------------------------------------
class PublicRegisterAPIView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]


class SessionLoginAPIView(views.APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        username = request.data.get("username")
        password = request.data.get("password")
        user = authenticate(request, username=username, password=password)

        if not user:
            return Response({"detail": "Invalid authentication credentials."}, status=status.HTTP_401_UNAUTHORIZED)
        
        # Scoping verification: Internal users are blocked on the public login
        if request.data.get("portal") == "public" and user.is_internal():
            return Response({"detail": "Unauthorized portal access. Security boundaries enforced."}, status=status.HTTP_403_FORBIDDEN)
        
        login(request, user)
        return Response({
            "message": "Authentication successful.",
            "user": {
                "id": str(user.id),
                "username": user.username,
                "role": user.role,
                "full_name": user.get_full_name()
            }
        })


class InternalSecureLoginAPIView(views.APIView):
    """Restricted login route accessible only at unadvertised endpoints."""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        username = request.data.get("username")
        password = request.data.get("password")
        user = authenticate(request, username=username, password=password)

        if not user or not user.is_internal():
            return Response({"detail": "Access Denied: Non-privileged authentication source."}, status=status.HTTP_403_FORBIDDEN)
        
        login(request, user)
        return Response({"message": "Staff/Admin session successfully anchored."})


class SessionLogoutAPIView(views.APIView):
    def post(self, request):
        logout(request)
        return Response({"message": "Session invalidated."})


# -------------------------------------------------------------
# Core Domain Functionality
# -------------------------------------------------------------
class PublicCatalogAPIView(generics.ListAPIView):
    queryset = LabService.objects.filter(is_active=True).select_related("category")
    serializer_class = LabServiceSerializer
    permission_classes = [permissions.AllowAny]


class DoctorOnboardPatientAPIView(views.APIView):
    permission_classes = [IsDoctorOwner]

    def post(self, request):
        serializer = DoctorOnboardPatientSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        if User.objects.filter(username=data["username"]).exists():
            return Response({"username": "Username already taken."}, status=status.HTTP_400_BAD_REQUEST)

        temp_password = f"LabCare#{uuid.uuid4().hex[:8]}"
        user = User.objects.create_user(
            username=data["username"],
            email=data["email"],
            first_name=data["first_name"],
            last_name=data["last_name"],
            phone_number=data.get("phone_number", ""),
            role=User.Role.PATIENT,
            password=temp_password
        )

        doctor_profile = request.user.doctor_profile
        patient_profile = PatientProfile.objects.create(
            user=user,
            patient_type=PatientProfile.PatientType.DOCTOR_REFERRED,
            primary_doctor=doctor_profile,
            date_of_birth=data.get("date_of_birth"),
            emergency_contact=data.get("emergency_contact", "")
        )

        created_order = None
        service_ids = data.get("initial_service_ids", [])
        if service_ids:
            services = LabService.objects.filter(id__in=service_ids, is_active=True)
            created_order = Order.objects.create(
                patient=patient_profile,
                ordering_doctor=doctor_profile
            )
            created_order.services.set(services)
            created_order.calculate_cost()

        return Response({
            "message": "Patient profile established and linked to your practice.",
            "patient_id": str(patient_profile.id),
            "temporary_access_key": temp_password,
            "order_id": str(created_order.id) if created_order else None
        }, status=status.HTTP_201_CREATED)



class OrderListCreateAPIView(generics.ListCreateAPIView):
    serializer_class = OrderSerializer

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return Order.objects.none()
        if user.is_internal():
            return Order.objects.all().select_related("patient__user", "ordering_doctor__user").prefetch_related("services")
        if user.is_doctor():
            return Order.objects.filter(ordering_doctor__user=user).select_related("patient__user").prefetch_related("services")
        if user.is_patient():
            return Order.objects.filter(patient__user=user).prefetch_related("services")
        return Order.objects.none()

    def create(self, request, *args, **kwargs):
        user = request.user
        if not user.is_authenticated:
            return Response({"detail": "Authentication required."}, status=status.HTTP_401_UNAUTHORIZED)

        services_ids = request.data.get("services", [])
        custom_test_names = request.data.get("custom_test_names", "").strip()

        if not services_ids and not custom_test_names:
            return Response({"detail": "Please select at least one test or specify custom requirements."}, status=status.HTTP_400_BAD_REQUEST)

        # 1. Doctor placing order for patient
        if user.is_doctor():
            patient_id = request.data.get("patient_id")
            if not patient_id:
                return Response({"patient_id": ["Please select a patient from your roster."]}, status=status.HTTP_400_BAD_REQUEST)
            try:
                patient = PatientProfile.objects.get(id=patient_id, primary_doctor=user.doctor_profile)
            except (PatientProfile.DoesNotExist, ValueError):
                return Response({"patient_id": ["Invalid patient selected."]}, status=status.HTTP_400_BAD_REQUEST)
            
            ordering_doctor = user.doctor_profile

        # 2. Patient self-booking
        elif user.is_patient():
            patient = user.patient_profile
            ordering_doctor = patient.primary_doctor

        else:
            return Response({"detail": "Unauthorized role for intake creation."}, status=status.HTTP_403_FORBIDDEN)

        order = Order.objects.create(
            patient=patient,
            ordering_doctor=ordering_doctor,
            order_type=request.data.get("order_type", Order.OrderType.LAB_TEST),
            custom_test_names=custom_test_names
        )

        if services_ids:
            services = LabService.objects.filter(id__in=services_ids, is_active=True)
            order.services.set(services)
            order.total_cost = order.calculate_cost()
            order.save(update_fields=["total_cost"])

        serializer = self.get_serializer(order)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

        return super().create(request, *args, **kwargs)


class SecureDocumentDownloadView(views.APIView):
    permission_classes = [DocumentAccessPermission]

    def get(self, request, order_id):
        order = get_object_or_404(Order, id=order_id)
        self.check_object_permissions(request, order)

        if not order.attached_report_pdf:
            raise Http404("Document compilation incomplete or pending validation.")

        file_path = order.attached_report_pdf.path
        if not os.path.exists(file_path):
            raise Http404("Filesystem trace degraded. Physical file non-existent.")

        return FileResponse(
            open(file_path, "rb"),
            as_attachment=True,
            filename=os.path.basename(file_path),
            content_type="application/pdf"
        )


#---doctors managed patients--@
class DoctorMyPatientsAPIView(views.APIView):
    permission_classes = [IsDoctorOwner]

    def get(self, request):
        doctor = request.user.doctor_profile
        patients = (
            PatientProfile.objects.filter(
                primary_doctor=doctor,
                is_archived_by_doctor=False
            )
            .select_related("user")
            .prefetch_related("orders")
            .order_by("-created_at")
        )

        data = []
        for p in patients:
            orders = p.orders.filter(ordering_doctor=doctor)
            data.append({
                "id": str(p.id),
                "full_name": p.user.get_full_name() or p.user.username,
                "username": p.user.username,
                "email": p.user.email,
                "phone": p.user.phone_number or "Not Provided",
                "emergency_contact": p.emergency_contact or "None",
                "date_of_birth": p.date_of_birth.strftime("%b %d, %Y") if p.date_of_birth else "N/A",
                "registered_on": p.created_at.strftime("%b %d, %Y"),
                "total_orders": orders.count(),
                "pending_orders": orders.filter(status__in=[Order.Status.PENDING]).count(),
                "completed_orders": orders.filter(status=Order.Status.COMPLETED).count(),
            })

        return Response(data)
    
    # --- Doctor Patient Management Endpoints ---
class DoctorPatientDetailAPIView(views.APIView):
    """Allows doctors to view or unlink/remove a patient from their roster."""
    permission_classes = [IsDoctorOwner]

    def delete(self, request, patient_id):
        patient = get_object_or_404(
            PatientProfile, id=patient_id, primary_doctor=request.user.doctor_profile
        )
        # Soft-archive so historical orders and referral ledger records remain intact
        patient.is_archived_by_doctor = True
        patient.save(update_fields=["is_archived_by_doctor"])
        return Response({"message": "Patient successfully removed from your active roster."})


# --- Patient Payment & Referral Profile View ---

class PatientProfileDetailAPIView(views.APIView):
    permission_classes = [IsPatientOwner]

    def get(self, request):
        p = request.user.patient_profile
        return Response({
            "referral_code": p.referral_code,
            "referral_link": f"{getattr(settings, 'BASE_URL', 'https://*.onrender.com')}/auth/?ref={p.referral_code}",
            "promo_credits": str(p.promo_credits),
            "patient_type": p.patient_type
        })


class SimulatePaymentAPIView(views.APIView):
    """Simulated payment endpoint under active development."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, order_id):
        order = get_object_or_404(Order, id=order_id)
        
        # Verify permissions
        if request.user.is_patient() and order.patient.user != request.user:
            return Response({"detail": "Unauthorized"}, status=403)
        if request.user.is_doctor() and order.ordering_doctor.user != request.user:
            return Response({"detail": "Unauthorized"}, status=403)

        if order.is_paid:
            return Response({"message": "Order is already paid."})

        order.is_paid = True
        order.save()  # Triggers referral bonuses and signals

        return Response({
            "message": "Payment simulation successful. Invoice settled and bonuses updated.",
            "status": "PAID"
        })

    

def payment_checkout_view(request, order_id):
    """Renders the dedicated clinical checkout page for a specific order."""
    if not request.user.is_authenticated:
        return redirect("auth-page")
    order = get_object_or_404(Order, id=order_id)
    
    # Ownership boundary: Only the owner patient or the ordering doctor can access
    if request.user.is_patient() and order.patient.user != request.user:
        raise Http404("Unauthorized order reference.")
    if request.user.is_doctor() and order.ordering_doctor and order.ordering_doctor.user != request.user:
        raise Http404("Unauthorized order reference.")
        
    return render(request, "payment_checkout.html", {"order": order})


class GlobalDoctorDirectoryAPIView(views.APIView):
    """Public read-only directory endpoint for verified global doctors with parameter filtering."""
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        query = request.query_params.get("q", "").strip().lower()
        specialty = request.query_params.get("specialty", "").strip()
        country = request.query_params.get("country", "").strip()

        qs = DoctorProfile.objects.filter(is_verified_global=True).select_related("user")

        if query:
            qs = qs.filter(
                Q(user__first_name__icontains=query) |
                Q(user__last_name__icontains=query) |
                Q(specialty__icontains=query) |
                Q(hospital_affiliation__icontains=query) |
                Q(bio__icontains=query)
            )

        if specialty:
            qs = qs.filter(specialty__iexact=specialty)
        if country:
            qs = qs.filter(country_name__iexact=country)

        data = []
        for d in qs:
            avatar_url = d.profile_picture.url if d.profile_picture else None
            data.append({
                "id": str(d.id),
                "full_name": d.user.get_full_name() or d.user.username,
                "first_name": d.user.first_name,
                "last_name": d.user.last_name,
                "specialty": d.specialty or "General Medical Specialist",
                "hospital": d.hospital_affiliation or "Independent Surgical Facility",
                "country_name": d.country_name,
                "country_iso": d.country_iso.lower(),
                "years_experience": d.years_of_experience,
                "star_rating": float(d.star_rating),
                "bio": d.bio,
                "bio_brief": (d.bio.split("\n")[0][:140] + "...") if d.bio else "Verified international physician offering specialized care and remote reviews.",
                "achievements": d.achievements or "Board certified clinical specialist with international surgical track record.",
                "avatar": avatar_url,
            })

        return Response(data)


class GlobalDoctorInquiryCreateAPIView(views.APIView):
    """Collects patient contact details to initiate team callback."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, doctor_id):
        doctor = get_object_or_404(DoctorProfile, id=doctor_id, is_verified_global=True)
        phone = request.data.get("phone", "").strip() or (request.user.phone_number if hasattr(request.user, "phone_number") else "")
        concern = request.data.get("clinical_concern", "").strip()

        if not phone:
            return Response({"phone": ["A valid contact phone number is required so our team can reach you."]}, status=400)

        patient_profile = getattr(request.user, "patient_profile", None)

        inquiry = GlobalDoctorInquiry.objects.create(
            doctor=doctor,
            patient=patient_profile,
            patient_full_name=request.user.get_full_name() or request.user.username,
            patient_phone=phone,
            patient_email=request.user.email,
            clinical_concern=concern or "Direct referral & cross-border treatment connection request."
        )

        return Response({
            "message": "Connection registered! Our care coordination team will contact you via phone within 24 hours.",
            "inquiry_id": str(inquiry.id)
        }, status=201)


def global_doctor_directory_page(request):
    """Renders the LinkedIn-style Global Doctor Directory."""
    # Pre-extract distinct specialties and countries for the filter dropdowns
    specialties = (
        DoctorProfile.objects.filter(is_verified_global=True)
        .exclude(specialty="")
        .values_list("specialty", flat=True)
        .distinct()
    )
    countries = (
        DoctorProfile.objects.filter(is_verified_global=True)
        .exclude(country_name="")
        .values_list("country_name", flat=True)
        .distinct()
    )
    return render(request, "directory_global_doctors.html", {
        "specialties": sorted(list(specialties)),
        "countries": sorted(list(countries))
    })


class PatientGlobalInquiriesAPIView(views.APIView):
    """Returns all global doctor connections made by the authenticated patient."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if not request.user.is_patient():
            return Response([])
        
        inquiries = (
            GlobalDoctorInquiry.objects.filter(patient__user=request.user)
            .select_related("doctor__user")
            .order_by("-created_at")
        )
        data = [
            {
                "id": str(i.id),
                "doctor_name": f"Dr. {i.doctor.user.get_full_name() or i.doctor.user.username}",
                "specialty": i.doctor.specialty or "Specialist",
                "country": i.doctor.country_name,
                "country_iso": i.doctor.country_iso.lower(),
                "hospital": i.doctor.hospital_affiliation or "International Center",
                "status": i.status,
                "created_at": i.created_at.strftime("%b %d, %Y")
            }
            for i in inquiries
        ]
        return Response(data)


class DoctorGlobalInquiriesAPIView(views.APIView):
    """Returns all international patient connections for a global doctor."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if not request.user.is_doctor():
            return Response({"is_global": False, "inquiries": []})
        
        doc = getattr(request.user, "doctor_profile", None)
        if not doc or not doc.is_verified_global:
            return Response({"is_global": False, "inquiries": []})

        inquiries = (
            GlobalDoctorInquiry.objects.filter(doctor=doc)
            .select_related("patient__user")
            .order_by("-created_at")
        )
        data = [
            {
                "id": str(i.id),
                "patient_name": i.patient_full_name,
                "patient_phone": i.patient_phone,
                "patient_email": i.patient_email,
                "concern": i.clinical_concern or "Consultation / Surgical review inquiry",
                "status": i.status,
                "requested_on": i.created_at.strftime("%b %d, %Y")
            }
            for i in inquiries
        ]
        return Response({"is_global": True, "inquiries": data})

class CareGiverMyPatientsAPIView(views.APIView):
    permission_classes= [IsCareGiverOwner]

    def get(self, request):
        caregiver, _ = CareGiverProfile.objects.get_or_create(user=request.user)
        patients = (
            PatientProfile.objects.filter(
                caregiver = caregiver,
                archived_by_caregiver = False
            )
            .select_related("user")
            .prefetch_related("orders")
            .order_by("-created_at")
        )

        data = []
        for p in patients:
            orders = p.orders.objects.get_all()
            data.append({
                "id": str(p.id),
                "full_name": p.user.get_full_name() or p.user.username,
                "username": p.user.username,
                "email": p.user.email,
                "phone": p.user.phone_number or "Not Provided",
                "emergency_contact": p.emergency_contact or "None",
                "date_of_birth": p.date_of_birth.strftime("%b %d, %Y") if p.date_of_birth else "N/A",
                "registered_on": p.created_at.strftime("%b %d, %Y"),
                "total_orders": orders.count(),
                "pending_orders": orders.filter(status__in=[Order.Status.PENDING]).count(),
                "completed_orders": orders.filter(status=Order.Status.COMPLETED).count(),
                })
        return Response(data)

class CareGiverPatientDetailAPIView(views.APIView):
    permissions_classes= [IsCareGiverOwner]

    def delete(self, request, patient_id ):
        patient = request.object_or_404(
            PatientProfile, id = patient_id, caregiver= request.user.caregiver_profile
        )
        patient.is_archavived_by_caregiver = True
        patient.save(update_fields=["archived_by_caregiver"])
        return Response({"message": "Patient successfully removed from your active roster."})
        


def round_to_nearest_five_minutes(dt):
    """
    Rounds a datetime object to the nearest 5-minute boundary
    and resets seconds and microseconds to 0.
    """
    discard = timedelta(
        minutes=dt.minute % 5,
        seconds=dt.second,
        microseconds=dt.microsecond
    )
    dt -= discard
    if discard >= timedelta(minutes=2.5):
        dt += timedelta(minutes=5)
    return dt


class CareScheduleAPIView(generics.ListCreateAPIView):
    serializer_class = CompanionshipSchedulerSerializer
    permission_classes = [permissions.IsAuthenticated]

    medroute_OPEN_HOUR = 6    # 06:00 AM
    medroute_CLOSE_HOUR = 18  # 06:00 PM

    def get_queryset(self):
        user = self.request.user
        if user.is_internal():
            return CompanionshipScheduler.objects.all().select_related("caregiver__user", "patient__user", "services").order_by("-start_date")
        if user.is_caregiver():
            return CompanionshipScheduler.objects.filter(caregiver__user=user).select_related("patient__user", "services").order_by("-start_date")
        if user.is_patient():
            return CompanionshipScheduler.objects.filter(patient__user=user).select_related("caregiver__user", "services").order_by("-start_date")
        return CompanionshipScheduler.objects.none()

    def create(self, request, *args, **kwargs):
        user = request.user
        if not user.is_patient():
            return Response(
                {"detail": "Only registered patients can schedule care services."},
                status=status.HTTP_403_FORBIDDEN
            )

        patient, _ = PatientProfile.objects.get_or_create(user=user)

        # Support both 'services_id' and 'start_date' / 'start_time' keys
        services_id = request.data.get("services_id")
        start_date_raw = request.data.get("start_date") or request.data.get("start_time")

        if not services_id or not start_date_raw:
            return Response(
                {"detail": "Both services_id and start_date are required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        services = get_object_or_404(LabService, id=services_id, is_active=True)
        start_date = parse_datetime(start_date_raw)
        
        if not start_date:
            return Response(
                {"detail": "Invalid start_date format. Please provide a valid timestamp."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Ensure datetime is timezone-aware
        if timezone.is_naive(start_date):
            start_date = timezone.make_aware(start_date, timezone.get_current_timezone())

        # Convert to configured local time
        local_start = timezone.localtime(start_date)

        # Round to the nearest 5 minutes (e.g., 09:23 -> 09:25)
        local_start = round_to_nearest_five_minutes(local_start)

        # Prevent past bookings
        if local_start < timezone.now():
            return Response(
                {"detail": "Session bookings cannot be scheduled in the past."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Set session duration (60 minutes default instead of 720 minutes / 12 hours)
        session_duration = getattr(services, "duration_minutes", 60)
        local_end = local_start + timedelta(minutes=session_duration)

        # Check operating hours window (06:00 AM - 06:00 PM)
        is_before_open = local_start.hour < self.medroute_OPEN_HOUR
        is_after_close = (local_end.hour > self.medroute_CLOSE_HOUR) or (
            local_end.hour == self.medroute_CLOSE_HOUR and local_end.minute > 0
        )

        if is_before_open or is_after_close:
            return Response(
                {
                    "detail": (
                        f"Medroute operates strictly from 06:00 AM to 06:00 PM. "
                        f"A session running {local_start.strftime('%I:%M %p')} - {local_end.strftime('%I:%M %p')} "
                        f"falls outside operating hours."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # Save normalized time back
        start_date = local_start
        end_date = local_end

        with transaction.atomic():
            busy_caregiver_ids = CompanionshipScheduler.objects.filter(
                status=CompanionshipScheduler.Status.SCHEDULED,
                start_date__lt=end_date,
                end_date__gt=start_date
            ).values_list("caregiver_id", flat=True)

            caregiver = None

            # 1. Preferred caregiver
            if patient.caregiver and patient.caregiver.id not in busy_caregiver_ids and patient.caregiver.user.is_active:
                caregiver = patient.caregiver

            # 2. Any active verified caregiver
            if not caregiver:
                caregiver = (
                    CareGiverProfile.objects
                    .filter(user__is_active=True, is_verified=True)
                    .exclude(id__in=busy_caregiver_ids)
                    .first()
                )

            # 3. Fallback: Any active caregiver
            if not caregiver:
                caregiver = (
                    CareGiverProfile.objects
                    .filter(user__is_active=True)
                    .exclude(id__in=busy_caregiver_ids)
                    .first()
                )

            if not caregiver:
                return Response(
                    {"detail": "All academy caregivers are booked during this time window. Please pick another slot."},
                    status=status.HTTP_409_CONFLICT
                )

            if patient.caregiver != caregiver:
                PatientProfile.objects.filter(id=patient.id).update(caregiver=caregiver)

            order = Order.objects.create(
                patient=patient,
                caregiver=caregiver,
                booking_start=start_date,
                booking_end=end_date,
                total_cost=services.price,
                status=Order.Status.PENDING
            )
            order.services.set([services])

            schedule = CompanionshipScheduler.objects.create(
                order=order,
                patient=patient,
                caregiver=caregiver,
                services=services,
                start_date=start_date,
                end_date=end_date,
                status=CompanionshipScheduler.Status.SCHEDULED
            )

        serializer = self.get_serializer(schedule)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class AboutUsAPIView(views.APIView):
    permission_classes=[permissions.AllowAny]

    def count(self, request):
        error_message = None
        number_services = 0
        active_services = LabService.objects.all()
        
        try:
            if active_services.exists():
               active_services 
               number_services = LabService.objects.count()
            else:
               number_services
               error_message = "failed to load services"
        except DatabaseError:
        # This catches database crashes, connection timeouts, or missing tables
           error_message = "Services failed to load due to a system error. Please try again later."

        context = {
            'services': active_services,
            'error_message': error_message,
        }
        return render(request, 'aboutus.html', context)

class ConnectCaregiverAPIView(views.APIView):
    # This automatically returns HTTP 401 if request.user is not logged in
    permission_classes = [permissions.IsAuthenticated]

    def handle_exception(self, exc, ):
        # Optional: return the redirect URL explicitly if unauthenticated
        response = super().handle_exception(exc)
        if response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]:
            response.data = {
                "detail": "Authentication credentials were not provided or session expired.",
                "redirect_url": reverse("auth-page")
            }
        return response

    def post(self, request):
        user = request.user
        patient, _ = PatientProfile.objects.get_or_create(user=user)

        service_id = request.data.get("service_id")
        if not service_id:
            return Response(
                {"detail": "Please select a service before submitting."},
                status=status.HTTP_400_BAD_REQUEST
            )

        service = get_object_or_404(LabService, id=service_id, is_active=True)

        full_name = user.get_full_name() or user.username
        phone = user.phone_number #getattr(user, "phone", "") or getattr(user, "patient_phone", "")
        email = user.email or ""

        care_request = CareRequest.objects.create(
            patient=patient,
            service=service,
            patient_name=full_name,
            patient_phone=phone,
            patient_email=email,
            status=CareRequest.RequestStatus.PENDING
        )

        return Response(
            {
                "id": care_request.id,
                "message": "Care request registered successfully.",
                "redirect_url": "/caregiver/thank-you/"
            },
            status=status.HTTP_201_CREATED
        )