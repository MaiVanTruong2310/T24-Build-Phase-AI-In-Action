import { Doctor } from '../../features/appointment-booking/api';

export function filterDoctors(doctors: Doctor[], search: string): Doctor[] {
  const query = search.trim().toLocaleLowerCase();
  if (!query) return doctors;

  return doctors.filter((doctor) => {
    const facilityInfo = (doctor.facilities || []).flatMap(({ department, room, facility }) => [
      department,
      room,
      facility?.name,
      facility?.code,
    ]).filter(Boolean).join(' ');
    return `${doctor.full_name} ${doctor.code} ${facilityInfo}`.toLocaleLowerCase().includes(query);
  });
}
