-- ============================================================================
-- Auth — Custom Access Token Hook : injection du claim `user_role` dans le JWT
-- Réf. architecture §5.2
--
-- À chaque émission de token, GoTrue appelle ce hook (exécuté en tant que rôle
-- supabase_auth_admin). On lit le rôle dans public.profiles et on l'ajoute aux
-- claims -> les policies RLS lisent ensuite le rôle via current_user_role()
-- sans requête supplémentaire ni récursion (performant, §5.2).
--
-- Évolutif : le hook est INDÉPENDANT de la méthode de connexion (téléphone,
-- Apple, Google futur). Ajouter un provider ne modifie ni ce hook ni la RLS.
-- ============================================================================

create or replace function public.custom_access_token_hook(event jsonb)
returns jsonb
language plpgsql
stable
set search_path = ''
as $$
declare
  v_claims jsonb := event -> 'claims';
  v_role   public.user_role;
begin
  select p.role into v_role
  from public.profiles p
  where p.id = (event ->> 'user_id')::uuid;

  -- Défaut robuste : 'client' si le profil n'existe pas encore.
  v_claims := jsonb_set(
    v_claims,
    '{user_role}',
    to_jsonb(coalesce(v_role, 'client')::text)
  );

  return jsonb_set(event, '{claims}', v_claims);
end;
$$;

comment on function public.custom_access_token_hook(jsonb) is
  'Hook GoTrue : ajoute le claim user_role (lu dans profiles) au JWT. Réf §5.2.';

-- ----------------------------------------------------------------------------
-- Permissions : seul le rôle d'auth peut exécuter le hook et lire le rôle.
-- ----------------------------------------------------------------------------
grant usage  on schema public to supabase_auth_admin;
grant execute on function public.custom_access_token_hook(jsonb) to supabase_auth_admin;
revoke execute on function public.custom_access_token_hook(jsonb) from authenticated, anon, public;

-- Le hook (exécuté en supabase_auth_admin) doit pouvoir lire profiles.
grant select on table public.profiles to supabase_auth_admin;

-- RLS : lecture de profiles autorisée au rôle d'auth, uniquement pour le hook.
create policy profiles_auth_admin_read on public.profiles
  for select to supabase_auth_admin
  using (true);
