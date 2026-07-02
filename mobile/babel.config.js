module.exports = function (api) {
  api.cache(true);
  return {
    presets: ['babel-preset-expo'],
    // Reanimated 4 : le plugin de worklets DOIT rester le dernier.
    plugins: ['react-native-worklets/plugin'],
  };
};
