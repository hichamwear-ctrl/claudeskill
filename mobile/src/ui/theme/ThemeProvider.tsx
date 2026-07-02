import { createContext, useContext, type ReactNode } from 'react';

import { lightTheme, type Theme } from './theme';

const ThemeContext = createContext<Theme>(lightTheme);

/**
 * Fournit le thème à l'arbre. V1 = thème clair fixe ; le passage au dark mode
 * se fera ici (lecture `useColorScheme`) sans changer les composants.
 */
export function ThemeProvider({ children }: { children: ReactNode }): ReactNode {
  return <ThemeContext.Provider value={lightTheme}>{children}</ThemeContext.Provider>;
}

/** Accès au thème courant depuis n'importe quel composant. */
export function useTheme(): Theme {
  return useContext(ThemeContext);
}
