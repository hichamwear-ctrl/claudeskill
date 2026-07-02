import type { ReactNode } from 'react';
import { useTranslation } from 'react-i18next';
import { ActivityIndicator, View } from 'react-native';

import { env } from '@/constants/env';
import { toUxError } from '@/lib/errorCatalog';
import { Button, Screen, Text, useTheme } from '@/ui';

import { useHealth } from './hooks/useHealth';

/**
 * Écran de diagnostic (NON métier) : confirme que l'app communique avec le
 * backend via l'Edge Function `health`. Illustre les 4 états (chargement,
 * contenu, erreur, config manquante) et le pipeline callEdge → AppError → UX.
 */
export function HealthScreen(): ReactNode {
  const { t } = useTranslation();
  const theme = useTheme();
  const query = useHealth();

  return (
    <Screen>
      <View style={{ gap: theme.spacing.md, flex: 1 }}>
        <Text variant="title">{t('health.title')}</Text>
        <Text variant="caption" color="textMuted">
          {t('health.subtitle')}
        </Text>

        {!env.isConfigured ? (
          <Card tone="warning">
            <Text variant="heading" color="danger">
              {t('health.notConfigured')}
            </Text>
            <Text color="textMuted">{t('health.notConfiguredHelp')}</Text>
          </Card>
        ) : query.isLoading ? (
          <Card>
            <View style={{ flexDirection: 'row', alignItems: 'center', gap: theme.spacing.sm }}>
              <ActivityIndicator color={theme.colors.primary} />
              <Text color="textMuted">{t('health.checking')}</Text>
            </View>
          </Card>
        ) : query.isError ? (
          <Card tone="error">
            <Text variant="heading" color="danger">
              {t('health.error')}
            </Text>
            <Text color="textMuted">{toUxError(query.error).message}</Text>
          </Card>
        ) : (
          <Card>
            <Text variant="heading" color="success">
              ✓ {t('health.ok')}
            </Text>
            <Row label={t('health.service')} value={query.data?.service ?? '—'} />
            <Row label="status" value={query.data?.status ?? '—'} />
            <Row label={t('health.time')} value={query.data?.time ?? '—'} />
          </Card>
        )}

        <View style={{ flex: 1 }} />
        <Button
          label={t('health.recheck')}
          onPress={() => query.refetch()}
          loading={query.isFetching}
          disabled={!env.isConfigured}
        />
      </View>
    </Screen>
  );
}

function Card({ children, tone }: { children: ReactNode; tone?: 'error' | 'warning' }): ReactNode {
  const theme = useTheme();
  return (
    <View
      style={{
        backgroundColor: tone === 'error' ? theme.colors.dangerSurface : theme.colors.surface,
        borderColor: theme.colors.border,
        borderWidth: 1,
        borderRadius: theme.radius.md,
        padding: theme.spacing.lg,
        gap: theme.spacing.xs,
      }}
    >
      {children}
    </View>
  );
}

function Row({ label, value }: { label: string; value: string }): ReactNode {
  const theme = useTheme();
  return (
    <View style={{ flexDirection: 'row', justifyContent: 'space-between', gap: theme.spacing.md }}>
      <Text color="textMuted">{label}</Text>
      <Text>{value}</Text>
    </View>
  );
}
