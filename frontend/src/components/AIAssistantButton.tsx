import { memo } from 'react'
import { MessageSquare } from 'lucide-react'

export const AIAssistantButton = memo(function AIAssistantButton() {
  return (
    <button className="fixed bottom-6 right-6 bg-sky-700 hover:bg-sky-800 text-white px-5 py-3 rounded-full shadow-lg shadow-sky-900/20 flex items-center gap-2 font-semibold transition-all hover:scale-105 z-50">
      <MessageSquare className="w-5 h-5" />
      Hỗ trợ lâm sàng AI
    </button>
  )
})
