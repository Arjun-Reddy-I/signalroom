export const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? '/api'
export const APP_NAME = 'Signalroom'
export const WORKSPACE_NAME = 'Northstar Studio'

export const isDemoModeEnabled = () => process.env.NEXT_PUBLIC_ENABLE_DEMO_MODE === 'true'
