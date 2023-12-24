export const cmm = {
    encryptValue: function(value) {
      const encoder = new TextEncoder();
      const data = encoder.encode(value);

      return window.crypto.subtle.digest('SHA-256', data)
        .then(hash => {
          const hashArray = Array.from(new Uint8Array(hash));
          const hashedValue = hashArray.map(byte => byte.toString(16).padStart(2, '0')).join('');
          return hashedValue;
        });
    }
}
