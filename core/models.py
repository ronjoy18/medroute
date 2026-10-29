import uuid
from decimal import Decimal
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator
from datetime import date
from django.db.models import SET_NULL
from phonenumber_field.modelfields import PhoneNumberField

class User(AbstractUser):
    class Role(models.TextChoices):
        DOCTOR = "DOCTOR", _("Doctor")
        PATIENT = "PATIENT", _("Patient")
        CAREGIVER = "CAREGIVER",_("Caregiver")
        STAFF = "STAFF", _("Lab Technician / Staff")
        ADMIN = "ADMIN", _("Super Administrator")
        
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.PATIENT)
    phone_number = PhoneNumberField(unique=False, region= "KE", help_text="country code and phone number")
    is_verified = models.BooleanField(default=False)

    def is_doctor(self):
        return self.role == self.Role.DOCTOR

    def is_patient(self):
        return self.role == self.Role.PATIENT

    def is_internal(self):
        return self.role in [self.Role.STAFF, self.Role.ADMIN]
    
    def is_caregiver(self):
        return self.role == self.Role.CAREGIVER

class DoctorProfile(models.Model):
    user = models.OneToOneField("core.User", on_delete=models.CASCADE, related_name="doctor_profile")
    license_number = models.CharField(max_length=64, unique=True)
    specialty = models.CharField(max_length=128, blank=True)
    hospital_affiliation = models.CharField(max_length=256, blank=True)
    commission_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("10.00"))
    total_accrued_bonus = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    # --- New Global Doctor Directory Fields ---
    profile_picture = models.ImageField(upload_to="doctors/avatars/", null=True, blank=True)
    country_name = models.CharField(max_length=100, default="Kenya")
    country_iso = models.CharField(max_length=2, default="KE", help_text=_("2-letter ISO code, e.g., US, IN, DE, KE for flags"))
    bio = models.TextField(blank=True, help_text=_("Comprehensive medical biography and background."))
    achievements = models.TextField(blank=True, help_text=_("Key clinical achievements, certifications, surgery track record."))
    years_of_experience = models.PositiveIntegerField(default=1)
    
    # Administrative verification & scoring
    is_verified_global = models.BooleanField(
        default=False, 
        help_text=_("Designates whether this doctor has passed identity & license verification.")
    )
    star_rating = models.DecimalField(
        max_digits=2, decimal_places=1, default=Decimal("5.0"),
        validators=[MinValueValidator(Decimal("1.0")), MaxValueValidator(Decimal("5.0"))],
        help_text=_("specialization rating score from 1.0 to 5.0 stars.")
    )
    admin_verification_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Dr. {self.user.get_full_name() or self.user.username} - {self.specialty} ({self.country_name})"

class CareGiverProfile(models.Model):
    
    user = models.OneToOneField("core.User", on_delete=SET_NULL, related_name="caregiver_profile", null= True)
    medical_report = models.CharField(max_length=256, blank=True, null=True,)
    behavior= models.CharField(max_length=256, null=True, blank=True)
    remarks = models.CharField(max_length=256, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    archived_by_caregiver =models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_verified = models.BooleanField(default=False)
    
    
class PatientProfile(models.Model):
    class PatientType(models.TextChoices):
        INDEPENDENT = "INDEPENDENT", _("Independent patient")
        DOCTOR_REFERRED = "DOCTOR_REFERRED", _("Doctor-Referred Patient")
        CAREGIVER_REFERRED = "CAREGIVER_REFERRED",_("Caregiver-Managed Patient ")
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField("core.User", on_delete=models.CASCADE, related_name="patient_profile")
    patient_type = models.CharField(
        max_length=20, choices=PatientType.choices, default=PatientType.INDEPENDENT
    )
    primary_doctor = models.ForeignKey(
        DoctorProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name="managed_patients"
    )
    
    archived_by_caregiver = models.BooleanField(default = False)
    caregiver = models.ForeignKey(
        CareGiverProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name="served_patients"
    )

    pending_caregiver_email= models.EmailField(blank=True, unique= False)
    pending_caregiver_name =models.CharField(max_length=128, blank=True)
    pending_doctor_name = models.CharField(max_length=128, blank=True)
    pending_doctor_email = models.EmailField(blank=True, unique= False)
    date_of_birth = models.DateField(null=True, blank=True)
    emergency_contact = models.CharField(max_length=128, blank=True)
    
    # Referral & Promo Fields for Independent patientts
    referral_code = models.CharField(max_length=32, unique=True, blank=True)
    referred_by = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True, related_name="referrals"
    )
    promo_credits = models.DecimalField(
        max_digits=8, decimal_places=2, default=Decimal("0.00"),
        help_text=_("Earned discount credit balance applied to future orders.")
    )
    
    # Soft archive for doctor management
    is_archived_by_doctor = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    phone = PhoneNumberField(unique=False, region= "KE", help_text="country code and phone number")
    def save(self, *args, **kwargs):
        if not self.referral_code:
            self.referral_code = f"PAT-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)

    @property
    def phone_number(self):
        return self.user.phone_number    

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} ({self.patient_type})"

class ServiceCategory(models.Model):
    class CategoryType(models.TextChoices):
        LAB_TEST = "LAB_TEST", _("Laboratory Diagnostic Service")
        COMPANIONSHIP = "COMPANIONSHIP", _("Medical Companionship Procedure")

    name = models.CharField(max_length=128)
    category_type = models.CharField(max_length=32, choices=CategoryType.choices)
    description = models.TextField(blank=True)

    class Meta:
        verbose_name_plural = "Service Categories"

    def __str__(self):
        return f"{self.name} [{self.get_category_type_display()}]"


class LabService(models.Model):
    category = models.ForeignKey(ServiceCategory, on_delete=models.PROTECT, related_name="services")
    name = models.CharField(max_length=256)
    code = models.CharField(max_length=32, unique=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    turnaround_time_hours = models.PositiveIntegerField(default=24)
    preparation_instructions = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.code}) - Ksh{self.price}"


def report_upload_directory_path(instance, filename):
    return f"diagnostic_reports/order_{instance.id}/{uuid.uuid4()}_{filename}"


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", _("Pending Intake")
        SAMPLE_COLLECTED = "SAMPLE_COLLECTED", _("Sample Collected")
        IN_ANALYSIS = "IN_ANALYSIS", _("In Laboratory Analysis")
        COMPLETED = "COMPLETED", _("Completed & Finalized")
        CANCELLED = "CANCELLED", _("Cancelled")

    class OrderType(models.TextChoices):
        LAB_TEST = "LAB_TEST", _("Laboratory Diagnostic")
        COMPANIONSHIP = "COMPANIONSHIP", _("Medical Companionship / Procedure Support")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order_type = models.CharField(max_length=32, choices=OrderType.choices, default=OrderType.LAB_TEST)
    patient = models.ForeignKey(PatientProfile, on_delete=models.PROTECT, related_name="orders")
    ordering_doctor = models.ForeignKey(
        DoctorProfile, on_delete=models.SET_NULL, related_name="dispatched_orders", null=True
    )
    caregiver = models.ForeignKey(CareGiverProfile, on_delete=models.PROTECT,null=True, blank=True, related_name='assigned_caregiver')
    services = models.ManyToManyField(LabService, blank=True, related_name="orders")
    custom_test_names = models.TextField(
        blank=True, 
        help_text=_("Freeform list of unlisted tests or bespoke companionship procedures requested.")
    )
    booking_start= models.DateTimeField(auto_now_add=True)
    booking_end=models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=32, choices=Status.choices, default=Status.PENDING)
    total_cost = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    is_paid = models.BooleanField(default=False)
    clinical_notes = models.TextField(blank=True)
    attached_report_pdf = models.FileField(upload_to=report_upload_directory_path, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    mpesa_checkout_id = models.CharField(max_length=128, blank=True, null=True, db_index=True)
    payment_reference = models.CharField(max_length=64, blank=True, null=True) # E.g., QKH890LKJ3

    def calculate_cost(self):
        return sum(service.price for service in self.services.all())

    def __str__(self):
        return f"Order {self.id} - {self.patient.user.username} - {self.status}"


class ReferralLedger(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    doctor = models.ForeignKey(DoctorProfile, on_delete=models.PROTECT, related_name="referral_records")
    order = models.OneToOneField(Order, on_delete=models.PROTECT, related_name="referral_ledger_entry")
    patient_identifier_snapshot = models.CharField(
        max_length=256,
        help_text=_("Immutable audit string capturing patient identity at billing time.")
    )
    order_amount_snapshot = models.DecimalField(max_digits=10, decimal_places=2)
    allocated_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    bonus_amount = models.DecimalField(max_digits=10, decimal_places=2)
    accrued_timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Referral Bonus Ledger"
        ordering = ["-accrued_timestamp"]

    def __str__(self):
        return f"LedgerEntry: Dr. {self.doctor.license_number} | +Ksh{self.bonus_amount} (Order: {self.order_id})"


class GlobalDoctorInquiry(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", _("Connection Pending , Waiting for Communication")
        CONNECTED = "CONNECTED", _("Connected ")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    doctor = models.ForeignKey(DoctorProfile, on_delete=models.CASCADE, related_name="patient_inquiries")
    patient = models.ForeignKey(PatientProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name="global_inquiries")
    patient_full_name = models.CharField(max_length=150)
    patient_phone = PhoneNumberField(unique=False, region= "KE", help_text="country code and phone number")
    patient_email = models.EmailField()
    clinical_concern = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.patient_full_name} ({self.patient_phone}) -> Dr. {self.doctor.user.last_name} [{self.get_status_display()}]"



class CompanionshipScheduler(models.Model):
    class Status(models.TextChoices):
        SCHEDULED="SCHEDULED",_('schedued')
        FREE="FREE",_('free')

    services=models.ForeignKey(LabService,on_delete=models.PROTECT,related_name = 'lab_services', null=True)
    patient = models.ForeignKey(PatientProfile,on_delete=models.CASCADE,related_name ='patient_in_care', )
    caregiver=models.ForeignKey(CareGiverProfile,on_delete=models.PROTECT,related_name ='patient_manager')
    order= models.ForeignKey(Order,on_delete=models.CASCADE,related_name ='offred_requests' )
    status = models.CharField(max_length=256, choices =Status.choices, default=Status.SCHEDULED)
    start_date=models.DateTimeField()
    end_date=models.DateTimeField()
    class Meta:
        indexes=[
            models.Index(fields=["caregiver", "start_date", "end_date"])
        ]

class CareRequest(models.Model):
    class RequestStatus(models.TextChoices):
        PENDING = "PENDING", "Pending Follow-up"
        CONTACTED = "CONTACTED", "Client Contacted"
        COMPLETED = "COMPLETED", "Converted to Order"
        CANCELLED = "CANCELLED", "Cancelled"

    patient = models.ForeignKey(
        PatientProfile,
        on_delete=models.CASCADE,
        related_name="care_requests"
    )
    service = models.ForeignKey(
        LabService,
        on_delete=models.PROTECT,
        related_name="care_requests"
    )
    order = models.ForeignKey(
        Order,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="care_requests"
    )
    patient_name = models.CharField(max_length=256)
    patient_phone = PhoneNumberField(unique=False, region= "KE", help_text="country code and phone number")
    patient_email = models.EmailField(max_length=256, blank=True, null=True)
    notes = models.TextField(blank=True, default="")
    status = models.CharField(
        max_length=20,
        choices=RequestStatus.choices,
        default=RequestStatus.PENDING
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.patient_name} - {self.service.name} ({self.status})"