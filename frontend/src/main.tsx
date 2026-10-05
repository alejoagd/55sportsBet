import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import { polyfillCountryFlagEmojis } from 'country-flag-emoji-polyfill'

// Windows no trae emojis de banderas (muestra "ES", "IT"…): en ese caso se
// carga una fuente solo para banderas. Se sirve desde /public para no
// depender del CDN. En Mac/iOS/Android no hace nada.
polyfillCountryFlagEmojis('Twemoji Country Flags', '/fonts/TwemojiCountryFlags.woff2')

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
