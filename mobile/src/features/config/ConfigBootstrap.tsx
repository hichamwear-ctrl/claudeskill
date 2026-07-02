import type { ReactNode } from 'react';

import { useAppConfig, useCatalogue, useContentStrings } from './hooks/useReferential';

/**
 * Précharge le référentiel data-driven (app_config, catalogue, content_strings)
 * dès l'entrée dans une zone authentifiée. Ne rend rien : les données vivent
 * dans le cache React Query (persisté → disponibles hors-ligne).
 */
export function ConfigBootstrap(): ReactNode {
  useAppConfig();
  useCatalogue();
  useContentStrings('fr');
  return null;
}
