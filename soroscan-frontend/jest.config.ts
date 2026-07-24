import type { Config } from 'jest';
import nextJest from 'next/jest.js';

const createJestConfig = nextJest({
  dir: './',
});

const config: Config = {
  coverageProvider: 'v8',
  testEnvironment: 'jsdom',
  setupFilesAfterEnv: ['<rootDir>/jest.setup.ts'],
  // Tell Jest how to resolve the @/ path aliases
  moduleNameMapper: {
    '^@/(.*)$': '<rootDir>/$1',
  },
  
  // Coverage collection - combined exclusions
  collectCoverageFrom: [
    'src/**/*.{js,jsx,ts,tsx}', 
    'app/**/*.{js,jsx,ts,tsx}', 
    'components/**/*.{js,jsx,ts,tsx}',
    'lib/**/*.{ts,tsx}',
    'context/**/*.{ts,tsx}',
    'providers/**/*.{ts,tsx}',
    '!**/*.d.ts', 
    '!**/node_modules/**',
    '!**/__generated__/**',
    '!**/gql/**',
  ],

  coverageDirectory: 'coverage',
  coverageReporters: ['text', 'text-summary', 'lcov', 'json', 'html'],

  // Preserved the 70% threshold mandated by the issue
  coverageThreshold: {
    global: {
      branches: 70,
      functions: 70,
      lines: 70,
      statements: 70,
    },
  },
};

export default createJestConfig(config);