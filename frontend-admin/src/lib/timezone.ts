/**
 * Utilitário para conversão de timezone UTC para local
 */

/**
 * Converte uma data UTC para timezone local (Brasil UTC-3)
 * @param utcDate Data em UTC (string ISO ou Date)
 * @returns Data formatada no timezone local
 */
export const convertUTCToLocal = (utcDate: string | Date): Date => {
  if (!utcDate) return new Date()

  const date = typeof utcDate === 'string' ? new Date(utcDate) : utcDate

  // Retorna a data já ajustada para o timezone local do navegador
  return new Date(date.getTime())
}

/**
 * Formata data UTC para string local no formato brasileiro
 * @param utcDate Data em UTC
 * @param options Opções de formatação
 * @returns String formatada no timezone local
 */
export const formatUTCToLocal = (
  utcDate: string | Date,
  options: {
    includeTime?: boolean
    includeSeconds?: boolean
  } = {}
): string => {
  if (!utcDate) return '-'

  const { includeTime = true, includeSeconds = false } = options

  const localDate = convertUTCToLocal(utcDate)

  const dateOptions: Intl.DateTimeFormatOptions = {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    timeZone: 'America/Sao_Paulo' // UTC-3 (Brasil)
  }

  if (includeTime) {
    dateOptions.hour = '2-digit'
    dateOptions.minute = '2-digit'

    if (includeSeconds) {
      dateOptions.second = '2-digit'
    }
  }

  return localDate.toLocaleString('pt-BR', dateOptions)
}

/**
 * Converte timestamp UTC para formato de data legível
 * @param utcTimestamp Timestamp UTC
 * @param showTime Se deve mostrar horário
 * @returns String formatada
 */
export const formatTimestampToLocal = (
  utcTimestamp: string | Date,
  showTime: boolean = true
): string => {
  return formatUTCToLocal(utcTimestamp, {
    includeTime: showTime,
    includeSeconds: false
  })
}

/**
 * Retorna a diferença de tempo entre UTC e local em horas
 * @returns Diferença em horas (ex: -3 para Brasil)
 */
export const getTimezoneOffset = (): number => {
  return new Date().getTimezoneOffset() / -60
}

/**
 * Verifica se uma data está no timezone UTC
 * @param dateString String da data
 * @returns True se for UTC
 */
export const isUTCDate = (dateString: string): boolean => {
  return dateString.includes('Z') || dateString.includes('+00:00')
}