import React, { useState } from 'react';
import { View, Text, Image, Pressable, StyleSheet, Dimensions } from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import {
  colors, fonts, radius, shadows,
  magicTextGradient, goldTextGradient, goldGradient, royalGradient,
} from '../theme';
import {
  mascotGroupImage, mascotStats, castles, whyCards, trustBadges,
  reviews, aboutParagraphs, teamImage, zones, faq, brand, contactBgImage,
} from '../data';
import { GradientText, Glass, GradientButton } from './ui';
import { openWhatsApp, openPhone, openEmail } from './links';

const { width } = Dimensions.get('window');
const H_PAD = 18;
const GRID_GAP = 12;
const CARD_W = (width - H_PAD * 2 - GRID_GAP) / 2;

/* ----------------------------- MASCOTTES ----------------------------- */
export function Mascottes({ onReserve }) {
  return (
    <View style={[styles.section, styles.padX]}>
      <View style={styles.center}>
        <View style={styles.goldEyebrow}>
          <Text style={styles.goldEyebrowText}>✨ Mascottes pour anniversaires à Bruxelles</Text>
        </View>
        <Text style={[styles.h2, styles.centerText]}>Vos héros préférés</Text>
        <GradientText gradient={magicTextGradient} style={[styles.h2, styles.centerText]}>
          à votre porte
        </GradientText>
        <Text style={[styles.sub, styles.centerText]}>
          Location de mascottes professionnelles à Bruxelles : nos artistes costumés animent les
          fêtes d'enfants et font briller les yeux des petits comme des grands.
        </Text>
      </View>

      <Image source={{ uri: mascotGroupImage }} style={styles.mascotImg} resizeMode="contain" />

      <View style={styles.pricePill}>
        <View style={styles.priceDot} />
        <Text style={styles.pricePillText}>
          À partir de 89,99€ / heure <Text style={styles.pricePillSoft}>· sans forfait imposé</Text>
        </Text>
      </View>

      <View style={styles.mascotStatsCard}>
        {mascotStats.map((s, i) => (
          <View
            key={s.label}
            style={[styles.mascotStat, i < mascotStats.length - 1 && styles.mascotStatBorder]}
          >
            <Text style={styles.mascotStatValue}>{s.value}</Text>
            <Text style={styles.mascotStatLabel}>{s.label}</Text>
            <Text style={styles.mascotStatNote}>{s.note}</Text>
          </View>
        ))}
      </View>

      <Glass style={styles.packCard}>
        <Text style={styles.packEmoji}>🎁</Text>
        <View style={styles.packBody}>
          <Text style={styles.packTitle}>Pack Magique : Château + Mascotte</Text>
          <Text style={styles.packText}>
            Réservez ensemble — recevez <Text style={styles.bold}>30 min d'animation offertes</Text>.
          </Text>
        </View>
        <GradientButton
          label="Réserver le pack"
          gradient={goldGradient}
          textColor="#3a2600"
          onPress={() => onReserve('Pack Magique (Château + Mascotte)')}
          style={styles.packBtn}
        />
      </Glass>
    </View>
  );
}

/* ------------------------------ CHÂTEAUX ----------------------------- */
export function Chateaux({ onCastlePress }) {
  return (
    <LinearGradient colors={royalGradient} style={[styles.section, styles.padX]}>
      <Text style={styles.magicEyebrow}>Location châteaux gonflables Bruxelles</Text>
      <View style={styles.row}>
        <Text style={styles.h2}>10 châteaux </Text>
        <GradientText gradient={magicTextGradient} style={styles.h2}>enchantés</GradientText>
      </View>
      <Text style={styles.sub}>
        Un thème pour chaque rêve. Touchez un château pour voir les détails et l'ajouter à votre
        sélection.
      </Text>

      <View style={styles.grid}>
        {castles.map((c) => (
          <Pressable key={c.name} style={styles.castleCard} onPress={() => onCastlePress(c)}>
            {c.badge ? (
              <LinearGradient colors={goldGradient} style={styles.castleBadge}>
                <Text style={styles.castleBadgeText}>{c.badge}</Text>
              </LinearGradient>
            ) : null}
            <View style={styles.castleImgWrap}>
              <Image source={{ uri: c.image }} style={styles.castleImg} resizeMode="contain" />
            </View>
            <View style={styles.castleInfo}>
              <Text style={styles.castleCat} numberOfLines={1}>{c.category}</Text>
              <Text style={styles.castleName} numberOfLines={1}>{c.name}</Text>
              <View style={styles.castlePriceRow}>
                <Text style={styles.castlePrice}>
                  {c.price}€<Text style={styles.castlePer}>/jour</Text>
                </Text>
                <Text style={styles.castleArrow}>→</Text>
              </View>
            </View>
          </Pressable>
        ))}
      </View>
    </LinearGradient>
  );
}

/* ------------------------------ POURQUOI ----------------------------- */
export function Pourquoi() {
  return (
    <View style={[styles.section, styles.padX]}>
      <View style={styles.center}>
        <View style={styles.row}>
          <Text style={styles.h2}>Pourquoi </Text>
          <GradientText gradient={goldTextGradient} style={styles.h2}>Royal Dream</GradientText>
          <Text style={styles.h2}> ?</Text>
        </View>
        <Text style={[styles.sub, styles.centerText]}>
          Une fête sans stress, des souvenirs pour toujours.
        </Text>
      </View>

      <View style={styles.grid}>
        {whyCards.map((c) => (
          <Glass key={c.title} style={styles.whyCard}>
            <Text style={styles.whyEmoji}>{c.emoji}</Text>
            <Text style={styles.whyTitle}>{c.title}</Text>
            <Text style={styles.whyText}>{c.text}</Text>
          </Glass>
        ))}
      </View>
    </View>
  );
}

/* --------------------------- TRUST BADGES ---------------------------- */
export function TrustBadges() {
  return (
    <View style={[styles.padX, { paddingVertical: 8 }]}>
      <View style={styles.grid}>
        {trustBadges.map((b) => (
          <Glass key={b.text} style={styles.trustCard}>
            <Text style={styles.trustEmoji}>{b.emoji}</Text>
            <Text style={styles.trustText}>{b.text}</Text>
          </Glass>
        ))}
      </View>
    </View>
  );
}

/* ------------------------------- AVIS -------------------------------- */
export function Avis() {
  return (
    <View style={[styles.section, styles.padX]}>
      <View style={styles.center}>
        <Text style={styles.goldLabel}>Avis clients</Text>
        <View style={styles.row}>
          <Text style={styles.h2}>Ils ont vécu </Text>
          <GradientText gradient={magicTextGradient} style={styles.h2}>la magie</GradientText>
        </View>
      </View>

      <View style={{ gap: GRID_GAP, marginTop: 22 }}>
        {reviews.map((r) => (
          <Glass key={r.author} style={styles.reviewCard}>
            <Text style={styles.stars}>★★★★★</Text>
            <Text style={styles.reviewText}>“{r.text}”</Text>
            <Text style={styles.reviewAuthor}>— {r.author}, {r.city}</Text>
          </Glass>
        ))}
      </View>
    </View>
  );
}

/* -------------------------- QUI SOMMES-NOUS -------------------------- */
export function QuiSommesNous() {
  return (
    <View style={[styles.section, styles.padX]}>
      <Glass style={styles.aboutImgWrap}>
        <Image source={{ uri: teamImage }} style={styles.aboutImg} resizeMode="cover" />
      </Glass>
      <Text style={[styles.magicEyebrow, { marginTop: 20 }]}>Qui sommes-nous</Text>
      <View style={styles.row}>
        <Text style={styles.h2}>Une équipe locale, </Text>
        <GradientText gradient={goldTextGradient} style={styles.h2}>passionnée</GradientText>
      </View>
      {aboutParagraphs.map((p, i) => (
        <Text key={i} style={[styles.sub, i === 0 && { color: colors.textSoft }]}>{p}</Text>
      ))}
    </View>
  );
}

/* ------------------------------- ZONES ------------------------------- */
export function Zones() {
  return (
    <LinearGradient colors={['#15114a', '#1b1857']} style={[styles.section, styles.padX]}>
      <View style={styles.center}>
        <Text style={styles.goldLabel}>Zones desservies</Text>
        <Text style={[styles.h2, styles.centerText]}>Châteaux gonflables & mascottes</Text>
        <GradientText gradient={magicTextGradient} style={[styles.h2b, styles.centerText]}>
          à Bruxelles et en Belgique francophone
        </GradientText>
        <Text style={[styles.sub, styles.centerText]}>
          Nous intervenons à domicile pour anniversaires, fêtes d'école, communions et événements
          privés dans toute la Région de Bruxelles-Capitale, le Brabant Wallon et la Wallonie.
        </Text>
      </View>

      <View style={styles.zoneWrap}>
        {zones.map((z) => (
          <Glass key={z} style={styles.zoneChip}>
            <Text style={styles.zoneText}>📍 {z}</Text>
          </Glass>
        ))}
      </View>
    </LinearGradient>
  );
}

/* -------------------------------- FAQ -------------------------------- */
function FaqItem({ item }) {
  const [open, setOpen] = useState(false);
  return (
    <Glass style={styles.faqCard}>
      <Pressable style={styles.faqHead} onPress={() => setOpen((o) => !o)}>
        <Text style={styles.faqQ}>{item.q}</Text>
        <Text style={[styles.faqPlus, open && { transform: [{ rotate: '45deg' }] }]}>+</Text>
      </Pressable>
      {open ? <Text style={styles.faqA}>{item.a}</Text> : null}
    </Glass>
  );
}

export function Faq() {
  return (
    <View style={[styles.section, styles.padX]}>
      <View style={styles.center}>
        <Text style={styles.magicLabel}>Questions fréquentes</Text>
        <View style={styles.row}>
          <Text style={styles.h2}>Tout ce que vous devez </Text>
          <GradientText gradient={goldTextGradient} style={styles.h2}>savoir</GradientText>
        </View>
      </View>
      <View style={{ gap: 12, marginTop: 22 }}>
        {faq.map((f) => <FaqItem key={f.q} item={f} />)}
      </View>
    </View>
  );
}

/* ------------------------------ CONTACT ------------------------------ */
export function Contact() {
  return (
    <View style={[styles.section, styles.padX]}>
      <View style={styles.contactCard}>
        <Image source={{ uri: contactBgImage }} style={StyleSheet.absoluteFill} resizeMode="cover" />
        <LinearGradient
          colors={['rgba(11,11,34,0.96)', 'rgba(11,11,34,0.7)', 'rgba(124,58,237,0.35)']}
          start={{ x: 0, y: 0 }}
          end={{ x: 1, y: 1 }}
          style={styles.contactInner}
        >
          <Text style={styles.goldLabel}>Réserver maintenant</Text>
          <View style={[styles.row, { marginTop: 6 }]}>
            <Text style={styles.h2}>Prêt à vivre </Text>
            <GradientText gradient={magicTextGradient} style={styles.h2}>la magie</GradientText>
            <Text style={styles.h2}> ?</Text>
          </View>
          <Text style={styles.sub}>
            Demandez votre devis gratuit — dites-nous la date, le thème et la mascotte choisie, on
            s'occupe du reste.
          </Text>
          <View style={{ gap: 10, marginTop: 18 }}>
            <GradientButton label="💬 Devis WhatsApp" onPress={() => openWhatsApp()} />
            <Pressable style={styles.contactGhost} onPress={openPhone}>
              <Text style={styles.contactGhostText}>📞 {brand.phoneDisplay}</Text>
            </Pressable>
            <Pressable style={styles.contactGhost} onPress={openEmail}>
              <Text style={styles.contactGhostText}>✉️ {brand.email}</Text>
            </Pressable>
          </View>
          <Text style={styles.contactNote}>
            Royal Dream Events · Bruxelles, Belgique · Réponse en quelques minutes
          </Text>
        </LinearGradient>
      </View>
    </View>
  );
}

/* ------------------------------- FOOTER ------------------------------ */
export function Footer() {
  return (
    <View style={styles.footer}>
      <Image source={{ uri: brand.logo }} style={styles.footerLogo} resizeMode="contain" />
      <Text style={styles.footerText}>
        © 2026 Royal Dream Events — Location châteaux gonflables & mascottes Bruxelles.
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  section: { paddingVertical: 44 },
  padX: { paddingHorizontal: H_PAD },
  center: { alignItems: 'center' },
  centerText: { textAlign: 'center' },
  row: { flexDirection: 'row', alignItems: 'center', flexWrap: 'wrap', justifyContent: 'center' },

  h2: { color: colors.text, fontFamily: fonts.display, fontSize: 30, lineHeight: 36 },
  h2b: { color: colors.text, fontFamily: fonts.display, fontSize: 22, lineHeight: 28 },
  sub: {
    color: colors.textSoft,
    fontFamily: fonts.body,
    fontSize: 15,
    lineHeight: 23,
    marginTop: 12,
  },

  goldEyebrow: {
    backgroundColor: 'rgba(251,191,36,0.18)',
    borderRadius: radius.pill,
    paddingHorizontal: 16,
    paddingVertical: 7,
    marginBottom: 12,
  },
  goldEyebrowText: {
    color: colors.gold, fontFamily: fonts.bodyBold, fontSize: 11,
    letterSpacing: 0.8, textTransform: 'uppercase', textAlign: 'center',
  },
  magicEyebrow: {
    color: colors.violet, fontFamily: fonts.bodyBold, fontSize: 13,
    letterSpacing: 1, textTransform: 'uppercase', marginBottom: 8,
  },
  goldLabel: {
    color: colors.gold, fontFamily: fonts.bodyBold, fontSize: 13,
    letterSpacing: 1.2, textTransform: 'uppercase', marginBottom: 8,
  },
  magicLabel: {
    color: colors.violet, fontFamily: fonts.bodyBold, fontSize: 13,
    letterSpacing: 1.2, textTransform: 'uppercase', marginBottom: 8,
  },

  mascotImg: { width: '100%', height: 240, marginTop: 24 },
  pricePill: {
    flexDirection: 'row', alignItems: 'center', gap: 10, alignSelf: 'center',
    backgroundColor: 'rgba(255,215,0,0.12)', borderWidth: 1, borderColor: 'rgba(255,215,0,0.35)',
    borderRadius: radius.pill, paddingHorizontal: 22, paddingVertical: 10, marginBottom: 22,
  },
  priceDot: { width: 8, height: 8, borderRadius: 4, backgroundColor: colors.goldBright },
  pricePillText: { color: colors.goldBright, fontFamily: fonts.bodyBold, fontSize: 13 },
  pricePillSoft: { color: 'rgba(255,215,0,0.6)', fontFamily: fonts.bodySemi },

  mascotStatsCard: {
    flexDirection: 'row', flexWrap: 'wrap', justifyContent: 'center',
    backgroundColor: 'rgba(180,50,220,0.06)', borderWidth: 1, borderColor: 'rgba(255,215,0,0.15)',
    borderRadius: radius.md, paddingVertical: 18,
  },
  mascotStat: { alignItems: 'center', paddingHorizontal: 18, paddingVertical: 6, width: '25%' },
  mascotStatBorder: { borderRightWidth: 1, borderRightColor: 'rgba(255,215,0,0.12)' },
  mascotStatValue: { fontFamily: fonts.serif, fontSize: 24, color: colors.goldBright },
  mascotStatLabel: {
    fontSize: 10, color: 'rgba(255,255,255,0.45)', fontFamily: fonts.bodyBold,
    letterSpacing: 0.5, textTransform: 'uppercase', marginTop: 3, textAlign: 'center',
  },
  mascotStatNote: { fontSize: 10, color: 'rgba(255,215,0,0.45)', marginTop: 1, textAlign: 'center' },

  packCard: { flexDirection: 'row', alignItems: 'center', gap: 14, padding: 18, marginTop: 28 },
  packEmoji: { fontSize: 38 },
  packBody: { flex: 1 },
  packTitle: { color: colors.text, fontFamily: fonts.displaySemi, fontSize: 17 },
  packText: { color: colors.textSoft, fontFamily: fonts.body, fontSize: 13, marginTop: 3 },
  bold: { fontFamily: fonts.bodyBold, color: colors.text },
  packBtn: { display: 'none' },

  grid: { flexDirection: 'row', flexWrap: 'wrap', gap: GRID_GAP, marginTop: 22 },

  castleCard: {
    width: CARD_W, borderRadius: radius.lg, overflow: 'hidden',
    backgroundColor: colors.card, ...shadows.card,
  },
  castleBadge: {
    position: 'absolute', top: 10, left: 10, zIndex: 2,
    borderRadius: radius.pill, paddingHorizontal: 10, paddingVertical: 3,
  },
  castleBadgeText: {
    color: '#3a2600', fontFamily: fonts.bodyBold, fontSize: 9,
    letterSpacing: 0.5, textTransform: 'uppercase',
  },
  castleImgWrap: {
    aspectRatio: 1, backgroundColor: 'rgba(255,255,255,0.04)', padding: 8,
  },
  castleImg: { width: '100%', height: '100%' },
  castleInfo: { padding: 12 },
  castleCat: {
    color: colors.violet, fontFamily: fonts.bodyBold, fontSize: 10,
    letterSpacing: 0.8, textTransform: 'uppercase',
  },
  castleName: { color: colors.text, fontFamily: fonts.displaySemi, fontSize: 15, marginTop: 2 },
  castlePriceRow: {
    flexDirection: 'row', alignItems: 'flex-end', justifyContent: 'space-between', marginTop: 8,
  },
  castlePrice: { color: colors.gold, fontFamily: fonts.bodyBold, fontSize: 20 },
  castlePer: { color: colors.textMuted, fontFamily: fonts.bodyReg, fontSize: 11 },
  castleArrow: { color: colors.violet, fontSize: 16 },

  whyCard: { width: CARD_W, padding: 16 },
  whyEmoji: { fontSize: 30, marginBottom: 8 },
  whyTitle: { color: colors.text, fontFamily: fonts.displaySemi, fontSize: 16, lineHeight: 20 },
  whyText: { color: colors.textSoft, fontFamily: fonts.body, fontSize: 13, lineHeight: 19, marginTop: 6 },

  trustCard: { width: CARD_W, flexDirection: 'row', alignItems: 'center', gap: 10, padding: 14 },
  trustEmoji: { fontSize: 22 },
  trustText: { flex: 1, color: colors.text, fontFamily: fonts.bodySemi, fontSize: 12, lineHeight: 16 },

  reviewCard: { padding: 18 },
  stars: { color: colors.gold, fontSize: 14, letterSpacing: 2 },
  reviewText: { color: colors.text, fontFamily: fonts.body, fontSize: 14, lineHeight: 21, marginTop: 8 },
  reviewAuthor: { color: colors.textMuted, fontFamily: fonts.bodyBold, fontSize: 12, marginTop: 12 },

  aboutImgWrap: { aspectRatio: 4 / 3, borderRadius: radius.lg, overflow: 'hidden' },
  aboutImg: { width: '100%', height: '100%' },

  zoneWrap: {
    flexDirection: 'row', flexWrap: 'wrap', gap: 8, justifyContent: 'center', marginTop: 24,
  },
  zoneChip: { paddingHorizontal: 14, paddingVertical: 8, borderRadius: radius.pill },
  zoneText: { color: colors.text, fontFamily: fonts.body, fontSize: 13 },

  faqCard: { padding: 18 },
  faqHead: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: 12 },
  faqQ: { flex: 1, color: colors.text, fontFamily: fonts.displaySemi, fontSize: 15, lineHeight: 21 },
  faqPlus: { color: colors.gold, fontSize: 24, fontFamily: fonts.body },
  faqA: { color: colors.textSoft, fontFamily: fonts.body, fontSize: 14, lineHeight: 22, marginTop: 12 },

  contactCard: { borderRadius: radius.xl, overflow: 'hidden', ...shadows.magic },
  contactInner: { padding: 24 },
  contactGhost: {
    backgroundColor: colors.glass, borderWidth: 1, borderColor: colors.border,
    borderRadius: radius.pill, paddingVertical: 14, alignItems: 'center',
  },
  contactGhostText: { color: colors.text, fontFamily: fonts.bodySemi, fontSize: 15 },
  contactNote: { color: colors.textMuted, fontFamily: fonts.body, fontSize: 12, marginTop: 16 },

  footer: {
    borderTopWidth: 1, borderTopColor: 'rgba(255,255,255,0.08)',
    paddingVertical: 28, paddingHorizontal: H_PAD, alignItems: 'center', gap: 12,
  },
  footerLogo: { height: 36, width: 120 },
  footerText: { color: colors.textMuted, fontFamily: fonts.body, fontSize: 12, textAlign: 'center' },
});
