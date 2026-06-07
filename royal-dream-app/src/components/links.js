import { Linking } from 'react-native';
import { brand } from '../data';

export function openWhatsApp(message) {
  const text = encodeURIComponent(
    message ||
      "Bonjour, j'aimerais des informations sur la location d'un château gonflable ou d'une mascotte."
  );
  Linking.openURL(`https://wa.me/${brand.whatsapp}?text=${text}`).catch(() => {});
}

export function openPhone() {
  Linking.openURL(`tel:${brand.phone}`).catch(() => {});
}

export function openEmail() {
  Linking.openURL(`mailto:${brand.email}`).catch(() => {});
}
