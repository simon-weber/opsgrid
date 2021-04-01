const path = require('path');
const CopyPlugin = require('copy-webpack-plugin');

module.exports = {
  mode: 'development',
  entry: {
    lib: './lib.js',
  },
  output:
  {
    filename: '[name].bundle.js',
    path: path.resolve(__dirname, 'dist'),
    libraryTarget: 'var',
    library: 'AppLib',
  },
  module:
  {
    rules: [
      {
        test: /\.js$/,
        exclude: /(node_modules|bower_components)/,
        use: {
          loader: 'babel-loader',
          options: {
            presets: [
              [
                '@babel/preset-env',
                {
                  useBuiltIns: 'usage',
                  corejs: '3.0.0',
                },
              ],
            ],
          },
        },
      },
      {
        test: /\.js$/,
        exclude: /(node_modules|bower_components)/,
        loader: 'string-replace-loader',
        options: {
          multiple: [
            { search: 'module.exports =', replace: 'export' },
            { flags: 'g', search: 'async ', replace: '' },
            { flags: 'g', search: 'await ', replace: '' },
            { flags: 'mg', search: '^.*// webpack-omit$', replace: '' },
          ],
        },
      },
    ],
  },
  plugins: [
    new CopyPlugin([
      'gas.js',
      'appsscript.json',
      '.clasp.json',
    ]),
  ],
};
