import React from 'react';
import { View, Text, Image, StyleSheet, Dimensions } from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { colors, fonts, radius, shadows, magicTextGradient, goldTextGradient } from '../theme';
import { heroImage, heroStats, heroFloatBadges } from '../data';
import { GradientText, GradientButton, GhostButton, Glass } from './ui';

const { width } = Dimensions.get('window');

export default function Hero({ topPad, onReserve, onQuote }) {
  return (
    <View style={[styles.section, { paddingTop: topPad }]}>
      {/* Hero image card */}
      <View style={styles.imageCard}>
        <Image source={{ uri: heroImage }} style={styles.image} resizeMode="cover" />
        <LinearGradient
          colors={['rgba(11,11,34,0.1)', 'rgba(11,11,34,0.85)']}
          style={StyleSheet.absoluteFill}
        />
        <Glass style={styles.imageBadge}>
          <Text style={styles.imageBadgeText}>✦ Mascottes incluses</Text>
        </Glass>
      </View>

      {/* Floating accent badges */}
      <View style={styles.floatRow}>
        {heroFloatBadges.map((b) => (
          <Glass key={b.label} style={styles.floatBadge}>
            <Text style={styles.floatEmoji}>{b.emoji}</Text>
            <Text style={styles.floatLabel}>{b.label}</Text>
          </Glass>
        ))}
      </View>

      <Glass style={styles.eyebrow}>
        <Text style={styles.eyebrowText}>
          <Text style={{ color: colors.gold }}>✦ </Text>
          Châteaux gonflables & Mascottes — Bruxelles
        </Text>
      </Glass>

      <View style={styles.titleWrap}>
        <View style={styles.titleRow}>
          <Text style={styles.title}>La magie </Text>
          <GradientText gradient={magicTextGradient} style={styles.title}>arrive</GradientText>
        </View>
        <Text style={styles.title}>chez vous.</Text>
      </View>

      <Text style={styles.lead}>
        Location de <Text style={styles.leadStrong}>châteaux gonflables</Text> et{' '}
        <Text style={styles.leadStrong}>mascottes</Text> (souris magique, héros araignée, reine des
        glaces, petit bleu) pour <Text style={styles.leadStrong}>anniversaires d'enfants à Bruxelles</Text>{' '}
        et en Belgique francophone.
      </Text>

      <View style={styles.ctaRow}>
        <GradientButton label="🏰 Réserver mon château" onPress={onReserve} style={styles.cta} />
        <GhostButton label="✨ Devis gratuit" onPress={onQuote} style={styles.cta} />
      </View>

      <View style={styles.stats}>
        {heroStats.map((s) => (
          <View key={s.label} style={styles.statItem}>
            <GradientText gradient={goldTextGradient} style={styles.statValue}>
              {s.value}
            </GradientText>
            <Text style={styles.statLabel}>{s.label}</Text>
          </View>
        ))}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  section: { paddingHorizontal: 18, paddingBottom: 28 },
  imageCard: {
    aspectRatio: 5 / 3,
    borderRadius: radius.xl,
    overflow: 'hidden',
    ...shadows.magic,
  },
  image: { width: '100%', height: '100%' },
  imageBadge: {
    position: 'absolute',
    top: 12,
    left: 12,
    paddingHorizontal: 12,
    paddingVertical: 5,
    borderRadius: radius.pill,
  },
  imageBadgeText: {
    color: colors.gold,
    fontFamily: fonts.bodyBold,
    fontSize: 10,
    letterSpacing: 1,
    textTransform: 'uppercase',
  },
  floatRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
    justifyContent: 'center',
    marginTop: 16,
  },
  floatBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    paddingHorizontal: 14,
    paddingVertical: 9,
    borderRadius: radius.md,
  },
  floatEmoji: { fontSize: 18 },
  floatLabel: { color: colors.text, fontFamily: fonts.bodySemi, fontSize: 13 },
  eyebrow: {
    alignSelf: 'flex-start',
    marginTop: 22,
    paddingHorizontal: 16,
    paddingVertical: 7,
    borderRadius: radius.pill,
  },
  eyebrowText: {
    color: colors.text,
    fontFamily: fonts.bodySemi,
    fontSize: 12,
    letterSpacing: 0.6,
    textTransform: 'uppercase',
  },
  titleWrap: { marginTop: 14 },
  titleRow: { flexDirection: 'row', alignItems: 'center', flexWrap: 'wrap' },
  title: {
    color: colors.text,
    fontFamily: fonts.display,
    fontSize: 44,
    lineHeight: 46,
  },
  lead: {
    color: colors.textSoft,
    fontFamily: fonts.body,
    fontSize: 16,
    lineHeight: 24,
    marginTop: 18,
  },
  leadStrong: { color: colors.text, fontFamily: fonts.bodyBold },
  ctaRow: { marginTop: 22, gap: 12 },
  cta: { width: '100%' },
  stats: {
    flexDirection: 'row',
    gap: 18,
    marginTop: 28,
  },
  statItem: { alignItems: 'flex-start' },
  statValue: { fontFamily: fonts.serif, fontSize: 32, lineHeight: 38 },
  statLabel: {
    color: colors.textMuted,
    fontFamily: fonts.bodySemi,
    fontSize: 11,
    letterSpacing: 1,
    textTransform: 'uppercase',
    marginTop: 2,
  },
});
