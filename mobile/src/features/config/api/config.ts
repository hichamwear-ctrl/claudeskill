import { unwrap } from '@/services/api';
import { supabase } from '@/services/supabase/client';
import type { Json } from '@/types/database.types';
import type { ServiceCategory } from '@/types/domain';

/** Clés `app_config` publiques (scope=public) → dictionnaire. */
export async function fetchAppConfig(): Promise<Record<string, Json>> {
  const rows = await unwrap<{ key: string; value: Json }[]>(
    supabase.from('app_config').select('key,value').eq('scope', 'public').eq('is_active', true),
  );
  return Object.fromEntries(rows.map((r) => [r.key, r.value]));
}

/** Catalogue actif (référentiel) trié pour affichage / résolution slug→id. */
export async function fetchCatalogue(): Promise<ServiceCategory[]> {
  return unwrap<ServiceCategory[]>(
    supabase.from('service_categories').select('*').eq('is_active', true).order('sort_order'),
  );
}

/** Textes pilotés par la donnée (content_strings) pour une locale → dictionnaire. */
export async function fetchContentStrings(locale: string): Promise<Record<string, string>> {
  const rows = await unwrap<{ key: string; value: string }[]>(
    supabase.from('content_strings').select('key,value').eq('locale', locale).eq('is_active', true),
  );
  return Object.fromEntries(rows.map((r) => [r.key, r.value]));
}
