import * as ImagePicker from 'expo-image-picker';

import { supabase } from '@/services/supabase/client';

const B64 = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/';

/** Décodeur base64 → octets (sans dépendance ni `atob`, fiable sous Hermes). */
function base64ToBytes(b64: string): Uint8Array {
  const clean = b64.replace(/=+$/, '');
  const bytes = new Uint8Array(Math.floor((clean.length * 3) / 4));
  let p = 0;
  let buffer = 0;
  let bits = 0;
  for (let i = 0; i < clean.length; i += 1) {
    const c = B64.indexOf(clean[i] as string);
    if (c < 0) continue;
    buffer = (buffer << 6) | c;
    bits += 6;
    if (bits >= 8) {
      bits -= 8;
      bytes[p] = (buffer >> bits) & 0xff;
      p += 1;
    }
  }
  return bytes.subarray(0, p);
}

/**
 * Sélectionne une image (galerie), la compresse et l'upload dans un bucket
 * privé. Retourne le chemin de stockage, ou `null` si l'utilisateur annule.
 */
export async function pickAndUploadImage(input: {
  bucket: string;
  pathPrefix: string;
}): Promise<string | null> {
  const perm = await ImagePicker.requestMediaLibraryPermissionsAsync();
  if (!perm.granted) throw new Error('Permission galerie refusée');

  const res = await ImagePicker.launchImageLibraryAsync({
    mediaTypes: ['images'],
    quality: 0.6,
    base64: true,
  });
  const asset = res.assets?.[0];
  if (res.canceled || !asset?.base64) return null;

  const path = `${input.pathPrefix}/${Date.now()}.jpg`;
  const { error } = await supabase.storage
    .from(input.bucket)
    .upload(path, base64ToBytes(asset.base64), { contentType: 'image/jpeg', upsert: false });
  if (error) throw error;
  return path;
}
