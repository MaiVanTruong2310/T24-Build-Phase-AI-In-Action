import { useEffect } from 'react'
import { Header } from './Header'
import { Hero } from './Hero'
import { Stats } from './Stats'
import { BentoFeatures } from './BentoFeatures'
import { Process } from './Process'
import { Services } from './Services'
import { Doctors } from './Doctors'
import { Comparison } from './Comparison'
import { Wearable } from './Wearable'
import { Testimonials } from './Testimonials'
import { CTA } from './CTA'
import { Footer } from './Footer'
import { ChatbotWidget } from '../../layouts/ChatbotWidget'

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
      <div className="min-h-screen font-sans bg-[#F8FAFC] dark:bg-[#0B1329] text-slate-900 dark:text-slate-100 transition-colors duration-300">
        <Header />
        <Hero />
        <Stats />
        <BentoFeatures />
        <Process />
        <Services />
        <Doctors />
        <Comparison />
        <Wearable />
        <Testimonials />
        <CTA />
        <Footer />
      </div>

      {/* Floating Chatbot Widget (Always fixed in viewport above all page layers) */}
      <ChatbotWidget />
    </>
  )
}
