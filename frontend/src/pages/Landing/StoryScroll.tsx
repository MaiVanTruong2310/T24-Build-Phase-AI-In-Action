import { useLayoutEffect, useRef, type ReactNode } from 'react'
import { Link } from 'react-router-dom'
import gsap from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'
import { CalendarCheck, Check, ListChecks, MessageCircle, PhoneCall, ShieldCheck, Stethoscope } from 'lucide-react'
import { SosButton } from '../../features/chat/SosButton'

gsap.registerPlugin(ScrollTrigger)

const STEPS: { icon: ReactNode; title: string; body: ReactNode }[] = [
  {
    icon: <MessageCircle className="h-5 w-5" />,
    title: 'Kể triệu chứng bằng lời của bạn',
    body: 'Không cần biết thuật ngữ y khoa. Trợ lý ghi nhận triệu chứng, thời gian và các dấu hiệu đi kèm.',
  },
  {
    icon: <ListChecks className="h-5 w-5" />,
    title: 'Mỗi lượt chỉ hỏi một câu ngắn',
    body: 'Trợ lý hỏi lại từng điều quan trọng để không bỏ sót dấu hiệu nguy hiểm, không bắt bạn điền form dài.',
  },
  {
    icon: <Stethoscope className="h-5 w-5" />,
    title: 'Phân tầng mức độ khẩn cấp',
    body: (
      <>
        Đánh giá theo thang ATS 1–5 và gợi ý chuyên khoa phù hợp.{' '}
        <span className="font-semibold text-red-700 dark:text-red-300">
          Có dấu hiệu nguy hiểm, hệ thống dừng ngay và hướng dẫn gọi 115.
        </span>
      </>
    ),
  },
  {
    icon: <ShieldCheck className="h-5 w-5" />,
    title: 'Điều phối viên rà soát',
    body: 'Nhân viên y tế xem lại hướng khám AI đề xuất và có thể tiếp quản cuộc trò chuyện. AI không chẩn đoán xác định và không kê đơn.',
  },
  {
    icon: <CalendarCheck className="h-5 w-5" />,
    title: 'Đặt lịch ngay trong cuộc trò chuyện',
    body: 'Chọn bác sĩ và khung giờ còn trống, giữ chỗ ngay trong cuộc trò chuyện. Điều phối viên xác nhận lịch rồi hệ thống nhắc bạn.',
  },
]

// Chỉ chạy kể chuyện theo cuộn trên màn hình lớn và khi người dùng không bật "giảm chuyển động".
// Các trường hợp còn lại hiển thị bản tĩnh: danh sách bước + khung điện thoại đầy đủ nội dung.
const ANIMATED_QUERY = '(min-width: 1024px) and (prefers-reduced-motion: no-preference)'

export function StoryScroll() {
  const root = useRef<HTMLElement>(null)

  useLayoutEffect(() => {
    const mm = gsap.matchMedia()
    mm.add(ANIMATED_QUERY, () => {
      const q = gsap.utils.selector(root)
      const texts = q('[data-story-text]')
      const tl = gsap.timeline({
        defaults: { ease: 'power2.out', duration: 0.5 },
        scrollTrigger: { trigger: root.current, start: 'top top', end: 'bottom bottom', scrub: 0.6 },
      })

      gsap.set(texts.slice(1), { autoAlpha: 0, y: 24 })
      gsap.set(q('[data-story-item]'), { autoAlpha: 0, y: 18 })
      gsap.set(q('[data-story-ats]'), { autoAlpha: 0 })
      gsap.set(q('[data-story-fill]'), { scaleY: 0, transformOrigin: 'top' })

      const showText = (index: number) =>
        tl
          .to(texts[index - 1], { autoAlpha: 0, y: -24 })
          .to(texts[index], { autoAlpha: 1, y: 0 }, '<0.15')

      tl.to(q('[data-story-fill]'), { scaleY: 1, ease: 'none', duration: 5 }, 0)
      tl.to(q('[data-story-item="1"]'), { autoAlpha: 1, y: 0 }, 0.2).to({}, { duration: 0.4 })
      showText(1)
      tl.to(q('[data-story-item="2"]'), { autoAlpha: 1, y: 0 }).to(q('[data-story-item="3"]'), { autoAlpha: 1, y: 0 })
      showText(2)
      tl.to(q('[data-story-item="4"]'), { autoAlpha: 1, y: 0 })
        .to(q('[data-story-pending]'), { autoAlpha: 0 }, '+=0.2')
        .to(q('[data-story-ats]'), { autoAlpha: 1 }, '<')
      showText(3)
      tl.to(q('[data-story-item="5"]'), { autoAlpha: 1, y: 0 })
      showText(4)
      tl.to(q('[data-story-item="6"]'), { autoAlpha: 1, y: 0 }).to({}, { duration: 0.6 })
    })
    return () => mm.revert()
  }, [])

  return (
    <section
      ref={root}
      id="quy-trinh"
      aria-labelledby="story-title"
      className="relative border-b border-app-border bg-app-deep motion-safe:lg:h-[460vh]"
    >
      <div className="mx-auto flex max-w-7xl items-center px-4 py-16 sm:px-6 sm:py-24 motion-safe:lg:sticky motion-safe:lg:top-0 motion-safe:lg:h-screen motion-safe:lg:py-0 motion-safe:lg:pt-28">
        <div className="grid w-full items-center gap-12 lg:grid-cols-[1fr_minmax(0,400px)] lg:gap-20">
          <div>
            <p className="lp-kicker">Một ca tư vấn minh họa</p>
            <h2 id="story-title" className="mb-10 text-3xl font-semibold leading-tight tracking-tight text-app-text sm:text-4xl lg:text-5xl">
              Từ một câu “tôi bị ho” đến lịch khám đúng chuyên khoa
            </h2>

            <div className="flex gap-6">
              <div aria-hidden="true" className="relative hidden w-0.5 shrink-0 rounded-full bg-app-border motion-safe:lg:block">
                <div data-story-fill className="absolute inset-0 rounded-full bg-app-primary" />
              </div>
              <ol className="space-y-8 motion-safe:lg:grid motion-safe:lg:space-y-0">
                {STEPS.map((step, index) => (
                  <li key={step.title} data-story-text className="flex gap-4 motion-safe:lg:[grid-area:1/1]">
                    <span className="lp-icon">
                      {step.icon}
                    </span>
                    <div>
                      <p className="lp-step">Bước {index + 1}/{STEPS.length}</p>
                      <h3 className="lp-step-title">{step.title}</h3>
                      <p className="mt-2 max-w-md text-sm leading-relaxed text-app-secondary sm:text-base">{step.body}</p>
                    </div>
                  </li>
                ))}
              </ol>
            </div>

            <div className="mt-10 flex flex-wrap items-center gap-3">
              <Link to="/patient" className="hero-btn hero-btn--primary">
                <MessageCircle className="h-5 w-5" strokeWidth={2.2} /> Thử tư vấn ngay
              </Link>
              <SosButton className="hero-sos">
                <PhoneCall className="h-[18px] w-[18px] shrink-0" strokeWidth={2.2} /> <b>Cấp cứu: gọi 115</b>
              </SosButton>
            </div>
          </div>

          <div>
            <PhoneMockup />
            <p className="lp-caption">Hội thoại minh họa, không phải dữ liệu bệnh nhân thật.</p>
          </div>
        </div>
      </div>
    </section>
  )
}

function PhoneMockup() {
  return (
    <div aria-hidden="true" className="mx-auto w-full max-w-[360px] rounded-[2.6rem] border-[10px] border-moss-900 bg-app-page shadow-2xl ring-1 ring-black/5 dark:border-black dark:ring-white/10">
      <div className="flex items-center gap-3 border-b border-app-border bg-app-surface px-4 py-3 rounded-t-[1.9rem]">
        <img src="/vcare-logo.png" alt="" className="h-9 w-9 rounded-xl bg-white object-contain p-0.5" />
        <div className="leading-tight">
          <p className="brand-wordmark text-lg">VCare<span className="brand-plus">+</span></p>
          <p className="text-[11px] text-app-secondary">Trợ lý tiếp đón · đang hoạt động</p>
        </div>
      </div>

      <div className="space-y-3 px-3.5 py-4 text-[13px] leading-snug">
        <Bubble step={1} from="patient">Tôi ho khan 5 ngày nay, chiều sốt nhẹ, người hơi mệt.</Bubble>
        <Bubble step={2} from="bot">Dạ, anh/chị có thấy khó thở hoặc đau ngực không ạ?</Bubble>
        <Bubble step={3} from="patient">Không ạ.</Bubble>

        <div data-story-item="4" className="rounded-2xl border border-app-border bg-app-surface p-3">
          <div className="flex items-center justify-between gap-2">
            <span className="text-[11px] font-semibold uppercase tracking-wide text-app-secondary">Mức độ khẩn cấp</span>
            <span className="grid text-[11px] font-semibold">
              <span data-story-pending className="[grid-area:1/1] invisible rounded-full bg-app-muted px-2 py-0.5 text-app-secondary motion-safe:lg:visible">
                Đang đánh giá…
              </span>
              <span data-story-ats className="[grid-area:1/1] rounded-full bg-forest-100 px-2 py-0.5 text-forest-800 dark:bg-forest-900 dark:text-forest-200">
                ATS 4 · Ít khẩn cấp
              </span>
            </span>
          </div>
          <p className="mt-2 text-app-text">
            Gợi ý chuyên khoa: <strong>Nội hô hấp</strong>
          </p>
        </div>

        <div data-story-item="5" className="flex items-center gap-3 rounded-2xl border border-app-border bg-app-surface p-3">
          <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-clay-100 text-sm font-bold text-clay-700 dark:bg-clay-900 dark:text-clay-200">ĐP</span>
          <div className="min-w-0 flex-1">
            <p className="font-semibold text-app-text">Điều phối viên</p>
            <p className="text-[12px] text-app-secondary">Đã rà soát hướng khám</p>
          </div>
          <ShieldCheck className="h-5 w-5 shrink-0 text-app-primary" />
        </div>

        <div data-story-item="6" className="rounded-2xl bg-app-primary p-3 text-app-on-primary">
          <div className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-wide opacity-80">
            <CalendarCheck className="h-4 w-4" /> Lịch khám
          </div>
          <p className="mt-1.5 text-[15px] font-semibold">Thứ Hai · 09:00 · Nội hô hấp</p>
          <p className="mt-1 flex items-center gap-1 text-[12px] opacity-90">
            <Check className="h-3.5 w-3.5" /> Đã giữ chỗ, điều phối viên sẽ gọi xác nhận
          </p>
        </div>
      </div>
    </div>
  )
}

function Bubble({ step, from, children }: { step: number; from: 'patient' | 'bot'; children: ReactNode }) {
  const mine = from === 'patient'
  return (
    <div data-story-item={step} className={`flex ${mine ? 'justify-end' : 'justify-start'}`}>
      <p
        className={`max-w-[82%] rounded-2xl px-3.5 py-2.5 ${
          mine ? 'rounded-br-md bg-app-primary text-app-on-primary' : 'rounded-bl-md border border-app-border bg-app-surface text-app-text'
        }`}
      >
        {children}
      </p>
    </div>
  )
}
