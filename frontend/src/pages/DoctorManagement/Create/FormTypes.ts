export interface DoctorForm {
  fullName: string;
  academicTitle: string;
  gender: string;
  dateOfBirth: string;
  idNumber: string;
  phone: string;
  email: string;
  licenseNumber: string;
  licenseIssueDate: string;
  licenseIssuer: string;
  practiceScope: string;
  experienceYears: string;
  facility: string;
  specialty: string;
  position: string;
  defaultRoom: string;
  permissionLevel: 'level1' | 'level2' | 'level3';
  standardPrice: string;
  vipPrice: string;
  allowOnlineBooking: boolean;
  enableEmergencyCode: boolean;
}

export type FieldErrors = Partial<Record<keyof DoctorForm, string>>;
