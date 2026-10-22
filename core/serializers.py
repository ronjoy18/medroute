from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from .models import (
    User,
    DoctorProfile,
    PatientProfile,
    LabService,
    ServiceCategory,
    Order,
    ReferralLedger,
    CareGiverProfile,
    CompanionshipScheduler,

    
    CareRequest
)


class ServiceCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceCategory
        fields = ["id", "name", "category_type", "description"]


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password_confirmation = serializers.CharField(write_only=True, required=True)
    license_number = serializers.CharField(write_only=True, required=False, allow_blank=True)
    referring_doctor_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)
    pending_doctor_name = serializers.CharField(write_only=True, required=False, allow_blank=True)
    pending_caregiver_email = serializers.EmailField(write_only=True, required=False, allow_blank=True)
    referral_code = serializers.CharField(write_only=True, required=False, allow_blank=True)
    pending_caregiver_name = serializers.CharField(write_only = True, required= False, allow_blank = True)
    pending_doctor_email = serializers.CharField(write_only = True, required= False, allow_blank = True)
    caregiver_id =serializers.UUIDField(write_only=True, required=False, allow_null=True)
    
    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "role",
            "phone_number",
            "password",
            "password_confirmation",
            "license_number",
            "referring_doctor_id",
            "pending_doctor_name",
            "pending_doctor_email",
            "referral_code",
            "pending_caregiver_email",
            "pending_caregiver_name",
            "caregiver_id"
        ]

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirmation"]:
            raise serializers.ValidationError(
                {"password_confirmation": "Password criteria check passed, but passwords do not match."}
            )

        role = attrs.get("role")
        if role == User.Role.DOCTOR and not attrs.get("license_number"):
            raise serializers.ValidationError(
                {"license_number": "A valid medical license designation is required for doctor accounts."}
            )

        if role in [User.Role.STAFF, User.Role.ADMIN]:
            raise serializers.ValidationError(
                {"role": "Privileged credentials cannot be provisioned via public endpoints."}
            )

        return attrs

    def create(self, validated_data):
        license_number = validated_data.pop("license_number", None)
        referring_doctor_id = validated_data.pop("referring_doctor_id", None)
        pending_doc_name = validated_data.pop("pending_doctor_name", "")
        pending_care_email = validated_data.pop("pending_caregiver_email", "")
        pending_doc_email = validated_data.pop("pending_doctor_email", "")
        pending_care_name = validated_data.pop("pending_caregiver_name", "")
        caregiver_id= validated_data.pop("caregiver_id", "")
        ref_code = validated_data.pop("referral_code", "").strip()
        validated_data.pop("password_confirmation")

        # Resolve patient referral link if provided
        referred_by_patient = None
        if ref_code:
            referred_by_patient = PatientProfile.objects.filter(referral_code=ref_code).first()

        user = User.objects.create_user(**validated_data)

        if user.role == User.Role.DOCTOR:
            DoctorProfile.objects.create(user=user, license_number=license_number)
        elif user.role == User.Role.PATIENT:
            patient_type = PatientProfile.PatientType.INDEPENDENT
            primary_doc = None

            if referring_doctor_id:
                try:
                    primary_doc = DoctorProfile.objects.get(id=referring_doctor_id)
                    patient_type = PatientProfile.PatientType.DOCTOR_REFERRED
                except DoctorProfile.DoesNotExist:
                    pass
            elif pending_doc_email:
                patient_type = PatientProfile.PatientType.DOCTOR_REFERRED
            elif caregiver_id:
                try:
                    care_g= CareGiverProfile.objects.get(id = caregiver_id)
                    patient_type = PatientProfile.PatientType.CAREGIVER_REFERRED
                except DoctorProfile.DoesNotExist:
                    pass


            PatientProfile.objects.create(
                user=user,
                patient_type=patient_type,
                primary_doctor=primary_doc,
                pending_doctor_name=pending_doc_name,
                pending_doctor_email=pending_doc_email,
                referred_by=referred_by_patient,  # Successfully linked to referrer
                pending_caregiver_name=pending_care_name,
                pending_caregiver_email=pending_care_email,
            )

        return user


class LabServiceSerializer(serializers.ModelSerializer):
    category = ServiceCategorySerializer(read_only=True)
    category_type = serializers.CharField(source="category.category_type", read_only=True)

    class Meta:
        model = LabService
        fields = [
            "id",
            "name",
            "code",
            "category",
            "category_type",
            "price",
            "turnaround_time_hours",
            "preparation_instructions",
            "is_active",
        ]


class OrderSerializer(serializers.ModelSerializer):
    services_detail = LabServiceSerializer(source="services", many=True, read_only=True)
    patient_name = serializers.CharField(source="patient.user.get_full_name", read_only=True)
    doctor_name = serializers.CharField(source="ordering_doctor.user.get_full_name", read_only=True)

    class Meta:
        model = Order
        fields = [
            "id",
            "order_type",
            "patient",
            "patient_name",
            "ordering_doctor",
            "doctor_name",
            "services",
            "services_detail",
            "custom_test_names",
            "status",
            "total_cost",
            "is_paid",
            "clinical_notes",
            "attached_report_pdf",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "status",
            "total_cost",
            "is_paid",
            "attached_report_pdf",
            "created_at",
            "updated_at",
        ]


class DoctorOnboardPatientSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150, required=True)
    email = serializers.EmailField(required=True)
    first_name = serializers.CharField(max_length=150, required=True)
    last_name = serializers.CharField(max_length=150, required=True)
    phone_number = serializers.CharField(max_length=20, required=True)
    date_of_birth = serializers.DateField(
        required=True,
        error_messages={
            "required": "Date of birth is required.",
            "invalid": "Please provide a valid date in YYYY-MM-DD format.",
        },
    )
    emergency_contact = serializers.CharField(max_length=128, required=False, allow_blank=True)
    initial_service_ids = serializers.ListField(
        child=serializers.IntegerField(), required=False, default=[]
    )


class ReferralLedgerSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReferralLedger
        fields = [
            "id",
            "patient_identifier_snapshot",
            "order_amount_snapshot",
            "allocated_percentage",
            "bonus_amount",
            "accrued_timestamp",
        ]

class CareGiverprofileSerializer(serializers.Serializer):
    
    username = serializers.CharField(max_length=150, required=True)
    email = serializers.EmailField(required=True)
    first_name = serializers.CharField(max_length=150, required=True)
    last_name = serializers.CharField(max_length=150, required=True)
    phone_number = serializers.CharField(max_length=20, required=True)
    
    date_of_birth = serializers.DateField(
        required=True,
        error_messages={
            "required": "Date of birth is required.",
            "invalid": "Please provide a valid date in YYYY-MM-DD format.",
            },
        )
    emergency_contact = serializers.CharField(max_length=128, required=False, allow_blank=True)
    initial_service_ids = serializers.ListField(
            child=serializers.IntegerField(), required=False, default=[]
        ) 

    #class Meta:
        #models = CareGiverProfile
        #fields =[
            #"id",
            #"user",
            #"medical_report",
            #"behavior",
            #"remarks",
        #]
        #read_only_fields =[
            #"createde_at",
        #]

class CompanionshipSchedulerSerializer(serializers.ModelSerializer):
    caregiver_name = serializers.SerializerMethodField()
    patient_name = serializers.SerializerMethodField()
    service_name = serializers.CharField(source="services.name", read_only=True)

    class Meta:
        model = CompanionshipScheduler
        fields = [
            "id", "order", "patient", "patient_name", "caregiver",
            "caregiver_name", "services", "service_name",
            "start_date", "end_date", "status",
        ]

    def get_caregiver_name(self, obj):
        if obj.caregiver and obj.caregiver.user:
            return obj.caregiver.user.get_full_name() or obj.caregiver.user.username
        return "Unassigned"

    def get_patient_name(self, obj):
        if obj.patient and obj.patient.user:
            return obj.patient.user.get_full_name() or obj.patient.user.username
        return "N/A"        

class CareRequestSerializer(serializers.ModelSerializer):
    service_name = serializers.CharField(source="service.name", read_only=True)
    price = serializers.DecimalField(source="service.price", max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = CareRequest
        fields = [
            "id",
            "service",
            "service_name",
            "price",
            "patient_name",
            "patient_phone",
            "patient_email",
            "status",
            "created_at",
        ]
        read_only_fields = ["patient_name", "patient_phone", "patient_email", "status"]