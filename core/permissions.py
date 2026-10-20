from rest_framework import permissions


class IsInternalStaff(permissions.BasePermission):
    """Permits access strictly to Lab Staff or Super Administrators."""
    def has_permission(self, request, view):
        return bool(
            request.user and 
            request.user.is_authenticated and 
            (request.user.is_staff or request.user.role in [request.user.Role.STAFF, request.user.Role.ADMIN])
        )


class IsDoctorOwner(permissions.BasePermission):
    """Ensures Doctors only see their own profile, ledger, and assigned patients."""
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_doctor())

    def has_object_permission(self, request, view, obj):
        if hasattr(obj, "doctor_profile"):
            return obj.doctor_profile.user == request.user
        if hasattr(obj, "primary_doctor") and obj.primary_doctor:
            return obj.primary_doctor.user == request.user
        if hasattr(obj, "ordering_doctor") and obj.ordering_doctor:
            return obj.ordering_doctor.user == request.user
        return False

class IsCareGiverOwner(permissions.BasePermission):
    """Allows only care givers to access the page"""
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_caregiver())

    def has_object_permission(self, request, view, obj):
        if hasattr(obj, "caregiver_profile"):
            return obj.caregiver_profile.user == request.user
        if hasattr(obj,"caregiver")and obj.caregiver:
            return obj.caregiver.user == request.user
        return False

class IsPatientOwner(permissions.BasePermission):
    """Ensures Patients only access their own direct records and diagnostic orders."""
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_patient())

    def has_object_permission(self, request, view, obj):
        if hasattr(obj, "patient_profile"):
            return obj.patient_profile.user == request.user
        if hasattr(obj, "patient") and obj.patient:
            return obj.patient.user == request.user
        return False


class DocumentAccessPermission(permissions.BasePermission):
    """
    Object-level check for document downloads:
    Allowed if Staff/Admin, or ordering Doctor, or the owner Patient.
    """
    def has_object_permission(self, request, view, obj):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_internal():
            return True
        if user.is_doctor() and obj.ordering_doctor:
            return obj.ordering_doctor.user == user
        if user.is_patient() and obj.patient:
            return obj.patient.user == user
        return False