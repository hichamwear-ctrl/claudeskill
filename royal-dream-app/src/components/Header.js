import React, { useState } from 'react';
import { View, Text, Image, Pressable, Modal, StyleSheet } from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { colors, fonts, radius, magicGradient, shadows } from '../theme';
import { brand, navLinks, languages } from '../data';
import { Glass } from './ui';

export default function Header({ insetTop, onNavigate, lang, setLang }) {
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <View style={[styles.wrap, { paddingTop: insetTop + 8 }]} pointerEvents="box-none">
      <Glass style={styles.bar}>
        <Pressable onPress={() => onNavigate('top')} style={styles.logoWrap} hitSlop={8}>
          <Image source={{ uri: brand.logo }} style={styles.logo} resizeMode="contain" />
        </Pressable>

        <View style={styles.right}>
          {/* Language switch — FR / NL / EN */}
          <View style={styles.langGroup}>
            {languages.map((l) =>
              l === lang ? (
                <LinearGradient
                  key={l}
                  colors={magicGradient}
                  start={{ x: 0, y: 0 }}
                  end={{ x: 1, y: 1 }}
                  style={styles.langActive}
                >
                  <Text style={styles.langActiveText}>{l}</Text>
                </LinearGradient>
              ) : (
                <Pressable key={l} onPress={() => setLang(l)} style={styles.langBtn}>
                  <Text style={styles.langText}>{l}</Text>
                </Pressable>
              )
            )}
          </View>

          <Pressable onPress={() => onNavigate('contact')}>
            <LinearGradient
              colors={magicGradient}
              start={{ x: 0, y: 0 }}
              end={{ x: 1, y: 1 }}
              style={[styles.reserve, shadows.magic]}
            >
              <Text style={styles.reserveText}>Réserver</Text>
            </LinearGradient>
          </Pressable>

          <Pressable onPress={() => setMenuOpen(true)} hitSlop={8} style={styles.menuBtn}>
            <Text style={styles.menuIcon}>☰</Text>
          </Pressable>
        </View>
      </Glass>

      {/* Navigation drawer */}
      <Modal visible={menuOpen} transparent animationType="fade" onRequestClose={() => setMenuOpen(false)}>
        <Pressable style={styles.menuOverlay} onPress={() => setMenuOpen(false)}>
          <Glass style={styles.menuPanel}>
            <Text style={styles.menuTitle}>Navigation</Text>
            {navLinks.map((link) => (
              <Pressable
                key={link.key}
                style={styles.menuItem}
                onPress={() => {
                  setMenuOpen(false);
                  setTimeout(() => onNavigate(link.key), 220);
                }}
              >
                <Text style={styles.menuItemText}>{link.label}</Text>
              </Pressable>
            ))}
          </Glass>
        </Pressable>
      </Modal>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    zIndex: 50,
    paddingHorizontal: 14,
  },
  bar: {
    borderRadius: radius.pill,
    paddingVertical: 8,
    paddingHorizontal: 12,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    backgroundColor: 'rgba(11,11,34,0.72)',
    ...shadows.card,
  },
  logoWrap: { flexShrink: 0 },
  logo: { height: 36, width: 120 },
  right: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  langGroup: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 2,
    borderRadius: radius.pill,
    borderWidth: 1,
    borderColor: 'rgba(167,139,250,0.4)',
    backgroundColor: 'rgba(31,20,56,0.8)',
    gap: 1,
  },
  langActive: {
    paddingHorizontal: 9,
    paddingVertical: 4,
    borderRadius: radius.pill,
  },
  langActiveText: { color: '#fff', fontFamily: fonts.bodyBold, fontSize: 10, letterSpacing: 1 },
  langBtn: { paddingHorizontal: 9, paddingVertical: 4, borderRadius: radius.pill },
  langText: { color: 'rgba(247,248,252,0.7)', fontFamily: fonts.bodyBold, fontSize: 10, letterSpacing: 1 },
  reserve: { paddingHorizontal: 16, paddingVertical: 9, borderRadius: radius.pill },
  reserveText: { color: '#fff', fontFamily: fonts.bodyBold, fontSize: 13 },
  menuBtn: { paddingHorizontal: 4 },
  menuIcon: { color: colors.text, fontSize: 22, marginTop: -2 },
  menuOverlay: {
    flex: 1,
    backgroundColor: 'rgba(7,7,26,0.6)',
    justifyContent: 'flex-start',
    alignItems: 'flex-end',
    paddingTop: 90,
    paddingHorizontal: 16,
  },
  menuPanel: {
    width: 230,
    padding: 12,
    backgroundColor: 'rgba(20,18,72,0.96)',
  },
  menuTitle: {
    color: colors.textMuted,
    fontFamily: fonts.bodyBold,
    fontSize: 11,
    letterSpacing: 1.2,
    textTransform: 'uppercase',
    marginBottom: 6,
    marginLeft: 6,
  },
  menuItem: { paddingVertical: 12, paddingHorizontal: 10, borderRadius: radius.md },
  menuItemText: { color: colors.text, fontFamily: fonts.bodySemi, fontSize: 16 },
});
