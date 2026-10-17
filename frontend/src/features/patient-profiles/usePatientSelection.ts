import { useEffect, useState } from 'react';
import { useSelector } from 'react-redux';
import type { RootState } from '../../app/store';
import { fetchPatientProfiles, type PatientProfile } from './api';

export interface PatientSelection {
  profileId: string;
  profiles: PatientProfile[];
  selectedProfile: PatientProfile | undefined;
  loading: boolean;
  error: string;
  choose: (profileId: string) => void;
}

export function usePatientSelection(): PatientSelection {
  const user = useSelector((state: RootState) => state.auth.user);
  const [profileId, setProfileId] = useState('');
  const [profiles, setProfiles] = useState<PatientProfile[]>([]);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let active = true;
    setProfileId('');
    setProfiles([]);
    setError('');
    if (user?.role !== 'patient') return;

    setLoading(true);
    fetchPatientProfiles()
      .then((items) => {
        if (active) setProfiles(items);
      })
      .catch((cause: unknown) => {
        if (active) setError(cause instanceof Error ? cause.message : 'Không thể tải hồ sơ người khám.');
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [user?.id, user?.role]);

  return {
    profileId,
    profiles,
    selectedProfile: profiles.find((profile) => profile.id === profileId),
    loading,
    error,
    choose: setProfileId,
  };
}
