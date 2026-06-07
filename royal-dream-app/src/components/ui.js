import React from 'react';
import { Text, View, Pressable, StyleSheet } from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import MaskedView from '@react-native-masked-view/masked-view';
import { colors, fonts, radius, shadows, magicGradient } from '../theme';

// Text filled with a left-to-right gradient (matches `.text-gradient-*` on the site).
export function GradientText({ children, gradient, style }) {
  return (
    <MaskedView
      maskElement={
        <Text style={[style, { backgroundColor: 'transparent' }]}>{children}</Text>
      }
    >
      <LinearGradient colors={gradient} start={{ x: 0, y: 0 }} end={{ x: 1, y: 0.4 }}>
        <Text style={[style, { opacity: 0 }]}>{children}</Text>
      </LinearGradient>
    </MaskedView>
  );
}

// Frosted-glass surface (matches `.glass`).
export function Glass({ children, style }) {
  return <View style={[styles.glass, style]}>{children}</View>;
}

// Pill button with a gradient fill.
export function GradientButton({ label, onPress, gradient = magicGradient, textColor = '#fff', style, textStyle }) {
  return (
    <Pressable onPress={onPress} style={({ pressed }) => [{ transform: [{ scale: pressed ? 0.97 : 1 }] }, style]}>
      <LinearGradient
        colors={gradient}
        start={{ x: 0, y: 0 }}
        end={{ x: 1, y: 1 }}
        style={[styles.btn, shadows.magic]}
      >
        <Text style={[styles.btnText, { color: textColor }, textStyle]}>{label}</Text>
      </LinearGradient>
    </Pressable>
  );
}

// Outlined / glass pill button (matches `.glass` ghost buttons).
export function GhostButton({ label, onPress, style, textStyle }) {
  return (
    <Pressable
      onPress={onPress}
      style={({ pressed }) => [styles.ghostBtn, { opacity: pressed ? 0.8 : 1 }, style]}
    >
      <Text style={[styles.ghostText, textStyle]}>{label}</Text>
    </Pressable>
  );
}

// Small uppercase eyebrow label.
export function Eyebrow({ children, color = colors.gold, style }) {
  return <Text style={[styles.eyebrow, { color }, style]}>{children}</Text>;
}

// Gold-tinted rounded chip used for section eyebrows.
export function GoldChip({ children, style }) {
  return (
    <View style={[styles.goldChip, style]}>
      <Text style={styles.goldChipText}>{children}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  glass: {
    backgroundColor: colors.glass,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.lg,
  },
  btn: {
    borderRadius: radius.pill,
    paddingVertical: 14,
    paddingHorizontal: 24,
    alignItems: 'center',
    justifyContent: 'center',
  },
  btnText: {
    fontFamily: fonts.bodyBold,
    fontSize: 15,
  },
  ghostBtn: {
    borderRadius: radius.pill,
    paddingVertical: 14,
    paddingHorizontal: 24,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: colors.glass,
    borderWidth: 1,
    borderColor: colors.border,
  },
  ghostText: {
    fontFamily: fonts.bodySemi,
    fontSize: 15,
    color: colors.text,
  },
  eyebrow: {
    fontFamily: fonts.bodyBold,
    fontSize: 12,
    letterSpacing: 1.2,
    textTransform: 'uppercase',
  },
  goldChip: {
    alignSelf: 'center',
    backgroundColor: 'rgba(251,191,36,0.18)',
    borderRadius: radius.pill,
    paddingHorizontal: 16,
    paddingVertical: 7,
  },
  goldChipText: {
    color: colors.gold,
    fontFamily: fonts.bodyBold,
    fontSize: 11,
    letterSpacing: 1,
    textTransform: 'uppercase',
    textAlign: 'center',
  },
});
