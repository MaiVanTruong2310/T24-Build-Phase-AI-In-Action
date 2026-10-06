import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { VitePWA } from 'vite-plugin-pwa'

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['vcare-logo.png'],
      manifest: {
        name: 'VCare+',
        short_name: 'VCare+',
        description: 'Hệ thống y tế số đa tầng bác sĩ giám sát',
        theme_color: '#0284c7',
        background_color: '#f8fafc',
        display: 'standalone',
        lang: 'vi',
        icons: [
          {
            src: '/vcare-logo.png',
            type: 'image/png'
          }
        ]
      }
    })
  ]
})
