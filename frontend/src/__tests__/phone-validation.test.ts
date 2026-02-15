/**
 * Tests for phone number validation using libphonenumber-js
 */

import { describe, it, expect } from 'vitest';
import { parsePhoneNumber, isValidPhoneNumber } from 'libphonenumber-js';

describe('Phone Number Validation', () => {
  describe('US Phone Numbers', () => {
    it('validates standard US phone formats', () => {
      const validNumbers = [
        '2128675309',
        '212-867-5309',
        '(212) 867-5309',
        '+1 212 867 5309',
        '+12128675309',
      ];

      validNumbers.forEach(number => {
        expect(isValidPhoneNumber(number, 'US')).toBe(true);
      });
    });

    it('rejects invalid US phone numbers', () => {
      const invalidNumbers = [
        '123',           // Too short
        'abc-def-ghij',  // Non-numeric
        '212',           // Way too short
        '123-456',       // Incomplete
        '555-123-4567',  // Invalid pattern (555 + 123-4567 reserved)
      ];

      invalidNumbers.forEach(number => {
        expect(isValidPhoneNumber(number, 'US')).toBe(false);
      });
    });
  });

  describe('E.164 Normalization', () => {
    it('normalizes US numbers to E.164 format', () => {
      const testCases = [
        { input: '212-867-5309', expected: '+12128675309' },
        { input: '(212) 867-5309', expected: '+12128675309' },
        { input: '+1 212 867 5309', expected: '+12128675309' },
        { input: '2128675309', expected: '+12128675309' },
      ];

      testCases.forEach(({ input, expected }) => {
        const phoneNumber = parsePhoneNumber(input, 'US');
        expect(phoneNumber?.format('E.164')).toBe(expected);
      });
    });

    it('preserves E.164 format when already formatted', () => {
      const e164Number = '+12128675309';
      const phoneNumber = parsePhoneNumber(e164Number, 'US');
      expect(phoneNumber?.format('E.164')).toBe(e164Number);
    });
  });

  describe('International Phone Numbers', () => {
    it('validates international phone numbers', () => {
      const internationalNumbers = [
        { number: '+44 20 7946 0958', country: 'GB' },  // UK
        { number: '+33 1 42 86 82 00', country: 'FR' }, // France
        { number: '+81 3-3264-5111', country: 'JP' },   // Japan
      ];

      internationalNumbers.forEach(({ number, country }) => {
        expect(isValidPhoneNumber(number, country as any)).toBe(true);
      });
    });

    it('formats international numbers to E.164', () => {
      const testCases = [
        { input: '+44 20 7946 0958', country: 'GB', expected: '+442079460958' },
        { input: '+33 1 42 86 82 00', country: 'FR', expected: '+33142868200' },
      ];

      testCases.forEach(({ input, country, expected }) => {
        const phoneNumber = parsePhoneNumber(input, country as any);
        expect(phoneNumber?.format('E.164')).toBe(expected);
      });
    });
  });

  describe('Edge Cases', () => {
    it('handles empty strings', () => {
      expect(isValidPhoneNumber('', 'US')).toBe(false);
    });

    it('handles whitespace-only strings', () => {
      expect(isValidPhoneNumber('   ', 'US')).toBe(false);
    });

    it('handles special characters', () => {
      expect(isValidPhoneNumber('+1 (212) 867-5309', 'US')).toBe(true);
    });

    it('rejects numbers with invalid country codes', () => {
      expect(isValidPhoneNumber('+999 999 999 9999', 'US')).toBe(false);
    });
  });
});
