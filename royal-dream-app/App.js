import React, { useRef, useState } from 'react';
import { View, ScrollView, ActivityIndicator, StyleSheet } from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { LinearGradient } from 'expo-linear-gradient';
import { SafeAreaProvider, useSafeAreaInsets } from 'react-native-safe-area-context';
import { useFonts } from 'expo-font';
import { Fredoka_500Medium, Fredoka_600SemiBold, Fredoka_700Bold } from '@expo-google-fonts/fredoka';
import {
  Quicksand_400Regular, Quicksand_500Medium, Quicksand_600SemiBold, Quicksand_700Bold,
} from '@expo-google-fonts/quicksand';
import { PlayfairDisplay_600SemiBold, PlayfairDisplay_700Bold } from '@expo-google-fonts/playfair-display';

import { colors, bgGradient } from './src/theme';
import Header from './src/components/Header';
import Hero from './src/components/Hero';
import {
  Mascottes, Chateaux, Pourquoi, TrustBadges, Avis,
  QuiSommesNous, Zones, Faq, Contact, Footer,
} from './src/components/Sections';
import CastleModal from './src/components/CastleModal';
import WhatsAppButton from './src/components/WhatsAppButton';
import { openWhatsApp } from './src/components/links';

function Root() {
  const insets = useSafeAreaInsets();
  const scrollRef = useRef(null);
  const sectionY = useRef({});
  const [castle, setCastle] = useState(null);
  const [lang, setLang] = useState('FR');

  const register = (key) => (e) => {
    sectionY.current[key] = e.nativeEvent.layout.y;
  };
  const navigate = (key) => {
    const y = key === 'top' ? 0 : sectionY.current[key];
    if (y != null) scrollRef.current?.scrollTo({ y: Math.max(0, y - 70), animated: true });
  };

  const reserve = (label) => openWhatsApp(
    label
      ? `Bonjour, je souhaite réserver : ${label}. Pouvez-vous me donner les disponibilités ?`
      : undefined
  );

  return (
    <LinearGradient colors={bgGradient} style={styles.flex}>
      <StatusBar style="light" />
      <ScrollView
        ref={scrollRef}
        style={styles.flex}
        contentContainerStyle={{ paddingBottom: insets.bottom + 24 }}
        showsVerticalScrollIndicator={false}
      >
        <Hero
          topPad={insets.top + 88}
          onReserve={() => navigate('chateaux')}
          onQuote={() => reserve('Devis gratuit')}
        />
        <View onLayout={register('mascottes')}><Mascottes onReserve={reserve} /></View>
        <View onLayout={register('chateaux')}><Chateaux onCastlePress={setCastle} /></View>
        <View onLayout={register('pourquoi')}><Pourquoi /></View>
        <TrustBadges />
        <View onLayout={register('avis')}><Avis /></View>
        <View onLayout={register('qui-sommes-nous')}><QuiSommesNous /></View>
        <View onLayout={register('zones')}><Zones /></View>
        <View onLayout={register('faq')}><Faq /></View>
        <View onLayout={register('contact')}><Contact /></View>
        <Footer />
      </ScrollView>

      <Header
        insetTop={insets.top}
        onNavigate={navigate}
        lang={lang}
        setLang={setLang}
      />
      <WhatsAppButton bottom={insets.bottom + 18} />
      <CastleModal castle={castle} onClose={() => setCastle(null)} />
    </LinearGradient>
  );
}

export default function App() {
  const [fontsLoaded] = useFonts({
    Fredoka_500Medium, Fredoka_600SemiBold, Fredoka_700Bold,
    Quicksand_400Regular, Quicksand_500Medium, Quicksand_600SemiBold, Quicksand_700Bold,
    PlayfairDisplay_600SemiBold, PlayfairDisplay_700Bold,
  });

  return (
    <SafeAreaProvider>
      {fontsLoaded ? (
        <Root />
      ) : (
        <View style={[styles.flex, styles.loading]}>
          <ActivityIndicator color={colors.gold} size="large" />
        </View>
      )}
    </SafeAreaProvider>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  loading: { backgroundColor: colors.bgDeep, alignItems: 'center', justifyContent: 'center' },
});
