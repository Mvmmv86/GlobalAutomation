import { describe, it, expect } from 'vitest';
import { verifyHMAC, generateHMAC } from './hmac';

describe('HMAC Utilities', () => {
  const testPayload = '{"test":"data"}';
  const testSecret = 'test_secret_key';

  describe('generateHMAC', () => {
    it('should generate consistent HMAC', () => {
      const hmac1 = generateHMAC(testPayload, testSecret);
      const hmac2 = generateHMAC(testPayload, testSecret);
      
      expect(hmac1).toBe(hmac2);
      expect(hmac1).toBeDefined();
      expect(typeof hmac1).toBe('string');
    });

    it('should generate different HMAC for different payloads', () => {
      const hmac1 = generateHMAC(testPayload, testSecret);
      const hmac2 = generateHMAC('{"different":"data"}', testSecret);
      
      expect(hmac1).not.toBe(hmac2);
    });

    it('should generate different HMAC for different secrets', () => {
      const hmac1 = generateHMAC(testPayload, testSecret);
      const hmac2 = generateHMAC(testPayload, 'different_secret');
      
      expect(hmac1).not.toBe(hmac2);
    });
  });

  describe('verifyHMAC', () => {
    it('should verify valid HMAC', () => {
      const expectedHmac = generateHMAC(testPayload, testSecret);
      const isValid = verifyHMAC(testPayload, expectedHmac, testSecret);
      
      expect(isValid).toBe(true);
    });

    it('should verify HMAC with sha256= prefix', () => {
      const expectedHmac = generateHMAC(testPayload, testSecret);
      const isValid = verifyHMAC(testPayload, `sha256=${expectedHmac}`, testSecret);
      
      expect(isValid).toBe(true);
    });

    it('should reject invalid HMAC', () => {
      const isValid = verifyHMAC(testPayload, 'invalid_hmac', testSecret);
      
      expect(isValid).toBe(false);
    });

    it('should reject HMAC with wrong payload', () => {
      const expectedHmac = generateHMAC(testPayload, testSecret);
      const isValid = verifyHMAC('{"wrong":"payload"}', expectedHmac, testSecret);
      
      expect(isValid).toBe(false);
    });

    it('should reject HMAC with wrong secret', () => {
      const expectedHmac = generateHMAC(testPayload, testSecret);
      const isValid = verifyHMAC(testPayload, expectedHmac, 'wrong_secret');
      
      expect(isValid).toBe(false);
    });
  });
});