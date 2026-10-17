import { Doctor } from '../../features/appointment-booking/api';

export function filterDoctors(doctors: Doctor[], search: string): Doctor[] {
  const query = search.trim().toLocaleLowerCase();
  if (!query) return doctors;

  return doctors.filter((doctor) => {
    const relatedInfo = [
      doctor.title,
      doctor.professional_role,
      ...(doctor.specialties || []).map((specialty) => specialty.name),
      ...(doctor.services || []).map((service) => service.name),
      ...(doctor.facilities || []).flatMap(({ department, room, facility }) => [
        department,
        room,
        facility?.name,
        facility?.code,
      ]),
    ].filter(Boolean).join(' ');
    return `${doctor.full_name} ${doctor.code} ${relatedInfo}`.toLocaleLowerCase().includes(query);
  });
}
