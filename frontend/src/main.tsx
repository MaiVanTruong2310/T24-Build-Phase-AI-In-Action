import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { Provider } from 'react-redux'
import { App } from './App'
import { store } from './app/store'
import './index.css'
import { startHeartbeatFavicon } from './lib/heartbeatFavicon'

const stopHeartbeatFavicon = startHeartbeatFavicon()
if (import.meta.hot) import.meta.hot.dispose(stopHeartbeatFavicon)

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <Provider store={store}>
      <App />
    </Provider>
  </StrictMode>
)
