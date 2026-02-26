/**
 * Types for Site and Team (multi-site supervisor scoping).
 * Mirrors backend schemas.site.SiteResponse and TeamResponse.
 */

export interface Site {
  id: string;
  name: string;
  location: string | null;
  created_at: string;
  teams: Team[];
}

export interface Team {
  id: string;
  site_id: string;
  name: string;
  created_at: string;
}
