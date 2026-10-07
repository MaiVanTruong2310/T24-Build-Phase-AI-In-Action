import { Navigate } from 'react-router-dom';

/**
 * FamilyProfiles route component.
 *
 * Feature has been unified into 'Hồ sơ bệnh án' (/patient/profile#family)
 * where patient profiles & relative profiles are centrally managed.
 */
export default function FamilyProfiles() {
  return <Navigate to="/patient/profile#family" replace />;
}
