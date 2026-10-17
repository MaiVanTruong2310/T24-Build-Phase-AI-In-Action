# Bàn điều phối khám

## Phạm vi

Điều phối viên được giả định là bác sĩ có kiến thức lâm sàng. Họ khai thác triệu chứng, tư vấn điều hướng, thay đổi chuyên khoa, tiếp quản hội thoại, ưu tiên cấp cứu, liên hệ lại, xác minh cọc và chốt lịch. Sản phẩm không cấp quyền chẩn đoán xác định hoặc kê đơn. Các mẫu kết luận bệnh/liều thuốc rõ ràng bị chặn; đây là lớp kiểm tra hỗ trợ, không thay thế trách nhiệm chuyên môn.

## Luồng đã triển khai

- Một ca bền vững nối hội thoại, phiếu khám theo buổi, gói dịch vụ và booking.
- Quyền điều phối được cấp trong `coordinator_members`, không suy ra từ thông tin JWT do người dùng tự sửa. Có giới hạn cơ sở; tài khoản quản trị toàn hệ thống mới được sửa danh mục, tài khoản và chính sách.
- Hàng đợi theo ưu tiên; nhận ca có khóa bản ghi và kiểm tra phiên bản.
- Tiếp quản thực thi ở backend. AI tạm dừng phản hồi thông thường khi nhân viên xử lý. Bộ kiểm tra cấp cứu vẫn hoạt động và phản hồi hướng dẫn khẩn ngay, không chờ LLM hoặc cọc.
- Phiên khách được ràng buộc cookie HttpOnly ngẫu nhiên và định danh graph bằng hash capability; không thể đọc phiếu chỉ bằng session ID. Ngữ cảnh cần thiết được lưu DB để khôi phục sau restart.
- Điều chỉnh chuyên khoa/bác sĩ/cơ sở có lý do, đồng ý của bệnh nhân, xác minh lịch và cửa sổ khám. Nếu AI đề xuất khác phương án đã thống nhất, hội thoại được chuyển lại cho người phụ trách.
- Cọc và giữ chỗ dùng chung `booking_holds` với luồng bệnh nhân. Xác nhận cọc yêu cầu mã giao dịch và bằng chứng đã đối soát; khoản đến muộn không tự động chốt lịch. Đổi lịch có thể dùng lại cọc đã xác minh, không yêu cầu thanh toán lần hai.
- Chốt/đổi/hủy cập nhật booking, nguồn yêu cầu, nhật ký và thông báo trong ứng dụng. Hủy khoản đã xác minh tạo trạng thái chờ hoàn; chỉ ghi đã hoàn khi có mã giao dịch thực tế.
- Bắt đầu/kết thúc và bàn giao toàn bộ ca trực; nhắc liên hệ và Dashboard từ dữ liệu DB. Hàng đợi cập nhật mỗi 5 giây; tin nhắn bệnh nhân mỗi 4 giây.
- Trang bệnh nhân `/patient/requests` hiển thị phiếu, hướng dẫn cọc, thông báo và nhận thông tin bổ sung/đổi/hủy. Khách dùng trình duyệt đã gửi phiếu.

## Trước khi triển khai

Áp dụng schema trước khi chạy backend mới. Không tự khởi tạo tài khoản hoặc điều khoản cọc mẫu.

1. Xác nhận `DATABASE_URL` và `AUTH_DATABASE_URL` trỏ cùng database có dữ liệu tài khoản/catalog hiện hành.
2. Trong thư mục dự án, áp dụng migration theo quy trình Alembic hiện hành: `python -m alembic upgrade head`. Migration mới: `0015_coordinator_workbench`. Nếu môi trường trước đây dùng các script schema trực tiếp thay vì Alembic, dùng `python -m scripts.apply_workbench_schema`; script chỉ tạo sáu bảng mới và kiểm tra tồn tại, bật RLS, thu hồi quyền browser. Không dùng `stamp` để bỏ qua migration chưa áp dụng.
3. Đăng ký và xác thực một tài khoản Supabase Auth. Cấp quyền quản trị đầu tiên bằng `python -m scripts.manage_coordinator --email <email-da-xac-thuc> --qualification <thong-tin-chuyen-mon> --admin`. Không đổi mật khẩu, không dùng tài khoản mặc định.
4. Đăng nhập lại; mở `/staff/settings`. Nhập thời hạn xử lý, giữ chỗ, hướng dẫn chuyển cọc và điều kiện đổi/hủy/hoàn thực tế. Cấp quyền tài khoản điều phối viên; cơ sở giới hạn nhập các UUID từ catalog, để trống chỉ khi được phép toàn hệ thống.
5. Công bố lịch thực tế tại `/staff/shifts` (quản trị), hoặc sử dụng lịch catalog đã có. Phiếu theo buổi cần slot thuộc buổi đã công bố.
6. Deploy backend và frontend sau khi schema, quyền và chính sách đã sẵn sàng.

## Vận hành tiền và thông báo

Hiện hỗ trợ xác minh chuyển khoản/hoàn cọc thủ công. Không có tích hợp thu tiền, webhook ngân hàng, gửi SMS/email hoặc tự chuyển tiền hoàn. Nhân viên liên hệ theo điện thoại trong phiếu; ghi kết quả cuộc gọi thật. Thông báo được lưu trong ứng dụng và trang theo dõi phiếu. Khi tích hợp nhà cung cấp thanh toán, phải xác minh chữ ký, số tiền, trạng thái và chống lặp giao dịch ở backend trước khi ghi nhận.

Các endpoint duyệt/chốt cũ được giữ để trả thông báo chuyển sang bàn điều phối; không cho đi vòng bước cọc.

## Kiểm thử

`python -m pytest tests/test_workbench.py -q` chạy kiểm thử offline. Để chạy PostgreSQL integration, đặt `WORKBENCH_TEST_DATABASE_URL` cho DB kiểm thử đã có `btree_gist`. Bộ test tạo một schema `workbench_test_<uuid>` riêng và xóa chính schema đó sau kiểm thử, không sửa dữ liệu ứng dụng.

Các ca kiểm thử bao phủ quyền/phiên khách, nhận ca và giữ chỗ đồng thời, cọc chưa xác minh/hết hạn/đến muộn, chốt/đổi/hủy/hoàn, takeover và cấp cứu, import nguồn không trùng và đồng bộ hủy.
