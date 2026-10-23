from decimal import Decimal
from django.db.models.signals import post_save, m2m_changed
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
from .models import Order, ReferralLedger, PatientProfile

@receiver(m2m_changed, sender=Order.services.through)
def calculate_order_total_on_service_change(sender, instance, action, **kwargs):
    if action in ["post_add", "post_remove", "post_clear"]:
        total = instance.calculate_cost()
        if instance.total_cost != total:
            instance.total_cost = total
            instance.save(update_fields=["total_cost"])

@receiver(post_save, sender=Order)
def process_order_lifecycle_events(sender, instance, created, **kwargs):
    # 1. Immediate Patient Intake Email
    if created:
        services_list = "\n".join([f" - {s.name} (Ksh{s.price})" for s in instance.services.all()])
        custom_notes = f"\nCustom Instructions / Requirements:\n{instance.custom_test_names}" if instance.custom_test_names else ""
        
        email_body = (
            f"Dear {instance.patient.user.get_full_name() or instance.patient.user.username},\n\n"
            f"Your service request has been received and registered into the LabCare Diagnostic queue.\n\n"
            f"--- INTAKE DETAILS ---\n"
            f"Order Tracking Code: {instance.id}\n"
            f"Category: {instance.get_order_type_display()}\n"
            f"Current Status: {instance.get_status_display()}\n"
            f"Total Billed: ksh{instance.total_cost}\n"
            f"{services_list}{custom_notes}\n\n"
            f"You can review your bill and complete payment directly from your patient workspace:\n"
            f"{getattr(settings, 'BASE_URL', 'https://medroute-xp7i.onrender.com/')}/dashboard/\n\n"
            f"LabCare Diagnostics Operations Team"
        )

        recipient_list = [instance.patient.user.email]
        if instance.ordering_doctor:
            recipient_list.append(instance.ordering_doctor.user.email)

        send_mail(
            subject=f"[LabCare] Request Confirmation: Order #{str(instance.id)[:8]}",
            message=email_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[e for e in recipient_list if e],
            fail_silently=True
        )

    # 2. Payment Verification, Doctor Commission & Patient Referral Promo Credit
    if instance.is_paid:
        # A. Doctor Referral Ledger
        if instance.ordering_doctor:
            if not ReferralLedger.objects.filter(order=instance).exists():
                doc = instance.ordering_doctor
                bonus = (instance.total_cost * (doc.commission_rate / Decimal("100.00"))).quantize(Decimal("0.01"))
                ReferralLedger.objects.create(
                    doctor=doc,
                    order=instance,
                    patient_identifier_snapshot=f"{instance.patient.user.get_full_name()} ({instance.patient.user.username})",
                    order_amount_snapshot=instance.total_cost,
                    allocated_percentage=doc.commission_rate,
                    bonus_amount=bonus
                )
                doc.total_accrued_bonus += bonus
                doc.save(update_fields=["total_accrued_bonus"])

        # B. Independent Patient Referral Promo Reward (10 credit per paying referral)
        patient = instance.patient
        if patient.referred_by and patient.patient_type == PatientProfile.PatientType.INDEPENDENT:
            # Grant 10.00 promo credit once per referred patient's first completed payment
            if not Order.objects.filter(patient=patient, is_paid=True).exclude(id=instance.id).exists():
                referrer = patient.referred_by
                referrer.promo_credits += Decimal("10.00")
                referrer.save(update_fields=["promo_credits"])
                send_mail(
                    subject="[LabCare Promo] Referral Reward Credited!",
                    message=f"Your referral {patient.user.first_name} completed their first booking! 10.00% has been credited to your next service.",
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[referrer.user.email],
                    fail_silently=True
                )

    # 3. Lab Results Availability Alert
    if instance.status == Order.Status.COMPLETED and instance.attached_report_pdf:
        recipients = [instance.patient.user.email]
        if instance.ordering_doctor:
            recipients.append(instance.ordering_doctor.user.email)

        send_mail(
            subject=f"[LabCare] Diagnostic Report Available: Order #{str(instance.id)[:8]}",
            message=(
                f"Your official diagnostic PDF report is authorized and ready for download.\n"
                f"Login to your dashboard to inspect your results."
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[e for e in recipients if e],
            fail_silently=True
        )