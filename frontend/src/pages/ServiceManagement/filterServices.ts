import { Service } from './api';
import { ServiceFilters } from './FilterBar';

export function filterServices(services: Service[], filters: ServiceFilters): Service[] {
  const query = filters.search.trim().toLocaleLowerCase();

  return services.filter((service) => {
    if (query && !`${service.name} ${service.code}`.toLocaleLowerCase().includes(query)) return false;
    if (filters.category && service.category !== filters.category) return false;
    if (filters.status && service.status !== filters.status) return false;
    if (filters.priceRange) {
      if (service.price == null) return false;
      if (filters.priceRange === 'under-1m' && service.price >= 1_000_000) return false;
      if (filters.priceRange === '1m-3m' && (service.price < 1_000_000 || service.price > 3_000_000)) return false;
      if (filters.priceRange === 'over-3m' && service.price <= 3_000_000) return false;
    }
    return true;
  });
}
