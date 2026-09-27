import { useState, FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { Eye, EyeOff, User, Lock, ShieldCheck, ArrowRight, Loader2, Phone } from 'lucide-react'

export function Register() {
  const [loading, setLoading] = useState(false)
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = useState(false)

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setLoading(true)
    // Simulate API call
    setTimeout(() => {
      setLoading(false)
    }, 1500)
  }

  return (
    <div className="w-full max-w-2xl">
      <div className="bg-white rounded-2xl shadow-[0_8px_30px_rgb(0,0,0,0.04)] p-8">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center gap-2 bg-blue-50 text-blue-700 px-3 py-1.5 rounded-full text-xs font-semibold mb-4">
            <ShieldCheck className="w-4 h-4" />
            Cổng Đăng Ký Y Tế Số An Toàn
          </div>
          <h2 className="text-3xl font-bold text-slate-900 mb-3">Tạo tài khoản MediCare AI</h2>
          <p className="text-sm text-slate-500 max-w-md mx-auto">
            Đăng ký nhanh chóng để quản lý hồ sơ sức khỏe và đặt lịch khám thông minh.
          </p>
        </div>

        <div className="flex gap-4 mb-8">
          <button className="flex-1 flex items-center justify-center gap-2 px-4 py-3 bg-slate-50 hover:bg-slate-100 rounded-xl transition-colors border border-slate-200">
            <div className="w-5 h-5 rounded-full bg-red-100 text-red-500 flex items-center justify-center">
              <User className="w-3 h-3" />
            </div>
            <span className="text-sm font-semibold text-slate-700">Đăng ký bằng VNeID</span>
          </button>
          <button className="flex-1 flex items-center justify-center gap-2 px-4 py-3 bg-slate-50 hover:bg-slate-100 rounded-xl transition-colors border border-slate-200">
            <div className="w-5 h-5 rounded-full bg-white flex items-center justify-center shadow-sm">
              <span className="font-bold text-blue-600 text-xs">G</span>
            </div>
            <span className="text-sm font-semibold text-slate-700">Tài khoản Google</span>
          </button>
        </div>

        <div className="relative flex items-center justify-center mb-8">
          <div className="absolute border-t border-slate-200 w-full"></div>
          <span className="bg-white px-4 text-[10px] font-bold text-slate-400 uppercase tracking-wider relative z-10">
            HOẶC ĐIỀN BIỂU MẪU TRỰC TIẾP
          </span>
        </div>

        <form onSubmit={handleSubmit} className="space-y-8">
          {/* Section 1 */}
          <div>
            <h3 className="flex items-center gap-2 font-bold text-slate-900 mb-4">
              <span className="flex items-center justify-center w-6 h-6 rounded-full bg-blue-100 text-blue-600 text-xs">1</span>
              Thông tin cá nhân
            </h3>
            
            <div className="space-y-4">
              <div className="space-y-1.5">
                <label className="text-sm font-semibold text-slate-900">Họ và tên <span className="text-red-500">*</span></label>
                <div className="relative">
                  <User className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
                  <input type="text" placeholder="Nguyễn Văn A" className="w-full pl-10 pr-4 py-3 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-sky-500/20 focus:border-sky-500 transition-all text-sm bg-white" />
                </div>
              </div>
              
              <div className="space-y-1.5">
                <div className="flex justify-between items-center">
                  <label className="text-sm font-semibold text-slate-900">Số điện thoại <span className="text-red-500">*</span></label>
                  <span className="text-xs text-emerald-600 font-medium flex items-center gap-1">
                    <Lock className="w-3 h-3" /> Dùng làm tài khoản đăng nhập
                  </span>
                </div>
                <div className="relative">
                  <Phone className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
                  <input type="text" placeholder="0912 345 678" className="w-full pl-10 pr-4 py-3 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-sky-500/20 focus:border-sky-500 transition-all text-sm bg-white" />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <label className="text-sm font-semibold text-slate-900">Ngày sinh <span className="text-red-500">*</span></label>
                  <input type="date" className="w-full px-4 py-3 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-sky-500/20 focus:border-sky-500 transition-all text-sm text-slate-500 bg-white" />
                </div>
                <div className="space-y-1.5">
                  <label className="text-sm font-semibold text-slate-900">Giới tính <span className="text-red-500">*</span></label>
                  <select className="w-full px-4 py-3 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-sky-500/20 focus:border-sky-500 transition-all text-sm text-slate-500 bg-white">
                    <option value="">Chọn giới tính</option>
                    <option value="male">Nam</option>
                    <option value="female">Nữ</option>
                  </select>
                </div>
              </div>
            </div>
          </div>

          {/* Section 2 */}
          <div className="bg-slate-50/50 p-6 rounded-2xl border border-slate-100">
            <div className="flex justify-between items-center mb-4">
              <h3 className="flex items-center gap-2 font-bold text-slate-900">
                <span className="flex items-center justify-center w-6 h-6 rounded-full bg-emerald-100 text-emerald-600 text-xs">2</span>
                Định danh y tế
              </h3>
              <span className="text-xs bg-slate-200 text-slate-600 px-2 py-1 rounded-md font-medium">Tùy chọn khuyến khích</span>
            </div>
            
            <div className="space-y-4">
              <div className="space-y-1.5">
                <label className="text-sm font-semibold text-slate-900">Số CCCD / Mã định danh cá nhân</label>
                <div className="relative">
                  <User className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
                  <input type="text" placeholder="12 chữ số" className="w-full pl-10 pr-4 py-3 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-sky-500/20 focus:border-sky-500 transition-all text-sm bg-white" />
                </div>
              </div>

              <div className="space-y-1.5">
                <div className="flex justify-between items-center">
                  <label className="text-sm font-semibold text-slate-900">Mã số Thẻ Bảo hiểm Y tế (BHYT)</label>
                  <span className="text-xs text-emerald-600 font-medium">Liên thông viện phí</span>
                </div>
                <div className="relative">
                  <ShieldCheck className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
                  <input type="text" placeholder="Gồm 15 ký tự - liên thông thanh toán" className="w-full pl-10 pr-4 py-3 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-sky-500/20 focus:border-sky-500 transition-all text-sm bg-white" />
                </div>
              </div>
            </div>
          </div>

          {/* Section 3 */}
          <div>
            <h3 className="flex items-center gap-2 font-bold text-slate-900 mb-4">
              <span className="flex items-center justify-center w-6 h-6 rounded-full bg-blue-100 text-blue-600 text-xs">3</span>
              Bảo mật tài khoản
            </h3>
            
            <div className="space-y-4">
              <div className="space-y-1.5">
                <label className="text-sm font-semibold text-slate-900">Mật khẩu <span className="text-red-500">*</span></label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
                  <input 
                    type={showPassword ? "text" : "password"} 
                    placeholder="Nhập ít nhất 8 ký tự" 
                    className="w-full pl-10 pr-10 py-3 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-sky-500/20 focus:border-sky-500 transition-all text-sm bg-white" 
                  />
                  <button type="button" onClick={() => setShowPassword(!showPassword)} className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400">
                    {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                  </button>
                </div>
                <div className="flex justify-between text-xs text-slate-500 mt-1">
                  <span>Độ bảo mật mật khẩu:</span>
                  <span>Chưa nhập</span>
                </div>
              </div>

              <div className="space-y-1.5">
                <label className="text-sm font-semibold text-slate-900">Xác nhận lại mật khẩu <span className="text-red-500">*</span></label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
                  <input 
                    type={showConfirmPassword ? "text" : "password"} 
                    placeholder="Nhập lại mật khẩu vừa tạo" 
                    className="w-full pl-10 pr-10 py-3 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-sky-500/20 focus:border-sky-500 transition-all text-sm bg-white" 
                  />
                  <button type="button" onClick={() => setShowConfirmPassword(!showConfirmPassword)} className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400">
                    {showConfirmPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                  </button>
                </div>
              </div>
            </div>
          </div>

          <label className="flex items-start gap-3 cursor-pointer">
            <input type="checkbox" className="mt-1 rounded text-sky-600 focus:ring-sky-500/20" />
            <span className="text-sm text-slate-600">
              Tôi đồng ý với <a href="#" className="text-sky-600 font-semibold hover:underline">Điều khoản dịch vụ</a> và <a href="#" className="text-sky-600 font-semibold hover:underline">Chính sách bảo mật dữ liệu y tế</a> của MediCare AI.
            </span>
          </label>

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-sky-700 hover:bg-sky-800 disabled:bg-slate-300 disabled:cursor-not-allowed text-white font-semibold py-3.5 rounded-xl transition-colors flex items-center justify-center gap-2"
          >
            {loading ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <>
                Tạo tài khoản ngay
                <ArrowRight className="w-5 h-5" />
              </>
            )}
          </button>

          <div className="bg-emerald-50 rounded-xl p-4 flex gap-3 border border-emerald-100">
            <ShieldCheck className="w-6 h-6 text-emerald-600 shrink-0" />
            <div>
              <h4 className="text-xs font-bold text-emerald-800 mb-0.5">Cam kết bảo mật y tế số Quốc Gia</h4>
              <p className="text-[11px] text-emerald-600/90 leading-relaxed">
                Dữ liệu cá nhân & hồ sơ sức khỏe điện tử (EHR) được mã hóa tuân thủ quy chuẩn của Bộ Y Tế.
              </p>
            </div>
          </div>
        </form>

        <div className="mt-8 text-center text-sm">
          <span className="text-slate-500">Đã có tài khoản? </span>
          <Link to="/login" className="font-semibold text-sky-600 hover:text-sky-700">
            Đăng nhập
          </Link>
        </div>
      </div>
    </div>
  )
}
