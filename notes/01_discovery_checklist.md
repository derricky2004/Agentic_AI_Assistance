# Step 1 – Discovery & Understanding (Filled from transcript)

## A. Mục tiêu & thông tin trong cuộc gọi
- Mục tiêu: Đặt lịch **khảo sát & báo giá** lắp **shower** cho shop chuyển thành apartment.
- Trường xuất hiện trong hội thoại:
  - Tên: **Steve Manley**
  - Địa chỉ: **[address provided]**
  - Điện thoại: **[phone provided]**
  - Email: **[email provided]** (Nick đã repeat để xác nhận)
  - Nhu cầu: **Add shower**, cần **estimate**
  - Ngày/giờ: **Ngày mai 11:00 a.m.** (khách linh hoạt, chỉ cần báo trước)
  - Lead source: **Thấy xe tải (truck) của công ty**

## B. Thông tin bắt buộc & validation
- Required:
  - full_name, service_address, phone_number, email, service_request, date, time_window
- Validation/chuẩn hoá:
  - phone: 10–11 số (strip non-digits)
  - email: có @ + domain, case-insensitive
  - address: có số nhà + tên đường
  - date: chuyển “tomorrow” → **YYYY-MM-DD**
  - time_window: chuẩn “HH:MM-HH:MM” (ví dụ **11:00-12:00** nếu chỉ có giờ lẻ)

## C. Quy tắc nghiệp vụ (rút ra/chuẩn hoá)
- Check **coverage** trước khi đề xuất slot.
- Nếu khách linh hoạt: đề xuất slot gần nhất (ví dụ **ngày mai 11:00**).
- Trước khi chốt: **recap đầy đủ** (name, address, phone, email, service, date, time).
- Nếu đổi ý/đổi giờ: quay lại hỏi đúng trường & **recap lại**.
- Gửi **email confirmation** sau khi đặt; kỹ thuật viên **gọi trước** khi đến.

## D. Tone & cách nói
- Lịch sự, ngắn gọn, chuyên nghiệp; hỏi từng bước; xác nhận lại email/phone.

## E. Definition of Done (để chuyển sang Prompt/Agent)
- Prompt có flow + policy thiếu/sai/slot bận/đổi lịch.
- Agent giữ state, có validator, mock tools (coverage/availability/booking/confirmation).
- Recap đầy đủ trước finalize.
