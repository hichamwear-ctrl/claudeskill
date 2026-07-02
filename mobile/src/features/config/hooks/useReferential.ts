import { useQuery } from '@tanstack/react-query';
import { useEffect } from 'react';

import { qk } from '@/constants/queryKeys';
import i18n from '@/services/i18n';

import { fetchAppConfig, fetchCatalogue, fetchContentStrings } from '../api/config';

const REFERENTIAL_STALE = 1000 * 60 * 60; // 1 h : le référentiel change rarement

/** Configuration publique (`app_config`) — mise en cache + persistée. */
export function useAppConfig() {
  return useQuery({ queryKey: qk.config.appConfig(), queryFn: fetchAppConfig, staleTime: REFERENTIAL_STALE });
}

/** Catalogue des catégories actives. */
export function useCatalogue() {
  return useQuery({ queryKey: qk.config.catalogue(), queryFn: fetchCatalogue, staleTime: REFERENTIAL_STALE });
}

/**
 * Textes data-driven : chargés puis fusionnés dans i18next sous le namespace
 * `db` (couche 2). Rend `t('db:<clé>')` disponible ; aucun texte métier en dur.
 */
export function useContentStrings(locale = 'fr') {
  const query = useQuery({
    queryKey: qk.config.contentStrings(locale),
    queryFn: () => fetchContentStrings(locale),
    staleTime: REFERENTIAL_STALE,
  });

  useEffect(() => {
    if (query.data) i18n.addResourceBundle(locale, 'db', query.data, true, true);
  }, [query.data, locale]);

  return query;
}
