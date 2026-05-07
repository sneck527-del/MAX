// 简单的 XOR + Base64 混淆，防止 API Key 明文存储在 localStorage
var Encryption = (function() {
  var KEY = 'ark_design_2024';

  function _xor(str, key) {
    var result = '';
    for (var i = 0; i < str.length; i++) {
      result += String.fromCharCode(str.charCodeAt(i) ^ key.charCodeAt(i % key.length));
    }
    return result;
  }

  function _encode(str) {
    try { return btoa(unescape(encodeURIComponent(_xor(str, KEY)))); } catch(e) { return str; }
  }

  function _decode(str) {
    try { return _xor(decodeURIComponent(escape(atob(str))), KEY); } catch(e) { return str; }
  }

  var SENSITIVE = ['apiKey', 'qwenApiKey'];

  return {
    encryptSensitiveFields: function(obj) {
      var out = Object.assign({}, obj);
      SENSITIVE.forEach(function(k) {
        if (out[k]) out[k] = _encode(out[k]);
      });
      return out;
    },
    decryptSensitiveFields: function(obj) {
      var out = Object.assign({}, obj);
      SENSITIVE.forEach(function(k) {
        if (out[k]) out[k] = _decode(out[k]);
      });
      return out;
    }
  };
})();
