import { useState, type ReactNode } from 'react';
import { Pressable, View } from 'react-native';

import { Button, Card, Input, Text, useTheme } from '@/ui';

import type { AnswerValue, PresentedQuestion } from '../types';
import { initialValue, validateAnswer } from '../validation';

export interface DynamicQuestionProps {
  question: PresentedQuestion;
  submitting?: boolean;
  onSubmit: (value: AnswerValue) => void;
}

/** Rend une question et valide la réponse (Zod) avant de la remonter. */
export function DynamicQuestion({ question, submitting, onSubmit }: DynamicQuestionProps): ReactNode {
  const [value, setValue] = useState<AnswerValue>(() => initialValue(question));
  const [error, setError] = useState<string | null>(null);

  const submit = () => {
    const result = validateAnswer(question, value);
    if (!result.ok) {
      setError(result.error ?? 'Valeur invalide');
      return;
    }
    setError(null);
    onSubmit(result.value ?? null);
  };

  return (
    <Card>
      <Text variant="heading">{question.label}</Text>
      {question.help ? (
        <Text variant="caption" color="textMuted">
          {question.help}
        </Text>
      ) : null}

      <Control question={question} value={value} onChange={setValue} error={error} />

      <Button label="Continuer" onPress={submit} loading={submitting} />
    </Card>
  );
}

function Control({
  question,
  value,
  onChange,
  error,
}: {
  question: PresentedQuestion;
  value: AnswerValue;
  onChange: (v: AnswerValue) => void;
  error: string | null;
}): ReactNode {
  const theme = useTheme();

  if (question.type === 'boolean') {
    return (
      <View style={{ gap: theme.spacing.xs }}>
        <View style={{ flexDirection: 'row', gap: theme.spacing.sm }}>
          {[
            { label: 'Oui', v: true },
            { label: 'Non', v: false },
          ].map((opt) => (
            <View key={opt.label} style={{ flex: 1 }}>
              <Button
                label={opt.label}
                variant={value === opt.v ? 'primary' : 'secondary'}
                onPress={() => onChange(opt.v)}
              />
            </View>
          ))}
        </View>
        {error ? (
          <Text variant="caption" color="danger">
            {error}
          </Text>
        ) : null}
      </View>
    );
  }

  if (question.type === 'select' || question.type === 'multiselect') {
    const selected = new Set(
      question.type === 'multiselect' ? ((value as string[]) ?? []) : value ? [value as string] : [],
    );
    const toggle = (optValue: string) => {
      if (question.type === 'multiselect') {
        const next = new Set(selected);
        if (next.has(optValue)) next.delete(optValue);
        else next.add(optValue);
        onChange([...next]);
      } else {
        onChange(optValue);
      }
    };
    return (
      <View style={{ gap: theme.spacing.xs }}>
        {question.options.map((opt) => (
          <Pressable
            key={opt.value}
            onPress={() => toggle(opt.value)}
            style={{
              minHeight: 48,
              paddingHorizontal: theme.spacing.md,
              borderRadius: theme.radius.md,
              borderWidth: 1,
              borderColor: selected.has(opt.value) ? theme.colors.primary : theme.colors.border,
              backgroundColor: selected.has(opt.value) ? theme.colors.surfaceMuted : theme.colors.surface,
              justifyContent: 'center',
            }}
          >
            <Text style={{ color: selected.has(opt.value) ? theme.colors.primary : theme.colors.text }}>
              {opt.label}
            </Text>
          </Pressable>
        ))}
        {error ? (
          <Text variant="caption" color="danger">
            {error}
          </Text>
        ) : null}
      </View>
    );
  }

  // text / number / address / date / time (+ fallback) → saisie texte
  const isNumber = question.type === 'number';
  return (
    <Input
      value={value === null || value === undefined ? '' : String(value)}
      onChangeText={(t) => onChange(isNumber ? (t === '' ? null : Number(t)) : t)}
      keyboardType={isNumber ? 'numeric' : 'default'}
      placeholder={question.type === 'address' ? 'Adresse' : undefined}
      error={error}
    />
  );
}
