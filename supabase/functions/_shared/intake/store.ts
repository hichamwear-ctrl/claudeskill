/**
 * `IntakeStore` concret adossé à Supabase (PostgREST via supabase-js).
 * Utilisé uniquement par les Edge Functions (converse / submit-request).
 *
 * Le client fourni est un client **service_role** (contourne la RLS) : la
 * conversation d'intake est écrite côté serveur (aucun grant d'écriture au
 * client, cf. migration M2.2). La PROPRIÉTÉ est vérifiée en code — chaque lecture
 * filtre sur `client_id` — puisque le service_role ne bénéficie pas de la RLS.
 *
 * Glue fine et directe : non couverte par les tests unitaires (nécessiterait la
 * stack Supabase complète) ; la logique testable vit dans `orchestrator.ts` /
 * `config.ts`, exercée via un store en mémoire.
 */
import type { SupabaseClient } from '@supabase/supabase-js';
import { assembleConfig, type RawOption, type RawQuestion, type RawSet } from './config.ts';
import type { Answers } from '../engine/types.ts';
import type {
  ConversationRow,
  ConversationState,
  IntakeStore,
  LoadedConfig,
  NewTurn,
} from './types.ts';

const KEYWORDS_KEY = 'classification.keywords';

function toState(raw: unknown): ConversationState {
  const s = (raw ?? {}) as { answers?: Answers; classification?: string | null };
  return { answers: s.answers ?? {}, classification: s.classification ?? null };
}

export class SupabaseStore implements IntakeStore {
  constructor(private readonly db: SupabaseClient) {}

  async loadConfig(locale: string): Promise<LoadedConfig> {
    const [setsRes, questionsRes, optionsRes, stringsRes, kwRes] = await Promise.all([
      this.db.from('question_sets').select(
        'id,slug,sort_order,category_id,service_categories(slug)',
      )
        .eq('is_active', true),
      this.db.from('questions')
        .select(
          'id,set_id,key,type,sort_order,label_key,help_key,visible_when,required_when,validation',
        )
        .eq('is_active', true),
      this.db.from('question_options').select('question_id,value,label_key,sort_order').eq(
        'is_active',
        true,
      ),
      this.db.from('content_strings').select('key,value').eq('locale', locale),
      this.db.from('app_config').select('value').eq('key', KEYWORDS_KEY).maybeSingle(),
    ]);
    for (const r of [setsRes, questionsRes, optionsRes, stringsRes]) {
      if (r.error) throw new Error(`loadConfig: ${r.error.message}`);
    }

    const setIdToSlug = new Map<string, string>();
    const sets: RawSet[] = (setsRes.data ?? []).map((s) => {
      setIdToSlug.set(s.id as string, s.slug as string);
      // Ressource embarquée (FK many-to-one) : objet au runtime, typée array par supabase-js.
      const embed = s.service_categories as unknown;
      const cat = (Array.isArray(embed) ? embed[0] : embed) as { slug: string } | null;
      return {
        slug: s.slug as string,
        sortOrder: s.sort_order as number,
        categorySlug: cat?.slug ?? null,
      };
    });

    const questions: RawQuestion[] = (questionsRes.data ?? []).map((q) => ({
      id: q.id as string,
      setSlug: setIdToSlug.get(q.set_id as string) ?? '',
      key: q.key as string,
      type: q.type as string,
      sortOrder: q.sort_order as number,
      labelKey: q.label_key as string,
      helpKey: (q.help_key as string | null) ?? null,
      visibleWhen: (q.visible_when as Record<string, unknown>) ?? {},
      requiredWhen: (q.required_when as Record<string, unknown>) ?? {},
      validation: (q.validation as Record<string, unknown>) ?? {},
    }));

    const options: RawOption[] = (optionsRes.data ?? []).map((o) => ({
      questionId: o.question_id as string,
      value: o.value as string,
      labelKey: o.label_key as string,
      sortOrder: o.sort_order as number,
    }));

    const strings: Record<string, string> = {};
    for (const s of stringsRes.data ?? []) strings[s.key as string] = s.value as string;

    const keywords = (kwRes.data?.value as Record<string, string[]>) ?? {};
    return assembleConfig(sets, questions, options, strings, keywords);
  }

  async createConversation(clientId: string, locale: string): Promise<ConversationRow> {
    const { data, error } = await this.db.from('conversations')
      .insert({ client_id: clientId, locale })
      .select('id,client_id,status,locale,state')
      .single();
    if (error) throw new Error(`createConversation: ${error.message}`);
    return {
      id: data.id,
      clientId: data.client_id,
      status: data.status,
      locale: data.locale,
      state: toState(data.state),
    };
  }

  async getConversation(id: string, clientId: string): Promise<ConversationRow | null> {
    const { data, error } = await this.db.from('conversations')
      .select('id,client_id,status,locale,state')
      .eq('id', id).eq('client_id', clientId).maybeSingle();
    if (error) throw new Error(`getConversation: ${error.message}`);
    if (!data) return null;
    return {
      id: data.id,
      clientId: data.client_id,
      status: data.status,
      locale: data.locale,
      state: toState(data.state),
    };
  }

  async saveState(id: string, state: ConversationState): Promise<void> {
    const { error } = await this.db.from('conversations').update({ state }).eq('id', id);
    if (error) throw new Error(`saveState: ${error.message}`);
  }

  async setStatus(id: string, status: ConversationRow['status']): Promise<void> {
    const { error } = await this.db.from('conversations').update({ status }).eq('id', id);
    if (error) throw new Error(`setStatus: ${error.message}`);
  }

  async appendTurns(turns: NewTurn[]): Promise<void> {
    if (turns.length === 0) return;
    const rows = turns.map((t) => ({
      conversation_id: t.conversationId,
      role: t.role,
      content: t.content,
      slot_key: t.slotKey ?? null,
      metadata: t.metadata ?? {},
    }));
    const { error } = await this.db.from('conversation_turns').insert(rows);
    if (error) throw new Error(`appendTurns: ${error.message}`);
  }
}
