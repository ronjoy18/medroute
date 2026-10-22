from decimal import Decimal
from django.contrib import admin
from django.core.mail import send_mail
from django.conf import settings
from .models import (
    User,
    DoctorProfile,
    PatientProfile,
    ServiceCategory,
    LabService,
    Order,
    ReferralLedger,
    GlobalDoctorInquiry,
    CareGiverProfile,
    CareRequest
)


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ["username", "email", "role", "is_staff", "is_active", "date_joined"]
    list_filter = ["role", "is_staff", "is_active"]
    search_fields = ["username", "email", "first_name", "last_name", "phone_number"]


@admin.register(DoctorProfile)
class DoctorProfileAdmin(admin.ModelAdmin):
    list_display = [
        "user_name",
        "specialty",
        "country_name",
        "star_rating",
        "is_verified_global",
        "total_accrued_bonus",
        "created_at",
    ]
    list_filter = ["is_verified_global", "country_name", "specialty", "star_rating"]
    search_fields = [
        "user__username",
        "user__first_name",
        "user__last_name",
        "user__email",
        "license_number",
        "specialty",
        "country_name",
        "hospital_affiliation",
    ]
    actions = ["verify_doctors_and_notify"]

    def user_name(self, obj):
        return obj.user.get_full_name() or obj.user.username
    user_name.short_description = "Doctor Name"

    @admin.action(description="Verify selected doctors and send confirmation email")
    def verify_doctors_and_notify(self, request, queryset):
        for doc in queryset:
            doc.is_verified_global = True
            doc.save(update_fields=["is_verified_global"])
            send_mail(
                subject="[LabCare Global] Your Medical Practice Profile Has Been Verified!",
                message=(
                    f"Dear Dr. {doc.user.last_name},\n\n"
                    f"Our administrative review team has verified your credentials and license.\n"
                    f"Your profile is now live on our Global Specialist Directory.\n\n"
                    f"LabCare Global Review Board"
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[doc.user.email],
                fail_silently=True,
            )
        self.message_user(request, f"{queryset.count()} doctors verified and notified.")


@admin.register(PatientProfile)
class PatientProfileAdmin(admin.ModelAdmin):
    list_display = ["user", "patient_type", "primary_doctor", "promo_credits", "created_at"]
    list_filter = ["patient_type", "is_archived_by_doctor", "archived_by_caregiver", "caregiver"]
    search_fields = ["user__username", "user__first_name", "user__last_name", "user__email", "referral_code"]


@admin.register(ServiceCategory)
class ServiceCategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "category_type", "description"]
    list_filter = ["category_type"]


@admin.register(LabService)
class LabServiceAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "category", "price", "turnaround_time_hours", "is_active"]
    list_filter = ["is_active", "category__category_type"]
    search_fields = ["name", "code"]


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ["id", "patient", "ordering_doctor", "order_type", "status", "total_cost", "is_paid", "created_at"]
    list_filter = ["status", "is_paid", "order_type"]
    search_fields = ["id", "patient__user__username", "ordering_doctor__user__username", "custom_test_names"]


@admin.register(ReferralLedger)
class ReferralLedgerAdmin(admin.ModelAdmin):
    list_display = ["doctor", "patient_identifier_snapshot", "bonus_amount", "allocated_percentage", "accrued_timestamp"]
    search_fields = ["doctor__user__username", "patient_identifier_snapshot"]




@admin.register(GlobalDoctorInquiry)
class GlobalDoctorInquiryAdmin(admin.ModelAdmin):
    list_display = ["patient_full_name", "patient_phone", "patient_email", "doctor", "status", "created_at"]
    list_filter = ["status", "doctor__country_name"]
    search_fields = ["patient_full_name", "patient_phone", "patient_email", "doctor__user__last_name"]
    actions = ["mark_as_connected"]

    @admin.action(description="Mark selected inquiries as Connected (Communication completed)")
    def mark_as_connected(self, request, queryset):
        count = queryset.update(status="CONNECTED")
        self.message_user(request, f"{count} global connection(s) marked as Connected.")

@admin.register(CareGiverProfile)
class CareGiverProfileAdmin(admin.ModelAdmin):
    list_display = ["user","created_at"]
    list_filter=["is_verified", "is_active"]
    search_fields = ["use__username"]

    actions = ["verify_caregiver_and_notify"]
    
    def user_name(self, obj):
        return obj.user.get_full_name() or obj.user.username
    user_name.short_description = "caregiver Name"
    
    @admin.action(description="Verify selected caregivers and send confirmation email")
    def verify_caregivers_and_notify(self, request, queryset):
            for cg in queryset:
                cg.is_verified = True
                
                send_mail(
                    subject="[LabCare Global] Your Medical Practice Profile Has Been Verified!",
                    message=(
                        f"Dear Dr. {cg.user.last_name},\n\n"
                        f"Our administrative review team has verified your credentials and license.\n"
                        f"Your profile is now live on our Global Specialist Directory.\n\n"
                        f"LabCare Global Review Board"
                    ),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[cg.user.email],
                    fail_silently=True,
                )
            self.message_user(request, f"{queryset.count()} caregivers verified and notified.")

@admin.register(CareRequest)
class CareRequestAdmin(admin.ModelAdmin):  
    list_display = ["patient_full_name", "patient_phone", "patient_email", "status", "created_at","patient"]
    list_filter = ["status"]
    search_fields = ["patient_full_name", "patient_phone", "patient_email"]


    