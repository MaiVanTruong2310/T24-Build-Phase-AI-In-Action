import { useEffect } from 'react'
import { Header } from './Header'
import { Hero } from './Hero'
import { StoryScroll } from './StoryScroll'
import { Features } from './Features'
import { Doctors } from './Doctors'
import { CTA } from './CTA'
import { Footer } from './Footer'
import { ChatbotWidget } from '../../layouts/ChatbotWidget'
import { Visible } from '../../features/uiVisibility/Visible'

export function Landing() {
  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add('is-visible')
          }
        })
      },
      {
        threshold: 0.15,
        rootMargin: '0px 0px -40px 0px',
      }
    )

    const revealElements = document.querySelectorAll('.reveal-item')
    revealElements.forEach((el) => observer.observe(el))

    return () => {
      revealElements.forEach((el) => observer.unobserve(el))
      observer.disconnect()
    }
  }, [])

  return (
    <>
      <div className="min-h-screen font-sans bg-app-page light:bg-app-page dark:bg-app-page text-slate-900 light:text-app-text dark:text-slate-100 transition-colors duration-300">
        <Header />
        <Visible id="landing.hero"><Hero /></Visible>
        <Visible id="landing.story"><StoryScroll /></Visible>
        <Visible id="landing.features"><Features /></Visible>
        <Visible id="landing.doctors"><Doctors /></Visible>
        <Visible id="landing.cta"><CTA /></Visible>
        <Visible id="global.footer"><Footer /></Visible>
      </div>

      {/* Floating Chatbot Widget (Always fixed in viewport above all page layers) */}
      <Visible id="global.floating_chat"><ChatbotWidget /></Visible>
    </>
  )
}
