import CryptoJS from 'crypto-js';

const MASTER_KEY = process.env.MASTER_KEY;

if (!MASTER_KEY) {
  throw new Error('MASTER_KEY environment variable is required');
}

export function encryptApiKey(plaintext: string): string {
  if (!MASTER_KEY) {
    throw new Error('MASTER_KEY is required for encryption');
  }
  try {
    const encrypted = CryptoJS.AES.encrypt(plaintext, MASTER_KEY).toString();
    return encrypted;
  } catch (error) {
    throw new Error('Failed to encrypt API key');
  }
}

export function decryptApiKey(ciphertext: string): string {
  if (!MASTER_KEY) {
    throw new Error('MASTER_KEY is required for decryption');
  }
  try {
    const decrypted = CryptoJS.AES.decrypt(ciphertext, MASTER_KEY);
    const plaintext = decrypted.toString(CryptoJS.enc.Utf8);
    
    if (!plaintext) {
      throw new Error('Decryption failed - invalid ciphertext or key');
    }
    
    return plaintext;
  } catch (error) {
    throw new Error('Failed to decrypt API key');
  }
}

export function encryptCredentials(apiKey: string, secretKey: string, passphrase?: string) {
  return {
    apiKey: encryptApiKey(apiKey),
    secretKey: encryptApiKey(secretKey),
    passphrase: passphrase ? encryptApiKey(passphrase) : undefined,
  };
}

export function decryptCredentials(encryptedApiKey: string, encryptedSecretKey: string, encryptedPassphrase?: string) {
  return {
    apiKey: decryptApiKey(encryptedApiKey),
    secretKey: decryptApiKey(encryptedSecretKey),
    passphrase: encryptedPassphrase ? decryptApiKey(encryptedPassphrase) : undefined,
  };
}