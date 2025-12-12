/**
 * Indicators Utils - Shared indicator calculations
 * Export all indicator types, engine, and helpers
 */

// Export all types
export * from './types'

// Export the engine
export { IndicatorEngine, indicatorEngine } from './IndicatorEngine'

// Export Nadaraya-Watson Envelope
export {
  calculateNadarayaWatsonEnvelope,
  NW_DEFAULT_PARAMS,
  NW_COLORS,
  NW_ENVELOPE_PRESET
} from './nadarayaWatson'
export type {
  NWEnvelopeParams,
  NWEnvelopePoint,
  NWEnvelopeResult,
  NWSignal
} from './nadarayaWatson'

// Export TPO (Time Price Opportunity / Market Profile)
// Réplica exata do Pine Script "TPO (Replica)" by Criptooasis
export {
  calculateTPO,
  generateRenderData as generateTPORenderData,
  getTPOColor,
  getBoxColor as getTPOBoxColor,
  getBlockColor as getTPOBlockColor,
  DEFAULT_TPO_CONFIG
} from './tpo'
export type {
  TPOConfig,
  TPOProfile,
  TPOLevel,
  TPOLetter,
  TPOResult,
  TPORenderData,
  TPOBox,
  TPOHorizontalLine
} from './tpo'
