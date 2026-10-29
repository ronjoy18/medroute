from decimal import Decimal
from django.db.models.signals import post_save, m2m_changed
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth import get_user_model

from .models import (
    Order,
    CareRequest,
    CompanionshipScheduler,
    PatientProfile,
    CareGiverProfile,
    DoctorProfile,
)

User = get_user_model()
COMPANY_EMAIL = getattr(settings, "COMPANY_ALERT_EMAIL", getattr(settings, "DEFAULT_FROM_EMAIL", "admin@medroute.com"))
BASE_URL = getattr(settings, "BASE_URL", "https://medrouterrands.com").rstrip("/")


# ==============================================================================
# 1. USER ACCOUNT CREATION (Patient, Doctor, Caregiver)
# ==============================================================================
@receiver(post_save, sender=User)
def send_welcome_and_onboarding_emails(sender, instance, created, **kwargs):
    if not created or not instance.email:
        return

    full_name = instance.get_full_name() or instance.username
    role = getattr(instance, "role", None)

    # 1A. Doctor Welcome (Includes credential/document requests)
    if role == "DOCTOR":
        subject = "[Medroute] Welcome Doctor - Action Required: License Verification"
        body = (
            f"Dear Dr. {full_name},\n\n"
            f"Welcome to the Medroute Global Healthcare Network.\n\n"
            f"Before your profile is published in our directory, compliance regulations "
            f"require verification of your credentials. Please reply directly to this email "
            f"with scanned copies of:\n"
            f"  1. Medical Board Practicing License\n"
            f"  2. Specialist Board Certification\n"
            f"  3. National Identification or Passport\n\n"
            f"You can review your console and setup here:\n"
            f"{BASE_URL}/dashboard/\n\n"
            f"Best regards,\n"
            f"Medroute Credentialing Board"
        )

    # 1B. Caregiver Welcome (Background check & certification submission)
    elif role == "CAREGIVER":
        subject = "[Medroute] Caregiver Onboarding - Submit Verification Documents"
        body = (
            f"Dear {full_name},\n\n"
            f"Thank you for joining Medroute Errands as a caregiver.\n\n"
            f"To complete your clinical onboarding and receive patient assignments, "
            f"please provide the following documents:\n"
            f"  1. Nursing / First Aid / BLS Certification\n"
            f"  2. Valid Certificate of Good Conduct\n"
            f"  3. Copy of National ID\n\n"
            f"Access your caregiver portal here:\n"
            f"{BASE_URL}/dashboard/\n\n"
            f"Best regards,\n"
            f"Medroute Operations Team"
        )

    # 1C. Standard Patient / Independent User Welcome
    else:
        subject = "[Medroute] Welcome to Medroute Clinical Systems"
        body = (
            f"Dear {full_name},\n\n"
            f"Your Medroute account has been registered successfully.\n\n"
            f"You can order tests, book errand assistance, and view reports at your dashboard:\n"
            f"{BASE_URL}/dashboard/\n\n"
            f"Warm regards,\n"
            f"Medroute Support Team"
        )

    send_mail(
        subject=subject,
        message=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[instance.email],
        fail_silently=True,
    )


# ==============================================================================
# 2. PATIENT REQUESTS A CAREGIVER (Lead / CareRequest)
# ==============================================================================
@receiver(post_save, sender=CareRequest)
def handle_care_request_notifications(sender, instance, created, **kwargs):
    if not created:
        return

    patient_name = instance.patient_name
    patient_email = instance.patient_email
    patient_phone = instance.patient_phone
    service_name = instance.service.name if instance.service else "Custom Errand"

    # 2A. Inform the Company
    company_subject = f"[ALERT] New Caregiver Request - {patient_name}"
    company_body = (
        f"A patient has requested a caregiver via the Care Connect portal.\n\n"
        f"--- PATIENT DETAILS ---\n"
        f"Name: {patient_name}\n"
        f"Email: {patient_email}\n"
        f"Phone: {patient_phone}\n"
        f"Service Requested: {service_name}\n"
        f"Status: PENDING PHYSICAL FOLLOW-UP\n\n"
        f"Please contact this client promptly to confirm details."
    )
    send_mail(
        subject=company_subject,
        message=company_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[COMPANY_EMAIL],
        fail_silently=True,
    )

    # 2B. Inform the Patient
    if patient_email:
        patient_subject = "[Medroute] We Have Received Your Caregiver Request"
        patient_body = (
            f"Dear {patient_name},\n\n"
            f"Thank you for requesting home-based caregiver assistance for '{service_name}'.\n\n"
            f"Our care coordination team has received your details (Phone: {patient_phone}) "
            f"and will call you shortly to discuss specific needs and schedule your session.\n\n"
            f"You can review your account activity anytime:\n"
            f"{BASE_URL}/dashboard/\n\n"
            f"Warm regards,\n"
            f"Medroute Errands Team"
        )
        send_mail(
            subject=patient_subject,
            message=patient_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[patient_email],
            fail_silently=True,
        )


# ==============================================================================
# 3. SCHEDULE CREATED (CompanionshipScheduler)
# ==============================================================================
@receiver(post_save, sender=CompanionshipScheduler)
def notify_on_schedule_creation(sender, instance, created, **kwargs):
    if not created:
        return

    patient = instance.patient
    caregiver = instance.caregiver
    patient_user = patient.user if patient else None
    caregiver_user = caregiver.user if caregiver else None

    patient_name = patient_user.get_full_name() or patient_user.username if patient_user else "Valued Client"
    caregiver_name = caregiver_user.get_full_name() or caregiver_user.username if caregiver_user else "Assigned Caregiver"
    service_title = instance.services.name if instance.services else "Care Routine"

    start_str = instance.start_date.strftime("%Y-%m-%d %I:%M %p") if instance.start_date else "TBD"
    end_str = instance.end_date.strftime("%I:%M %p") if instance.end_date else "Flexible"

    # 3A. Inform Company via Email
    company_subject = f"[Schedule Booked] #{str(instance.id)[:8]} - {patient_name} with {caregiver_name}"
    company_body = (
        f"A new care service session has been scheduled.\n\n"
        f"Schedule ID: {instance.id}\n"
        f"Patient: {patient_name} ({getattr(patient_user, 'email', 'N/A')})\n"
        f"Caregiver: {caregiver_name} ({getattr(caregiver_user, 'email', 'N/A')})\n"
        f"Service: {service_title}\n"
        f"Window: {start_str} - {end_str}\n"
        f"Status: {instance.status}\n"
    )
    send_mail(
        subject=company_subject,
        message=company_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[COMPANY_EMAIL],
        fail_silently=True,
    )

    # 3B. Inform Patient about the Booking
    if patient_user and patient_user.email:
        patient_subject = f"[Medroute] Booking Confirmed: {service_title}"
        patient_body = (
            f"Dear {patient_name},\n\n"
            f"Your service booking has been confirmed.\n\n"
            f"--- SESSION DETAILS ---\n"
            f"Service: {service_title}\n"
            f"Assigned Caregiver: {caregiver_name}\n"
            f"Date & Time: {start_str} to {end_str}\n\n"
            f"View your live itinerary at:\n"
            f"{BASE_URL}/dashboard/\n\n"
            f"Medroute Scheduling Desk"
        )
        send_mail(
            subject=patient_subject,
            message=patient_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[patient_user.email],
            fail_silently=True,
        )

    # 3C. Inform Scheduled Caregiver
    if caregiver_user and caregiver_user.email:
        caregiver_subject = f"[New Assignment] Care Session on {start_str}"
        caregiver_body = (
            f"Dear {caregiver_name},\n\n"
            f"You have been assigned to a caregiving session.\n\n"
            f"--- ASSIGNMENT DETAILS ---\n"
            f"Patient: {patient_name}\n"
            f"Service: {service_title}\n"
            f"Start Time: {start_str}\n"
            f"End Time: {end_str}\n\n"
            f"Open your roster to review client details:\n"
            f"{BASE_URL}/dashboard/\n\n"
            f"Medroute Operations Desk"
        )
        send_mail(
            subject=caregiver_subject,
            message=caregiver_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[caregiver_user.email],
            fail_silently=True,
        )


# ==============================================================================
# 4. PAYMENT SETTLEMENT ALERT (Order.is_paid)
# ==============================================================================
@receiver(post_save, sender=Order)
def notify_company_and_parties_on_payment(sender, instance, created, **kwargs):
    # Only fire once when payment is marked settled
    if instance.is_paid and not getattr(instance, "_payment_alert_sent", False):
        patient_user = instance.patient.user if instance.patient else None
        patient_name = patient_user.get_full_name() or patient_user.username if patient_user else "N/A"

        # 4A. Inform Company of Payment
        company_subject = f"[PAYMENT RECEIVED] Ksh {instance.total_cost} - Order #{str(instance.id)[:8]}"
        company_body = (
            f"Payment has been settled.\n\n"
            f"Order Code: {instance.id}\n"
            f"Patient: {patient_name} ({getattr(patient_user, 'email', 'N/A')})\n"
            f"Amount Paid: Ksh {instance.total_cost}\n"
            f"Status: SETTLED / ACTIVE\n"
        )
        send_mail(
            subject=company_subject,
            message=company_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[COMPANY_EMAIL],
            fail_silently=True,
        )

        # 4B. Inform Patient of Receipt
        if patient_user and patient_user.email:
            patient_subject = f"[Receipt] Payment Received - Order #{str(instance.id)[:8]}"
            patient_body = (
                f"Dear {patient_name},\n\n"
                f"We received your payment of Ksh {instance.total_cost} for Order #{str(instance.id)[:8]}.\n\n"
                f"Your service is cleared and ongoing. View your invoice status:\n"
                f"{BASE_URL}/dashboard/\n\n"
                f"Medroute Accounts Team"
            )
            send_mail(
                subject=patient_subject,
                message=patient_body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[patient_user.email],
                fail_silently=True,
            )

        instance._payment_alert_sent = True