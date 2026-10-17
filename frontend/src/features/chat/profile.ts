export interface ChatProfile {
  name: string;
  phone: string;
  date_of_birth?: string;
  gender?: string;
}

export const GUEST_PROFILE_KEY = 'p124_chat_guest_profile';
export const GUEST_PROFILE_EVENT = 'p124:guest-profile';

export function normalizeChatProfile(
  name: string,
  phone: string,
  dob?: string,
  gender?: string
): ChatProfile | null {
  const cleanName = name.trim().replace(/\s+/g, ' ');
  const cleanPhone = phone.trim().replace(/[\s().-]/g, '');
  if (cleanName.length < 2 || cleanName.length > 120 || !/^[+]?\d{9,15}$/.test(cleanPhone)) return null;
  return {
    name: cleanName,
    phone: cleanPhone,
    date_of_birth: dob?.trim() || undefined,
    gender: gender?.trim() || undefined,
  };
}

export function readGuestProfile(): ChatProfile | null {
  try {
    const profile = JSON.parse(sessionStorage.getItem(GUEST_PROFILE_KEY) || 'null');
    return profile && typeof profile.name === 'string' && typeof profile.phone === 'string'
      ? normalizeChatProfile(profile.name, profile.phone) : null;
  } catch {
    return null;
  }
}

export function saveGuestProfile(profile: ChatProfile | null): void {
  if (profile) sessionStorage.setItem(GUEST_PROFILE_KEY, JSON.stringify(profile));
  else sessionStorage.removeItem(GUEST_PROFILE_KEY);
  window.dispatchEvent(new Event(GUEST_PROFILE_EVENT));
}
