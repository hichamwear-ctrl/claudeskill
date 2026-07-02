import { describe, expect, it } from '@jest/globals';

import { routes } from '@/constants/routes';

import { guardAuthGroup, guardClientGroup, guardOperatorGroup, resolveLanding } from '../guards';

describe('resolveLanding', () => {
  it('attend pendant le chargement', () => {
    expect(resolveLanding('loading', null)).toBeNull();
  });
  it('envoie à la connexion si non authentifié', () => {
    expect(resolveLanding('unauthenticated', null)).toBe(routes.signIn);
  });
  it('route le client vers l’accueil (rôle null = client)', () => {
    expect(resolveLanding('authenticated', 'client')).toBe(routes.clientHome);
    expect(resolveLanding('authenticated', null)).toBe(routes.clientHome);
  });
  it('route operator/admin vers le cockpit', () => {
    expect(resolveLanding('authenticated', 'operator')).toBe(routes.operatorCockpit);
    expect(resolveLanding('authenticated', 'admin')).toBe(routes.operatorCockpit);
  });
});

describe('guardAuthGroup', () => {
  it('laisse passer un visiteur non authentifié', () => {
    expect(guardAuthGroup('unauthenticated', null)).toBeNull();
  });
  it('éjecte un utilisateur déjà connecté vers son accueil', () => {
    expect(guardAuthGroup('authenticated', 'operator')).toBe(routes.operatorCockpit);
  });
});

describe('guardClientGroup', () => {
  it('exige une session', () => {
    expect(guardClientGroup('unauthenticated', null)).toBe(routes.signIn);
  });
  it('renvoie un opérateur vers le cockpit', () => {
    expect(guardClientGroup('authenticated', 'operator')).toBe(routes.operatorCockpit);
  });
  it('laisse le client dans le groupe', () => {
    expect(guardClientGroup('authenticated', 'client')).toBeNull();
  });
});

describe('guardOperatorGroup', () => {
  it('exige une session', () => {
    expect(guardOperatorGroup('unauthenticated', null)).toBe(routes.signIn);
  });
  it('renvoie un client vers l’accueil client', () => {
    expect(guardOperatorGroup('authenticated', 'client')).toBe(routes.clientHome);
  });
  it('laisse operator/admin dans le groupe', () => {
    expect(guardOperatorGroup('authenticated', 'operator')).toBeNull();
    expect(guardOperatorGroup('authenticated', 'admin')).toBeNull();
  });
});
