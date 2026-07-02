/**
 * Types de la base Supabase — dérivés du schéma BACKEND GELÉ (M1→M12).
 *
 * ⚠️ Fichier de référence rédigé à la main à partir des migrations
 * `supabase/migrations/*`. En environnement disposant de la stack Supabase
 * (locale ou liée), régénérer la version faisant autorité avec :
 *
 *     npm run gen:types      # supabase gen types typescript --local
 *
 * Le mobile n'écrit jamais `service_role` : seules les surfaces soumises à la
 * RLS (PostgREST), les RPC `SECURITY DEFINER` et les Edge Functions sont
 * utilisées. Ces types couvrent les tables/fonctions consommées par l'app.
 */

export type Json = string | number | boolean | null | { [key: string]: Json | undefined } | Json[];

export type Database = {
  public: {
    Tables: {
      profiles: {
        Row: {
          id: string;
          role: Database['public']['Enums']['user_role'];
          first_name: string | null;
          last_name: string | null;
          email: string | null;
          phone: string | null;
          avatar_url: string | null;
          locale: string;
          created_at: string;
          updated_at: string;
        };
        Insert: {
          id: string;
          role?: Database['public']['Enums']['user_role'];
          first_name?: string | null;
          last_name?: string | null;
          email?: string | null;
          phone?: string | null;
          avatar_url?: string | null;
          locale?: string;
          created_at?: string;
          updated_at?: string;
        };
        Update: {
          first_name?: string | null;
          last_name?: string | null;
          email?: string | null;
          phone?: string | null;
          avatar_url?: string | null;
          locale?: string;
        };
        Relationships: [];
      };
      missions: {
        Row: {
          id: string;
          client_id: string;
          operator_id: string | null;
          category_id: string | null;
          family: Database['public']['Enums']['mission_family'] | null;
          status: Database['public']['Enums']['mission_status'];
          conversation_id: string | null;
          group_id: string | null;
          sequence: number | null;
          depends_on_mission_id: string | null;
          title: string | null;
          free_text: string | null;
          instructions: string | null;
          details: Json;
          metadata: Json;
          dropoff_address: string | null;
          estimated_price: number | null;
          estimated_eta_min: number | null;
          service_fee: number | null;
          advance_estimate: number | null;
          advance_actual: number | null;
          final_amount: number | null;
          operator_earning: number | null;
          quoted_price: number | null;
          quote_expires_at: string | null;
          quote_status: string | null;
          tip_amount: number | null;
          submitted_at: string | null;
          review_claimed_by: string | null;
          review_claimed_at: string | null;
          reviewed_at: string | null;
          reviewed_by: string | null;
          review_reason: string | null;
          accepted_at: string | null;
          completed_at: string | null;
          cancelled_at: string | null;
          cancelled_by: Database['public']['Enums']['cancel_actor'] | null;
          cancel_reason: string | null;
          scheduled_for: string | null;
          queue_position: number | null;
          created_at: string;
          updated_at: string;
        };
        Insert: never;
        Update: never;
        Relationships: [];
      };
      mission_events: {
        Row: {
          id: string;
          mission_id: string;
          from_status: Database['public']['Enums']['mission_status'] | null;
          to_status: Database['public']['Enums']['mission_status'] | null;
          actor_id: string | null;
          reason: string | null;
          metadata: Json;
          created_at: string;
        };
        Insert: never;
        Update: never;
        Relationships: [];
      };
      conversations: {
        Row: {
          id: string;
          client_id: string;
          status: Database['public']['Enums']['conversation_status'];
          locale: string;
          state: Json;
          metadata: Json;
          created_at: string;
          updated_at: string;
          expires_at: string | null;
        };
        Insert: never;
        Update: never;
        Relationships: [];
      };
      conversation_turns: {
        Row: {
          id: string;
          conversation_id: string;
          role: string;
          content: Json;
          created_at: string;
        };
        Insert: never;
        Update: never;
        Relationships: [];
      };
      messages: {
        Row: {
          id: string;
          mission_id: string;
          sender_id: string;
          kind: string;
          body: string | null;
          media: Json | null;
          read_at: string | null;
          metadata: Json;
          created_at: string;
        };
        Insert: {
          mission_id: string;
          sender_id: string;
          kind?: string;
          body?: string | null;
          media?: Json | null;
          metadata?: Json;
        };
        Update: never;
        Relationships: [];
      };
      payments: {
        Row: {
          id: string;
          mission_id: string;
          client_id: string;
          provider: string;
          provider_pi_ref: string | null;
          provider_customer_ref: string | null;
          amount_authorized: number | null;
          amount_captured: number | null;
          amount_refunded: number | null;
          currency: string;
          status: Database['public']['Enums']['payment_status'];
          authorized_at: string | null;
          captured_at: string | null;
          metadata: Json;
          created_at: string;
          updated_at: string;
        };
        Insert: never;
        Update: never;
        Relationships: [];
      };
      notifications: {
        Row: {
          id: string;
          user_id: string;
          template: string;
          channel: string;
          title: string;
          body: string | null;
          deep_link: string | null;
          payload: Json;
          mission_id: string | null;
          dedup_key: string;
          pushed: boolean;
          read_at: string | null;
          created_at: string;
        };
        Insert: never;
        Update: {
          read_at?: string | null;
        };
        Relationships: [];
      };
      device_tokens: {
        Row: {
          id: string;
          user_id: string;
          platform: string;
          token: string;
          active: boolean;
          last_seen: string;
          created_at: string;
        };
        Insert: {
          user_id: string;
          platform: string;
          token: string;
          active?: boolean;
          last_seen?: string;
        };
        Update: {
          active?: boolean;
          last_seen?: string;
        };
        Relationships: [];
      };
      service_categories: {
        Row: {
          id: string;
          family: Database['public']['Enums']['mission_family'];
          slug: string;
          label: string;
          icon: string | null;
          is_active: boolean;
          fulfillment: string;
          legal_note: string | null;
          base_fee: number;
          prep_buffer_min: number;
          requires_shopping: boolean;
          requires_preparation: boolean;
          sort_order: number;
          metadata: Json;
          created_at: string;
          updated_at: string;
        };
        Insert: never;
        Update: never;
        Relationships: [];
      };
      question_sets: {
        Row: {
          id: string;
          slug: string;
          name: string;
          category_id: string | null;
          created_at: string;
          updated_at: string;
        };
        Insert: never;
        Update: never;
        Relationships: [];
      };
      questions: {
        Row: {
          id: string;
          set_id: string;
          key: string;
          type: Database['public']['Enums']['question_type'];
          label_key: string;
          help_key: string | null;
          placeholder_key: string | null;
          sort_order: number;
          is_active: boolean;
          visible_when: Json;
          required_when: Json;
          validation: Json;
          metadata: Json;
          created_at: string;
          updated_at: string;
        };
        Insert: never;
        Update: never;
        Relationships: [];
      };
      question_options: {
        Row: {
          id: string;
          question_id: string;
          value: string;
          label_key: string;
          sort_order: number;
          is_active: boolean;
          metadata: Json;
        };
        Insert: never;
        Update: never;
        Relationships: [];
      };
      app_config: {
        Row: {
          key: string;
          value: Json;
          scope: string;
          description: string | null;
          is_active: boolean;
          updated_by: string | null;
          updated_at: string;
        };
        Insert: never;
        Update: never;
        Relationships: [];
      };
      content_strings: {
        Row: {
          key: string;
          locale: string;
          value: string;
          description: string | null;
          is_active: boolean;
          updated_by: string | null;
          updated_at: string;
        };
        Insert: never;
        Update: never;
        Relationships: [];
      };
    };
    Views: Record<string, never>;
    Functions: {
      transition_mission: {
        Args: {
          p_mission_id: string;
          p_to: Database['public']['Enums']['mission_status'];
          p_reason?: string;
          p_price?: number;
          p_eta_min?: number;
          p_metadata?: Json;
        };
        Returns: Json;
      };
      claim_review: {
        Args: { p_mission_id: string; p_release?: boolean };
        Returns: Json;
      };
      estimate_price: {
        Args: {
          p_category_id: string;
          p_dropoff_lng: number;
          p_dropoff_lat: number;
          p_pickup_lng?: number;
          p_pickup_lat?: number;
        };
        Returns: Json;
      };
      zone_check: {
        Args: { p_lng: number; p_lat: number; p_at?: string };
        Returns: Json;
      };
      mark_messages_read: {
        Args: { p_mission_id: string };
        Returns: number;
      };
      update_location: {
        Args: {
          p_lat: number;
          p_lng: number;
          p_heading?: number;
          p_speed?: number;
          p_accuracy?: number;
        };
        Returns: Json;
      };
      get_operator_location: {
        Args: { p_mission_id: string };
        Returns: Json;
      };
      operator_queue: {
        Args: Record<string, never>;
        Returns: Json;
      };
      mission_overview: {
        Args: { p_mission_id: string };
        Returns: Json;
      };
      admin_stats: {
        Args: Record<string, never>;
        Returns: Json;
      };
      validate_config: {
        Args: Record<string, never>;
        Returns: Json;
      };
    };
    Enums: {
      user_role: 'client' | 'operator' | 'admin';
      mission_family: 'shopping' | 'auto' | 'home_service' | 'courier' | 'custom';
      conversation_status: 'active' | 'submitted' | 'abandoned' | 'expired';
      cancel_actor: 'client' | 'operator' | 'admin' | 'system';
      question_type:
        | 'text'
        | 'number'
        | 'boolean'
        | 'select'
        | 'multiselect'
        | 'photo'
        | 'document'
        | 'address'
        | 'date'
        | 'time';
      mission_status:
        | 'created'
        | 'pending_review'
        | 'needs_information'
        | 'rejected'
        | 'accepted'
        | 'assigned'
        | 'searching'
        | 'shopping'
        | 'preparing'
        | 'en_route'
        | 'arrived'
        | 'in_progress'
        | 'completed'
        | 'rated'
        | 'cancelled'
        | 'failed';
      payment_status:
        | 'pending'
        | 'requires_capture'
        | 'succeeded'
        | 'partially_captured'
        | 'canceled'
        | 'refunded'
        | 'failed';
    };
    CompositeTypes: Record<string, never>;
  };
};

/* ---- Helpers d'accès (mêmes noms que la sortie `supabase gen types`) ---- */

type PublicSchema = Database['public'];

export type Tables<T extends keyof PublicSchema['Tables']> = PublicSchema['Tables'][T]['Row'];
export type TablesInsert<T extends keyof PublicSchema['Tables']> =
  PublicSchema['Tables'][T]['Insert'];
export type TablesUpdate<T extends keyof PublicSchema['Tables']> =
  PublicSchema['Tables'][T]['Update'];
export type Enums<T extends keyof PublicSchema['Enums']> = PublicSchema['Enums'][T];
export type FunctionArgs<T extends keyof PublicSchema['Functions']> =
  PublicSchema['Functions'][T]['Args'];
export type FunctionReturns<T extends keyof PublicSchema['Functions']> =
  PublicSchema['Functions'][T]['Returns'];
