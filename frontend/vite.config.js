import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      // 프론트에서 /api로 시작하는 요청을 백엔드로 프록시 전송
      '/api': {
        target: 'http://localhost:8080',   // 백엔드 주소 (포트 포함)
        changeOrigin: true,
        // 옵션: 필요하다면 ws: true, secure: false 등 추가
      },
    },
  },
})
