import { Bot, MessageCircle, X } from 'lucide-react'
import { useDispatch, useSelector } from 'react-redux'
import { closeChat, toggleChat, type RootState } from '../app/store'

export function ChatbotWidget() {
  const dispatch = useDispatch()
  const isChatOpen = useSelector((state: RootState) => state.layout.isChatOpen)

  return (
    <div className="fixed bottom-6 right-6 z-40 flex flex-col items-end gap-3">
      {isChatOpen && (
        <section className="w-[min(22rem,calc(100vw-3rem))] rounded-2xl border border-slate-200 bg-white p-4 shadow-xl" aria-label="MediCare AI chatbot">
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="font-semibold text-slate-900">MediCare AI</p>
              <p className="mt-1 text-xs text-slate-500">OpenAI là provider mặc định</p>
            </div>
            <button
              type="button"
              onClick={() => dispatch(closeChat())}
              className="rounded-lg p-1.5 text-slate-500 hover:bg-slate-100 hover:text-slate-900"
              aria-label="Đóng chatbot"
            >
              <X className="size-4" />
            </button>
          </div>
          <div className="mt-4 rounded-xl bg-cyan-50 p-3 text-sm text-cyan-950">
            Widget sẵn sàng để kết nối với AI service.
          </div>
        </section>
      )}
      <button
        type="button"
        onClick={() => dispatch(toggleChat())}
        className="grid size-14 place-items-center rounded-full bg-cyan-600 text-white shadow-lg shadow-cyan-600/25 transition hover:bg-cyan-700 focus:outline-none focus:ring-4 focus:ring-cyan-200"
        aria-label={isChatOpen ? 'Đóng chatbot' : 'Mở chatbot'}
      >
        {isChatOpen ? <MessageCircle className="size-6" /> : <Bot className="size-6" />}
      </button>
    </div>
  )
}
