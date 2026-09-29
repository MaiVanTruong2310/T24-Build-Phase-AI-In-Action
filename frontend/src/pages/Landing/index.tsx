import { Header } from './Header'
import { Hero } from './Hero'
import { Stats } from './Stats'
import { Process } from './Process'
import { Services } from './Services'
import { Doctors } from './Doctors'
import { Comparison } from './Comparison'
import { Wearable } from './Wearable'
import { Testimonials } from './Testimonials'
import { CTA } from './CTA'
import { Footer } from './Footer'

export function Landing() {
  return (
    <div className="min-h-screen font-sans bg-white relative">
      <Header />
      <Hero />
      <Stats />
      <Process />
      <Services />
      <Doctors />
      <Comparison />
      <Wearable />
      <Testimonials />
      <CTA />
      <Footer />
      
      {/* Floating Chatbot Action button */}
      <button className="fixed bottom-6 right-6 bg-sky-700 hover:bg-sky-800 text-white w-14 h-14 rounded-full shadow-[0_8px_30px_rgb(12,74,110,0.3)] flex items-center justify-center transition-transform hover:scale-105 z-50">
        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="m3 21 1.9-5.7a8.5 8.5 0 1 1 3.8 3.8z"/></svg>
        <div className="absolute top-0 right-0 w-4 h-4 bg-red-500 rounded-full border-2 border-white flex items-center justify-center text-[10px] font-bold">1</div>
      </button>
    </div>
  )
}
