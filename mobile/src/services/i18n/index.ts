import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';

import fr from '../../../locales/fr.json';

/**
 * i18n — COUCHE 1 (shell de l'app) : libellés de navigation, actions, erreurs.
 * La COUCHE 2 (contenu piloté par la donnée : catalogue, questions,
 * notifications) sera fusionnée depuis `content_strings` au module M5.
 * Locale par défaut : `fr` (source : `profiles.locale`).
 */
export const defaultNS = 'translation';

// eslint-disable-next-line import/no-named-as-default-member
void i18n.use(initReactI18next).init({
  resources: { fr: { translation: fr } },
  lng: 'fr',
  fallbackLng: 'fr',
  defaultNS,
  interpolation: { escapeValue: false },
  returnNull: false,
  compatibilityJSON: 'v4',
});

export default i18n;
