import type { ReactNode } from 'react';

import { HealthScreen } from '@/features/health';

/** Route de diagnostic backend (accessible via app://health). */
export default function HealthRoute(): ReactNode {
  return <HealthScreen />;
}
