function secureEquals_(left, right) {
  left = String(left || '');
  right = String(right || '');
  const max = Math.max(left.length, right.length);
  let diff = left.length ^ right.length;
  for (let i = 0; i < max; i += 1) {
    diff |= (left.charCodeAt(i % Math.max(1, left.length)) || 0) ^
      (right.charCodeAt(i % Math.max(1, right.length)) || 0);
  }
  return diff === 0;
}

function authorized_(supplied, expected) {
  return supplied && expected && secureEquals_(supplied, expected);
}

function unauthorized_() {
  return jsonOutput_({ok: false, error: 'unauthorized'});
}
