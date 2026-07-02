import type { ExpoConfig } from 'expo/config';

/**
 * Configuration Expo dynamique.
 * Les valeurs sensibles ne sont JAMAIS ici : l'app ne lit que des variables
 * publiques `EXPO_PUBLIC_*` au runtime (cf. env.d.ts / .env.example).
 */
const config: ExpoConfig = {
  name: '[NOM_PRODUIT]',
  slug: 'mobile',
  version: '1.0.0',
  scheme: 'app', // deep links : app://mission/{id}, app://health…
  orientation: 'portrait',
  icon: './assets/icon.png',
  userInterfaceStyle: 'light', // thème clair en V1 (dark-ready côté design system)
  ios: {
    supportsTablet: true,
    bundleIdentifier: 'com.example.mobile',
    infoPlist: {
      NSLocationWhenInUseUsageDescription:
        'La localisation est utilisée uniquement pendant une mission active pour le suivi en temps réel.',
      NSCameraUsageDescription:
        'La caméra sert à joindre des photos à votre demande ou un ticket de course.',
      NSPhotoLibraryUsageDescription:
        'La galerie sert à joindre des photos à votre demande ou un ticket de course.',
    },
  },
  android: {
    package: 'com.example.mobile',
    adaptiveIcon: {
      backgroundColor: '#E6F4FE',
      foregroundImage: './assets/android-icon-foreground.png',
      backgroundImage: './assets/android-icon-background.png',
      monochromeImage: './assets/android-icon-monochrome.png',
    },
    predictiveBackGestureEnabled: false,
    permissions: ['ACCESS_FINE_LOCATION', 'ACCESS_COARSE_LOCATION', 'CAMERA'],
  },
  web: {
    favicon: './assets/favicon.png',
  },
  plugins: [
    'expo-router',
    'expo-secure-store',
    [
      'expo-location',
      {
        locationWhenInUsePermission:
          'La localisation est utilisée uniquement pendant une mission active pour le suivi en temps réel.',
      },
    ],
    'expo-notifications',
    [
      'expo-image-picker',
      {
        photosPermission:
          'La galerie sert à joindre des photos à votre demande ou un ticket de course.',
        cameraPermission:
          'La caméra sert à joindre des photos à votre demande ou un ticket de course.',
      },
    ],
  ],
};

export default config;
