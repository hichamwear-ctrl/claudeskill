import React from 'react';
import { Modal, View, Text, Image, Pressable, ScrollView, StyleSheet } from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { colors, fonts, radius, shadows, goldGradient } from '../theme';
import { castleIncludes } from '../data';
import { GradientButton } from './ui';
import { openWhatsApp } from './links';

export default function CastleModal({ castle, onClose }) {
  return (
    <Modal
      visible={!!castle}
      transparent
      animationType="slide"
      onRequestClose={onClose}
    >
      <View style={styles.overlay}>
        <Pressable style={StyleSheet.absoluteFill} onPress={onClose} />
        <View style={styles.sheet}>
          {castle ? (
            <ScrollView showsVerticalScrollIndicator={false}>
              <View style={styles.handle} />
              <Pressable style={styles.close} onPress={onClose} hitSlop={10}>
                <Text style={styles.closeText}>✕</Text>
              </Pressable>

              <View style={styles.imgWrap}>
                <Image source={{ uri: castle.image }} style={styles.img} resizeMode="contain" />
                {castle.badge ? (
                  <LinearGradient colors={goldGradient} style={styles.badge}>
                    <Text style={styles.badgeText}>{castle.badge}</Text>
                  </LinearGradient>
                ) : null}
              </View>

              <Text style={styles.cat}>{castle.category}</Text>
              <Text style={styles.name}>{castle.name}</Text>

              <View style={styles.priceRow}>
                <Text style={styles.price}>{castle.price}€</Text>
                <Text style={styles.per}>/jour · livraison incluse</Text>
              </View>

              <Text style={styles.desc}>{castle.desc}</Text>

              <View style={styles.includes}>
                {castleIncludes.map((line) => (
                  <Text key={line} style={styles.includeItem}>{line}</Text>
                ))}
              </View>

              <GradientButton
                label={`💬 Réserver le ${castle.name}`}
                onPress={() =>
                  openWhatsApp(
                    `Bonjour, je souhaite réserver le château gonflable « ${castle.name} » (${castle.price}€/jour). Pouvez-vous me confirmer la disponibilité ?`
                  )
                }
                style={{ marginTop: 18 }}
              />
              <Pressable onPress={onClose} style={styles.closeBtn}>
                <Text style={styles.closeBtnText}>Continuer à explorer</Text>
              </Pressable>
            </ScrollView>
          ) : null}
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  overlay: { flex: 1, justifyContent: 'flex-end', backgroundColor: 'rgba(7,7,26,0.7)' },
  sheet: {
    maxHeight: '88%',
    backgroundColor: '#171145',
    borderTopLeftRadius: radius.xl,
    borderTopRightRadius: radius.xl,
    borderWidth: 1,
    borderColor: colors.border,
    padding: 20,
    ...shadows.magic,
  },
  handle: {
    alignSelf: 'center',
    width: 44, height: 5, borderRadius: 3,
    backgroundColor: 'rgba(255,255,255,0.25)',
    marginBottom: 14,
  },
  close: { position: 'absolute', top: 0, right: 0, padding: 6, zIndex: 5 },
  closeText: { color: colors.textMuted, fontSize: 18 },
  imgWrap: {
    aspectRatio: 1.4,
    borderRadius: radius.lg,
    backgroundColor: 'rgba(255,255,255,0.05)',
    padding: 10,
    overflow: 'hidden',
  },
  img: { width: '100%', height: '100%' },
  badge: {
    position: 'absolute', top: 12, left: 12,
    borderRadius: radius.pill, paddingHorizontal: 12, paddingVertical: 4,
  },
  badgeText: {
    color: '#3a2600', fontFamily: fonts.bodyBold, fontSize: 10,
    letterSpacing: 0.5, textTransform: 'uppercase',
  },
  cat: {
    color: colors.violet, fontFamily: fonts.bodyBold, fontSize: 12,
    letterSpacing: 1, textTransform: 'uppercase', marginTop: 16,
  },
  name: { color: colors.text, fontFamily: fonts.display, fontSize: 26, marginTop: 4 },
  priceRow: { flexDirection: 'row', alignItems: 'flex-end', gap: 6, marginTop: 8 },
  price: { color: colors.gold, fontFamily: fonts.serif, fontSize: 30 },
  per: { color: colors.textMuted, fontFamily: fonts.body, fontSize: 13, marginBottom: 4 },
  desc: { color: colors.textSoft, fontFamily: fonts.body, fontSize: 15, lineHeight: 23, marginTop: 14 },
  includes: {
    marginTop: 18, gap: 10,
    backgroundColor: colors.glass, borderRadius: radius.md,
    borderWidth: 1, borderColor: colors.border, padding: 16,
  },
  includeItem: { color: colors.text, fontFamily: fonts.bodySemi, fontSize: 14 },
  closeBtn: { alignItems: 'center', paddingVertical: 16 },
  closeBtnText: { color: colors.textMuted, fontFamily: fonts.bodySemi, fontSize: 14 },
});
