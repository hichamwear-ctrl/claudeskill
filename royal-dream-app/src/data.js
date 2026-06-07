// All textual + media content mirrored from happy-jump-analysis.lovable.app
// Images are referenced by their live URLs so they load on the phone.
export const SITE = 'https://happy-jump-analysis.lovable.app';
const img = (p) => `${SITE}${p}`;

export const brand = {
  name: 'Royal Dream Events',
  logo: img('/assets/logo-CFwaxIjh.png'),
  phone: '+32000000000',
  phoneDisplay: '+32 0 00 00 00',
  email: 'hello@royaldream.events',
  whatsapp: '32000000000',
  city: 'Bruxelles, Belgique',
};

export const heroImage = img('/assets/hero-castle-D4F1QMiT.jpg');
export const mascotGroupImage = img('/assets/char-heroes-group-Bwbqe3pn.png');
export const teamImage = img('/__l5e/assets-v1/7a828c22-b4ab-416a-bd80-44115014dc62/team-royal-dream.png');
export const contactBgImage = img('/assets/cosplay-CZFvk3bX.jpg');

export const navLinks = [
  { label: 'Mascottes ✨', key: 'mascottes' },
  { label: 'Châteaux', key: 'chateaux' },
  { label: 'Zones', key: 'zones' },
  { label: 'FAQ', key: 'faq' },
  { label: 'Contact', key: 'contact' },
];

export const languages = ['FR', 'NL', 'EN'];

export const heroStats = [
  { value: '10', label: 'Châteaux' },
  { value: '4', label: 'Mascottes' },
  { value: '20km', label: 'Livraison' },
];

export const heroFloatBadges = [
  { emoji: '🎂', label: 'Anniversaires' },
  { emoji: '🎉', label: 'Fêtes inoubliables' },
  { emoji: '👑', label: 'Royal' },
];

export const mascotStats = [
  { value: '89,99€', label: 'Par heure', note: 'à partir de' },
  { value: '4', label: 'Mascottes', note: 'disponibles' },
  { value: '1h', label: 'Minimum', note: 'sans maximum' },
  { value: '🇧🇪', label: 'Belgique', note: 'partout sur demande' },
];

export const castles = [
  {
    name: 'Royal Castle', category: 'Royal', price: 220, badge: 'Best-seller',
    image: img('/assets/castle-royal-CWtCSKGZ.jpg'),
    desc: "Un château royal majestueux avec tours et créneaux dorés. L'effet « wow » garanti pour les petits princes et princesses.",
  },
  {
    name: 'Princess Palace', category: 'Princesse', price: 190, badge: null,
    image: img('/assets/castle-princess-B0Ck1q8D.jpg'),
    desc: 'Un palais de princesse rose et féérique, parfait pour un anniversaire digne des contes de fées.',
  },
  {
    name: 'Ice Queen', category: 'Reine des glaces', price: 195, badge: 'Magique',
    image: img('/assets/castle-frozen-CPaOTz86.jpg'),
    desc: 'Plongez dans un univers glacé digne de la reine des neiges. Toboggan et aire de saut tout en cristal.',
  },
  {
    name: 'Super Hero', category: 'Super-héros', price: 185, badge: null,
    image: img('/assets/castle-hero-CYc4nApb.jpg'),
    desc: 'Un repaire de super-héros pour les petits justiciers en herbe. Action et sauts garantis.',
  },
  {
    name: 'Unicorn Rainbow', category: 'Licorne', price: 190, badge: null,
    image: img('/assets/castle-unicorn-BRWVs6SF.jpg'),
    desc: 'Licornes et arcs-en-ciel pour un anniversaire haut en couleurs et plein de magie.',
  },
  {
    name: 'Pirate Ship', category: 'Pirate', price: 180, badge: null,
    image: img('/assets/castle-pirate-BNtGoJdI.jpg'),
    desc: "À l'abordage ! Un navire pirate gonflable avec mât et toboggan pour de folles aventures.",
  },
  {
    name: 'T-Rex Adventure', category: 'Dinosaure', price: 185, badge: null,
    image: img('/assets/castle-dino-CeWnPVYq.jpg'),
    desc: 'Un monde de dinosaures avec T-Rex géant. Pour les petits explorateurs intrépides.',
  },
  {
    name: 'Jungle Safari', category: 'Jungle', price: 180, badge: null,
    image: img('/assets/castle-jungle-CpLMOWYL.jpg'),
    desc: 'Partez en safari au cœur de la jungle, entre lianes, animaux et toboggan tropical.',
  },
  {
    name: 'Galaxy Quest', category: 'Espace', price: 195, badge: 'Nouveau',
    image: img('/assets/castle-space-CnfQC6qR.jpg'),
    desc: "Direction l'espace ! Fusées, planètes et étoiles pour une fête interstellaire.",
  },
  {
    name: 'Rainbow Slide', category: 'Toboggan', price: 200, badge: null,
    image: img('/assets/castle-rainbow-Dk0a2AQT.jpg'),
    desc: 'Un immense toboggan arc-en-ciel pour des descentes à sensations et des fous rires.',
  },
];

export const castleIncludes = [
  '🚚 Livraison & installation incluses',
  '🛡️ Certifié aux normes européennes',
  '🧼 Désinfecté avant chaque fête',
  '🌧️ Annulation météo 100% gratuite',
];

export const whyCards = [
  { emoji: '🚚', title: 'Livraison & installation', text: 'On livre, on installe, on récupère partout à Bruxelles.' },
  { emoji: '🎭', title: 'Mascottes en cosplay', text: "Souris magique, héros araignée, reine des glaces — l'effet wow garanti." },
  { emoji: '🛡️', title: 'Sécurité certifiée', text: 'Tous nos châteaux respectent les normes européennes.' },
  { emoji: '🌧️', title: 'Annulation météo', text: 'Mauvais temps le jour J ? Annulation 100% gratuite.' },
  { emoji: '📍', title: 'Livraison gratuite', text: 'Dans toute Bruxelles-Capitale (20 km). Au-delà sur demande.' },
  { emoji: '💬', title: 'Réservation facile', text: 'WhatsApp, téléphone ou formulaire — réponse en quelques minutes.' },
];

export const trustBadges = [
  { emoji: '🛡️', text: 'Assuré en responsabilité civile' },
  { emoji: '✅', text: 'Châteaux certifiés normes européennes' },
  { emoji: '🧼', text: 'Désinfectés après chaque utilisation' },
  { emoji: '🚚', text: 'Livraison & installation incluses' },
];

export const reviews = [
  { text: 'Anniversaire de notre fille parfait ! Le château Princess Palace était magnifique et la Reine des glaces a fait sensation.', author: 'Sarah', city: 'Uccle' },
  { text: "Livraison à l'heure, installation rapide. Les enfants n'ont pas voulu quitter le château gonflable. Je recommande à 100%.", author: 'Mehdi', city: 'Anderlecht' },
  { text: 'Service au top, équipe adorable. La mascotte Spider-Man était hyper pro avec les enfants. Merci Royal Dream !', author: 'Camille', city: 'Ixelles' },
  { text: 'Réservation facile via WhatsApp, prix corrects, matériel impeccable. On refait l\'année prochaine.', author: 'Julien', city: 'Waterloo' },
];

export const aboutParagraphs = [
  "Royal Dream Events, c'est une petite équipe basée à Bruxelles qui transforme les anniversaires d'enfants en souvenirs féériques. Nos châteaux gonflables sont entretenus avec soin, nos mascottes sont jouées par des artistes formés, et notre seul objectif : faire briller les yeux de vos enfants.",
  'Nous intervenons partout à Bruxelles, dans le Brabant Wallon et sur toute la Belgique francophone.',
];

export const zones = [
  'Bruxelles', 'Anderlecht', 'Uccle', 'Ixelles', 'Schaerbeek', 'Woluwe',
  'Etterbeek', 'Forest', 'Saint-Gilles', 'Jette', 'Auderghem', 'Evere',
  'Waterloo', "Braine-l'Alleud", 'Wavre', 'Nivelles', 'Louvain-la-Neuve',
  'Namur', 'Charleroi', 'Mons', 'Liège',
];

export const faq = [
  {
    q: "Combien coûte la location d'un château gonflable à Bruxelles ?",
    a: 'Nos châteaux gonflables sont disponibles à partir de 180€ la journée à Bruxelles, livraison et installation incluses dans un rayon de 20 km.',
  },
  {
    q: 'Livrez-vous dans toute la région bruxelloise ?',
    a: 'Oui, nous livrons à Anderlecht, Uccle, Ixelles, Schaerbeek, Woluwe, Etterbeek et toutes les communes de Bruxelles-Capitale, ainsi que dans le Brabant Wallon (Waterloo, Wavre, Nivelles, Louvain-la-Neuve).',
  },
  {
    q: "Combien de temps dure l'animation mascotte ?",
    a: 'Nos animations mascotte sont facturées 89,99€ / heure (minimum 1h) et peuvent être prolongées sur demande pour des fêtes plus longues.',
  },
  {
    q: 'Quels personnages sont disponibles ?',
    a: 'Le duo souris magique (Mickey & Minnie style), le héros araignée (Spider-Man style), la reine des glaces (Frozen style) et le petit bleu d\'Hawaï (Stitch style). Nos artistes sont costumés professionnellement.',
  },
  {
    q: "Combien de temps à l'avance faut-il réserver ?",
    a: 'Pour garantir votre date, nous recommandons de réserver 2 à 4 semaines à l\'avance, surtout pour les week-ends et la période avril-septembre.',
  },
  {
    q: 'Les mascottes peuvent-elles se déplacer à domicile ?',
    a: 'Absolument. Nos mascottes interviennent à domicile, en salle ou en extérieur partout à Bruxelles et en Belgique francophone.',
  },
];
