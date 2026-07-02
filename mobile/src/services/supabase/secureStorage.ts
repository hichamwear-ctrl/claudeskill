import AsyncStorage from '@react-native-async-storage/async-storage';
import * as SecureStore from 'expo-secure-store';
import { Platform } from 'react-native';

/**
 * Adaptateur de stockage pour la session Supabase.
 *
 * - Natif : **expo-secure-store** (Keychain/Keystore). La valeur d'une entrée
 *   SecureStore est limitée (~2 Ko) ; la session peut la dépasser → on
 *   **découpe en morceaux** transparents.
 * - Web : `AsyncStorage` (localStorage) — SecureStore n'y est pas disponible.
 *
 * Interface attendue par supabase-js : `{ getItem, setItem, removeItem }`.
 */
const CHUNK_SIZE = 1800;
const isWeb = Platform.OS === 'web';

function metaKey(key: string): string {
  return `${key}__chunks`;
}

function chunkKey(key: string, index: number): string {
  return `${key}__${index}`;
}

async function setItem(key: string, value: string): Promise<void> {
  if (isWeb) {
    await AsyncStorage.setItem(key, value);
    return;
  }
  await removeItem(key);
  const total = Math.max(1, Math.ceil(value.length / CHUNK_SIZE));
  await SecureStore.setItemAsync(metaKey(key), String(total));
  for (let i = 0; i < total; i += 1) {
    await SecureStore.setItemAsync(chunkKey(key, i), value.slice(i * CHUNK_SIZE, (i + 1) * CHUNK_SIZE));
  }
}

async function getItem(key: string): Promise<string | null> {
  if (isWeb) return AsyncStorage.getItem(key);
  const meta = await SecureStore.getItemAsync(metaKey(key));
  if (meta === null) return null;
  const total = Number.parseInt(meta, 10);
  let out = '';
  for (let i = 0; i < total; i += 1) {
    const part = await SecureStore.getItemAsync(chunkKey(key, i));
    if (part === null) return null; // morceau manquant → session invalide
    out += part;
  }
  return out;
}

async function removeItem(key: string): Promise<void> {
  if (isWeb) {
    await AsyncStorage.removeItem(key);
    return;
  }
  const meta = await SecureStore.getItemAsync(metaKey(key));
  const total = meta ? Number.parseInt(meta, 10) : 0;
  for (let i = 0; i < total; i += 1) {
    await SecureStore.deleteItemAsync(chunkKey(key, i));
  }
  await SecureStore.deleteItemAsync(metaKey(key));
}

export const largeSecureStore = { getItem, setItem, removeItem };
