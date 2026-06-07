import React from 'react';
import { Pressable, Text, StyleSheet } from 'react-native';
import { colors, shadows } from '../theme';
import { openWhatsApp } from './links';

export default function WhatsAppButton({ bottom }) {
  return (
    <Pressable
      style={[styles.btn, { bottom }]}
      onPress={() => openWhatsApp()}
      accessibilityLabel="Contacter Royal Dream Events sur WhatsApp"
    >
      <Text style={styles.icon}>💬</Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  btn: {
    position: 'absolute',
    right: 18,
    height: 58,
    width: 58,
    borderRadius: 29,
    backgroundColor: colors.whatsapp,
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 60,
    ...shadows.magic,
  },
  icon: { fontSize: 26 },
});
