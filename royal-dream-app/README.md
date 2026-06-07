# Royal Dream Events — Application mobile

Application mobile (React Native + Expo) reproduisant **fidèlement** le site
[happy-jump-analysis.lovable.app](https://happy-jump-analysis.lovable.app) :
location de châteaux gonflables & mascottes à Bruxelles.

Toutes les sections du site sont présentes :

- En-tête avec logo, sélecteur de langue **FR / NL / EN** et bouton **Réserver**
- Menu de navigation (☰ → Mascottes, Châteaux, Zones, FAQ, Contact)
- **Hero** « La magie arrive chez vous » + statistiques (10 châteaux · 4 mascottes · 20 km)
- **Mascottes** : prix 89,99€/h, stats, **Pack Magique** (Château + Mascotte)
- **10 châteaux** cliquables (Royal Castle, Princess Palace, Ice Queen, Super Hero,
  Unicorn Rainbow, Pirate Ship, T-Rex Adventure, Jungle Safari, Galaxy Quest, Rainbow Slide)
  → fiche détaillée + réservation WhatsApp
- **Pourquoi Royal Dream** (6 atouts) + badges de confiance
- **Avis clients** (4 témoignages 5★)
- **Qui sommes-nous** (équipe locale)
- **Zones desservies** (21 communes)
- **FAQ** (6 questions, accordéon)
- **Contact** (WhatsApp, téléphone, e-mail) + bouton WhatsApp flottant
- Pied de page

> Les images proviennent directement du site en ligne (chargées depuis Internet).

---

## 📲 Tester sur votre iPhone (le plus simple)

### 1. Installez **Expo Go** sur l'iPhone
App Store → cherchez **« Expo Go »** → installez (gratuit).

### 2. Sur un ordinateur (Mac ou PC), installez Node.js
Téléchargez Node.js LTS depuis https://nodejs.org si ce n'est pas déjà fait.

### 3. Récupérez ce dossier et lancez le serveur
```bash
cd royal-dream-app
npm install
npx expo start
```
Un **QR code** s'affiche dans le terminal.

### 4. Scannez le QR code avec l'iPhone
Ouvrez l'app **Appareil photo** de l'iPhone, visez le QR code, touchez la
notification → l'application s'ouvre dans **Expo Go**. 🎉

> ⚠️ L'iPhone et l'ordinateur doivent être sur le **même réseau Wi-Fi**.
> Si ça ne marche pas (Wi-Fi public, réseaux séparés), lancez plutôt :
> ```bash
> npx expo start --tunnel
> ```
> (installe un tunnel sécurisé, fonctionne partout).

---

## Notes techniques

- **Expo SDK 52** / React Native 0.76.
- Si Expo Go affiche une erreur de version de SDK (parce que votre Expo Go est
  plus récent), mettez le projet à jour :
  ```bash
  npm install expo@latest
  npx expo install --fix
  ```
- Pour transformer plus tard en vraie app installable (.ipa) sur l'App Store :
  `npx eas build -p ios` (compte Expo + Apple Developer requis).
