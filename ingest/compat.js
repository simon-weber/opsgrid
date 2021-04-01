function isNode() {
  return (typeof process.release !== 'undefined') && (process.release.name === 'node');
}

module.exports = { isNode };
