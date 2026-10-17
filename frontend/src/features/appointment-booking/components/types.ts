import React from 'react';

export type Facility = { id: string; name: string; address: string; image?: string };
export type Specialty = { id: string; name: string; desc: string; icon: React.ElementType };
export type Doctor = { id: string; name: string; title: string; avatar: string; rating: number; specialtyId: string; facilityId: string };
export type TimeSlot = { id: string; time: string; status: 'available' | 'booked' | 'selected'; date: string };
