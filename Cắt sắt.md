# Định mức sản xuất và tối ưu cắt sắt[^1]

## Giả định

### 1 mã nhà máy (không quan tâm biến thể của khách hàng)

## Ghi chú

### Quản lí kho sắt trực tiếp từ tiến độ sản xuất sắt

### Cây BOM thành phẩm chỉ thể hiện Tổng chiều dài sắt cần để sản xuất Thành phẩm đó

### Chi tiết các đoạn sắt được thể hiện ở một DocType khác

## Doctype

### Loại sắt

#### Custom từ Doctype Item

#### Nếu có checkbox CẮT SẮT

##### Ô nhập số bó sắt khả thi cho MCTĐ

### Chi tiết cắt

#### Tên bộ phận (Tên mảnh)

##### Số lượng mảnh

#### Trong mảnh có

##### Link tới Loại sắt

##### Tên đoạn sắt

###### dày sắt 0.5 0.6mm ?

###### Các feature cần cho estimate thời gian cắt laser
- Số lượng lỗ dập
- Số lượng tán
- Số lượng khoan
- Các chi tiết gia công khác...

##### Kích thước đoạn

##### Số đoạn trên mảnh

##### Số lượng cần

## Yêu cầu cắt sắt

### Cắt sắt cho đồng bộ đủ chi tiết để hàn thành mảnh -> Đủ mảnh để sản xuất cho 1 container

### MC Laser

#### Gia công toàn bộ chi tiết được ngoại trừ uốn sắt

#### Thời gian phụ thuộc

##### Tốc độ máy

##### Số lượng chi tiết gia công

### MC tự động

#### Cắt sắt theo bó sắt (đã khai báo ở loại sắt)

#### Không có gia công chi tiết đoạn sắt (chỉ cắt)

## Thiết kế custom ERPNext cho cắt sắt

### Doctype Item thành phẩm link tới Doctype Chi tiết cắt

#### Mỗi thành phẩm có một bảng chi tiết cắt sắt

### Đầu vào

#### Thành phẩm cần sản xuất (multiple select)

#### Số lượng cần sản xuất của mỗi thành phẩm)

### Quá trình xử lí

#### Tự động filter theo từng loại sắt

#### Có thể điều chỉnh số lượng cần

### Đầu ra bảng chi tiết cắt (Cho từng loại sắt)

#### Có nút start, stop để công nhân ghi nhận hoàn thành

##### Tính tiến độ sản xuất đã cắt

##### Ghi nhận lịch sử thời gian hoàn thành

## SRS

### Non-functional 

### Functional

## BRD

### BACCM

#### Context

##### Sản xuất bàn ghế 

##### B1: Cắt sắt

#### Value

##### Tối ưu lượng sắt cần dùng

##### Tăng tốc độ tính toán so với tính thủ công

#### Stakeholder

##### Admin

##### Kế hoạch sản xuất

###### Xem tiến độ đã cắt sắt

###### Thống kê thời gian cắt sắt

##### Kế toán

###### Quản lí định mức sắt

###### Dùng phần mềm tính toán

##### Công nhân

###### Ghi nhận bắt đầu, hoàn thành

#### Needs

##### **system quản lí định mức sắt**

###### custom thêm từ ERPNext

##### login, phân quyền

##### Gom nhiều thành phẩm -> 1 kế hoạch cắt

##### Tối ưu kế hoạch cắt theo từng loại sắt

##### Tiến độ sản xuất

##### Thống kê lịch sử (thời gian/ sản lượng) cắt

#### Change

##### tính 1 tiếng -> tính 5p

##### tuyển vị trí mới cho kế toán dễ dàng

##### Cắt theo kinh nghiệm -> Cắt theo kế hoạch hệ thống đề xuất

##### cảm tính thời gian -> thống kê tg chính xác

#### Solution

##### Cutting Optimization Problem (Mathlab/ Gurobi/ Google Or-tools)

##### Frappe/ ERPNext framework

### User story

#### Scope

#### Context

#### Business case

### BFD

## Sản phẩm đã có

### Code tính máy cắt laser
	Để giúp bạn có thể prompt cho một AI khác (như ChatGPT, Claude) làm lại hoặc phát triển tiếp dự án này, mình sẽ mô tả chi tiết bài toán dưới dạng một **Tài liệu đặc tả kỹ thuật (Technical Specification Document)**.
	
	Bạn có thể sử dụng cấu trúc dưới đây để yêu cầu AI thực hiện.
	
	---
	
	# ĐẶC TẢ BÀI TOÁN TỐI ƯU HÓA CẮT SẮT (1D CUTTING STOCK PROBLEM)
	
	## 1. Tổng quan dự án
	
	Xây dựng ứng dụng web bằng **Django** để giải quyết bài toán cắt sắt (1D Bin Packing / Cutting Stock Problem). Mục tiêu là tối ưu hóa kế hoạch cắt từ các cây sắt thô (Stock) ra các chi tiết (Items) theo đơn đặt hàng, sử dụng thuật toán quy hoạch ràng buộc (Constraint Programming) với thư viện **Google OR-Tools**.
	
	Hệ thống đặc biệt hỗ trợ quy trình cắt Laser với các ràng buộc về hao hụt, mạch cắt, tề đầu và ưu tiên sản xuất.
	
	## 2. Yêu cầu công nghệ (Tech Stack)
	
	* **Backend:** Python, Django 5.x.
	* **Real-time Communication:** Django Channels (WebSocket), Redis (để stream log quá trình tính toán ra giao diện).
	* **Algorithm Library:** Google OR-Tools (`ortools.sat.python.cp_model`), Pandas, Numpy.
	* **Frontend:** HTML, Bootstrap 5, JavaScript.
	* **Input Data Grid:** Sử dụng thư viện **Handsontable** để nhập liệu danh sách chi tiết (Excel-like).
	
	## 3. Mô hình toán học & Thuật toán (Core Logic)
	
	Bài toán được chia làm 2 giai đoạn (2-Phase Approach) để xử lý số lượng lớn và đảm bảo tìm ra nghiệm tối ưu.
	
	**Lưu ý kỹ thuật quan trọng:** Do OR-Tools CP-SAT chỉ làm việc với số nguyên, toàn bộ dữ liệu đầu vào (kích thước) phải được nhân với hệ số `SCALING_FACTOR = 10` (chuyển float sang int) trước khi tính toán và chia lại khi hiển thị.
	
	### Giai đoạn 1: Tìm tất cả các mẫu cắt (Pattern Generation)
	
	Mục tiêu: Tìm tất cả các cách sắp xếp hợp lệ (Patterns) các chi tiết trên 1 cây sắt thô.
	
	* **Đầu vào:**
	* `L`: Chiều dài cây sắt thô (ví dụ: 6000mm).
	* `trim`: Kích thước tề đầu (cắt bỏ phần đầu cây sắt, ví dụ: 3mm hoặc 10mm).
	* `kerf`: Độ rộng mạch cắt (độ dày lưỡi cưa/tia laser, ví dụ: 1mm).
	* `max_waste`: % hao hụt tối đa cho phép trên 1 cây.
	* `items`: Danh sách các loại đoạn cần cắt .
	
	
	* **Biến quyết định:**  là số lượng đoạn loại  trong một pattern.
	* **Ràng buộc:**
	
	
	* Hao hụt phải nằm trong giới hạn cho phép hoặc phải đủ lớn để tận dụng lại (Ràng buộc Logic: hoặc waste = 0 (lý tưởng), hoặc waste >= ngưỡng nhất định).
	
	
	* **Cơ chế Caching:** Lưu kết quả Giai đoạn 1 vào file `.pkl` dựa trên hash của tham số đầu vào để không phải tính lại nếu dữ liệu không đổi.
	
	### Giai đoạn 2: Tối ưu hóa kế hoạch sản xuất (Production Planning)
	
	Mục tiêu: Từ các Patterns tìm được ở GĐ1, chọn ra số lượng cây sắt cần cắt theo mỗi Pattern để đáp ứng nhu cầu.
	
	* **Đầu vào:**
	* `Patterns`: Kết quả GĐ1.
	* `Demand`: Số lượng yêu cầu cho mỗi loại đoạn ().
	* `Priority`: Độ ưu tiên của từng loại đoạn.
	* `Max Surplus`: Số lượng dư thừa tối đa cho phép (để tránh cắt quá nhiều so với đơn hàng).
	
	
	* **Biến quyết định:**  là số lượng cây sắt được cắt theo Pattern .
	* **Ràng buộc:**
	* Đáp ứng nhu cầu: Tổng số lượng đoạn loại  sản xuất ra .
	* Giới hạn tồn kho: (Tổng sản xuất - Nhu cầu)  `Max Surplus`.
	
	
	* **Hàm mục tiêu (Đa mục tiêu theo thứ tự ưu tiên - Lexicographical Optimization):**
	1. **Ưu tiên 1:** Tối thiểu hóa tổng lượng sắt hao hụt (Scrap).
	2. **Ưu tiên 2:** Tối thiểu hóa tổng lượng tồn kho (Surplus - cắt dư so với yêu cầu).
	3. **Ưu tiên 3 (Optional):** Tối ưu hóa dựa trên điểm ưu tiên (Priority Score). Ưu tiên dùng các pattern chứa các đoạn có Priority cao (số nhỏ).
	
	
	
	### Chế độ đặc biệt: Cắt kết hợp (Combined Mode) - Optional
	
	Logic lọc Pattern trước khi vào GĐ2: Chỉ giữ lại các Pattern thỏa mãn điều kiện nhất định về "Đoạn cuối" (thường dùng để kết hợp giữa máy cắt Laser và máy cắt tay cho đoạn dư).
	
	* Nếu đoạn dài : Pattern phải chứa ít nhất 1 đoạn này.
	* Nếu đoạn ngắn : Pattern phải chứa số lượng lớn đoạn này.
	* Hoặc Pattern phải có phần phôi thừa lớn (để mang đi cắt tay).
	
	## 4. Yêu cầu về Giao diện & Trải nghiệm (UI/UX)
	
	### Trang chủ (Input Form)
	
	* **Thông số chung:**
	* Chiều dài cây sắt (mặc định 6000).
	* Giới hạn tồn kho (Max Surplus).
	* Thời gian giới hạn chạy thuật toán (Time limit).
	* Checkbox: Bật/tắt chế độ ưu tiên, Chế độ cắt kết hợp.
	
	
	* **Bảng nhập liệu (Handsontable):**
	* Cột: Tên sắt, Kích thước (mm), Số lượng cần (Demand), Độ ưu tiên (Priority), Checkbox (Đoạn cuối/Kết hợp).
	* Tính năng: Thêm dòng, xóa dòng, validate dữ liệu số.
	
	
	* **Nút bấm:** "Tìm phương án cắt sắt".
	
	### Khu vực Kết quả & Log (Real-time)
	
	* Sử dụng **WebSocket** để stream log từ Backend lên Frontend:
	* Hiển thị thông báo: "Đang tìm patterns...", "Đang chạy GĐ2...", "Tìm thấy giải pháp tối ưu hao hụt...", "Thời gian chạy: Xs".
	
	
	* **Kết quả cuối cùng:**
	* Bảng tổng hợp: Loại sắt | Cần | Cắt được | Tồn kho.
	* Thống kê: Tổng số cây sắt dùng, Tổng % hao hụt, Tổng chiều dài hao hụt.
	* **Bảng kế hoạch chi tiết (Visual Plan):**
	* STT | Pattern (Minh họa các đoạn cắt: 470mm | 470mm | 25mm...) | Số lượng cây | Hao hụt.
	* Có style CSS đóng khung các đoạn cắt để thợ dễ nhìn.
	
	
	* Nút "In kết quả" (Print view).
	
	
	
	## 5. Luồng xử lý dữ liệu (Data Flow)
	
	1. Người dùng nhập liệu trên Web -> Bấm Submit (AJAX/Fetch).
	2. Backend nhận Request -> Khởi tạo luồng `stdout` ảo để bắt log.
	3. Hàm `get_or_calculate_patterns`: Check hash cache -> Nếu chưa có thì chạy GĐ1 (OR-Tools) -> Lưu cache.
	4. Hàm `solve_phase2`: Load Patterns -> Lọc theo Priority/Combined Mode -> Chạy Solver tối ưu 3 mục tiêu.
	5. Trong quá trình chạy, gửi Log qua Channel Layer (Redis) tới WebSocket Client.
	6. Trả về kết quả JSON -> Frontend render lại bảng kết quả.
	

### Code tính MCTĐ
	Chào bạn, dựa trên toàn bộ source code bạn cung cấp, đây là **Bản mô tả kỹ thuật chi tiết (Technical Requirement Document)**.
	
	Bạn có thể dùng nội dung này để yêu cầu ChatGPT (hoặc các AI khác/Dev khác) xây dựng lại hệ thống tương tự.
	
	---
	
	# YÊU CẦU XÂY DỰNG HỆ THỐNG TỐI ƯU HÓA CẮT SẮT (1D CUTTING STOCK PROBLEM)
	
	## 1. Tổng quan dự án
	
	Xây dựng ứng dụng web giải quyết bài toán tối ưu hóa cắt sắt (1D Cutting Stock) cho nhà máy sản xuất. Hệ thống cần tính toán phương án cắt từ các thanh sắt nguyên liệu (Stock) ra các đoạn ngắn (Segments) theo nhu cầu, sao cho **tối thiểu hóa phế liệu (waste)** và **tối ưu quy trình vận hành** (cắt theo bó).
	
	## 2. Công nghệ yêu cầu (Tech Stack)
	
	* **Backend:** Python, Django.
	* **Optimization Engine:** Google OR-Tools (sử dụng module CP-SAT).
	* **Real-time Communication:** Django Channels (WebSockets) & Redis (để gửi log tiến trình giải thuật ra giao diện).
	* **Frontend:** HTML5, Bootstrap 5, JavaScript.
	* **Data Input Grid:** Handsontable (để nhập liệu dạng Excel).
	* **Data Structure:** Numpy, Pandas.
	
	## 3. Đầu vào bài toán (Input Parameters)
	
	Người dùng nhập các thông số sau trên giao diện:
	
	### A. Thông số kỹ thuật
	
	1. **Chiều dài cây sắt (Stock Length - ):** Ví dụ: 6000mm, 11700mm...
	2. **Tề đầu sắt (Trim Cut - ):** Độ dài phần sắt cần cắt bỏ ở đầu mỗi cây để làm sạch (Ví dụ: 10mm).
	3. **Độ dày lưỡi cắt (Blade Width - ):** Phần hao hụt do lưỡi cưa (Ví dụ: 2.5mm).
	4. **Hệ số bó (Factors):** Các số lượng cây sắt có thể cắt cùng một lúc trong một bó.
	* *Ví dụ:* "14 16 18 20" (nghĩa là máy có thể cắt 1 bó 14 cây, 1 bó 16 cây...).
	* Mặc định hệ thống luôn thêm `1` (cắt tay/cắt lẻ) và `0` vào danh sách này.
	
	
	5. **Giới hạn cắt thủ công:** Số lượng cây lẻ (hệ số = 1) tối đa được phép cắt.
	6. **Dư cho phép (Max Stock Over):** Số lượng đoạn thành phẩm được phép cắt dư so với nhu cầu (để làm tròn bó).
	
	### B. Dữ liệu đoạn cần cắt (Demand List)
	
	Nhập qua bảng tính (Handsontable) gồm 3 cột:
	
	1. **Tên chi tiết:** (Ví dụ: Dầm A, Cột B).
	2. **Kích thước ():** Chiều dài đoạn cần cắt.
	3. **Số lượng ():** Nhu cầu cần thiết.
	
	## 4. Logic thuật toán tối ưu (Optimization Logic)
	
	Hệ thống sử dụng quy trình 2 giai đoạn (2-Phase Approach) với OR-Tools:
	
	### Giai đoạn 1: Sinh mẫu cắt (Pattern Generation)
	
	* **Mục tiêu:** Tìm tất cả các cách cắt hợp lệ (Pattern) trên 1 cây sắt đơn lẻ.
	* **Ràng buộc toán học:**
	
	
	
	*Trong đó:*  là số lượng đoạn kích thước  trong mẫu.
	* **Điều kiện lọc (Heuristic Filtering):**
	1. Chỉ chấp nhận các mẫu cắt sử dụng tối thiểu 99% chiều dài cây sắt (để giảm không gian tìm kiếm).
	2. Sau khi sinh mẫu, kiểm tra lại: Nếu mẫu cắt có phần dư <  (tề đầu) thì loại bỏ (vì không đủ chỗ để cắt tề đầu).
	3. **Giới hạn máy:** Mỗi mẫu cắt chỉ được chứa tối đa **5 loại kích thước khác nhau** (do hạn chế của máy nhả phôi).
	
	
	* **Caching:** Sử dụng MD5 hash của đầu vào để lưu kết quả Phase 1 vào file `.pkl` nhằm tăng tốc cho các lần chạy sau.
	
	### Giai đoạn 2: Phân phối số bó (Bundle Optimization)
	
	* **Mục tiêu:** Chọn ra các mẫu cắt (từ GĐ1) và số lượng bó (theo Factors) để đáp ứng nhu cầu.
	* **Biến quyết định:**  là số lượng bó của Mẫu  với hệ số bó  (ví dụ: 5 bó loại 20 cây/bó theo mẫu A).
	* **Ràng buộc:**
	1. **Đáp ứng nhu cầu:** Tổng số đoạn cắt ra phải  Nhu cầu ().
	2. **Giới hạn dư:** Tổng số đoạn cắt ra phải  Nhu cầu () + Dư cho phép.
	3. **Giới hạn cắt tay:** Tổng số cây cắt với hệ số = 1 phải  Giới hạn cắt thủ công.
	
	
	* **Hàm mục tiêu (Minimize):**
	
	
	* Ưu tiên chính là giảm hao hụt sắt.
	* Ưu tiên phụ là giảm số lần gá phôi (số bó) để tăng năng suất.
	
	
	
	## 5. Chức năng hệ thống & Giao diện (System Features)
	
	### A. Giao diện nhập liệu
	
	* Form nhập thông số kỹ thuật bên trái.
	* Bảng Handsontable bên phải để paste dữ liệu từ Excel.
	* Nút "Tìm phương án cắt" gửi request AJAX.
	
	### B. Xử lý & Phản hồi (Logging)
	
	* **WebSockets:** Khi Backend đang giải thuật (vốn tốn thời gian), phải gửi log Real-time về client.
	* Hiển thị thời gian đếm ngược.
	* Hiển thị: "Đang sinh mẫu...", "Tìm thấy X patterns...", "Hao hụt hiện tại...".
	
	
	* **Cơ chế TeeStream:** Capture `sys.stdout` của Python để đẩy qua WebSockets, giúp người dùng thấy log in ra từ console server.
	
	### C. Hiển thị kết quả (Output)
	
	Sau khi tính toán xong, trả về JSON để hiển thị:
	
	1. **Bảng tổng hợp:**
	* Tên sắt | Kích thước | SL Cần | SL Cắt được | Tồn kho (Dư).
	
	
	2. **Bảng kế hoạch cắt chi tiết (Cutting Plan):**
	* Cấu trúc cột: STT | Hao hụt (mm) | [Các cột kích thước đoạn] | [Các cột số lượng bó theo hệ số] | Tổng số cây.
	* Định dạng: Ẩn các số 0, kẻ khung đậm phân chia rõ ràng các nhóm cột.
	
	
	3. **Thống kê:**
	* Tổng số cây sắt nguyên liệu.
	* Tổng % hao hụt.
	* Số cây cắt máy (theo bó) và số cây cắt tay (lẻ).
	
	
	4. **Chức năng in:** Nút bấm mở cửa sổ in riêng biệt, CSS tối ưu cho khổ giấy A4.
	
	## 6. Lưu ý đặc biệt (Implementation Notes)
	
	* **Lưu trạng thái (Local Storage):** Tự động lưu các giá trị nhập trong Form và Bảng vào `localStorage` của trình duyệt để không bị mất khi reload trang.
	* **Xử lý lỗi:** Nếu không tìm thấy nghiệm (Infeasible), phải báo rõ nguyên nhân (ví dụ: do giới hạn cắt tay quá thấp hoặc không cho phép dư kho).
	* **Timer:** Có cơ chế ngắt thuật toán (Time Limit) nếu chạy quá số phút quy định.
	
	---
	

# Thiết kế DocType cắt sắt[^2]

## Định mức phôi sắt

### Thành phẩm

#### Mảnh 1 - Số lượng 

##### Các chi tiết cắt

#### Mảnh 2 - Số lượng

##### Các chi tiết cắt

## Item (Customize)
	Cần thêm các Custom Field vào Doctype Item chuẩn để phân biệt loại sắt.

### Cây sắt

#### Group: Thép ống

##### UOM: Cây

##### Tạo Template Item có attributes

###### Chiều dài (mm)

###### Vuông? Hộp? Phi?

###### Kích thước (vd V10, H10-20)

###### thickness (5zem, 6zem)

##### Có Custom Field là một list các số nguyên (bó sắt trong máy cắt tự động)

### Thành phẩm

#### Custom Field link tới Bảng cắt chi tiết

## Bảng cắt chi tiết (new Doctype)

### Tên bộ phận (Tên mảnh)

#### Số lượng mảnh

### Trong mảnh có

#### Link tới Loại sắt

#### Tên đoạn sắt

##### dày sắt 0.5 0.6mm ?

##### Các feature cần cho estimate thời gian cắt laser

###### Số lượng lỗ dập

###### Số lượng tán

###### Số lượng khoan

###### Các chi tiết gia công khác...

#### Kích thước đoạn

#### Số lượng đoạn trên mảnh

#### -> Số lượng cần

## Câu hỏi?

### Làm cách nào để có BOM từ thành phẩm -> mảnh -> chi tiết sắt (kiểu BOM đa cấp)

#### vào Thành phẩm là thể hiện tổng quan hết mảnh nào có các chi tiết - số lượng cần nào.

### Lên lộ trình làm app này

# TRIỂN KHAI

## Trả lời 2 câu hỏi chính?

### làm BOM đa cấp (Thành phẩm -> Mảnh -> Chi tiết sắt) như thế nào trong ERPNext/Frappe

### Lộ trình build app (từ dễ -> khó, không làm sai kiến trúc)

## Doctype

### DocType BOM sắt

#### Item - Sắt

##### Dùng **Item Template** và **Item Variants**

##### Item Attributes

###### Length
- 5850mm, 6000m

###### Shape
- Vuông, Hộp, Tròn (Phi), V, U

###### Dimension
- 30x30, 40x80, D60...

###### Thickness
- 5zem, 6zem…

##### Item (Standard Fields & Custom Fields)

###### Item Group:
- Thép ống / Raw Material

###### UOM
- Cây (Bar)

###### Số bó (Custom Field - Data): list string

#### Item - Thành phẩm

##### Dùng Item chuẩn của ERPNext

##### Custom Field

###### Item Group:
- **Thành phẩm**

###### cutting_spec (Link -> **Cutting Specification**)

##### Thành phẩm không chứa chi tiết sắt trực tiếp

#### **Cutting Specification (new)**

##### Đây là BOM logic

##### Fields

###### item -> Link tới Item (Thành phẩm)

###### pieces -> Table: **Cutting Piece**

#### **Cutting Piece (Child Table - Mảnh)**

##### Fields

###### piece_name (Tên mảnh)

###### piece_qty (Số lượng mảnh/ Thành phẩm)

###### details -> Table: **Cutting Detail**

#### **Cutting Detail (Child Table - Chi tiết sắt)**

##### Fields

###### steel_item -> Link Item (Loại sắt)

###### segment_name (tên đoạn)

###### length_mm

###### qty_per_piece

###### total_qty (Read Only - auto)

###### Feature để estimate thời gian cắt
- holes
- bends (uốn)
- rivets (tán)

### **DocType của kế hoạch sản xuất**

#### 1 lsx là 1 container

#### 1 Container cần sản xuất các bộ thành phẩm - SL?

### **Doctype của Kết quả cắt sắt**

#### Kết quả tối ưu trả về dạng database chuẩn để thống kê tiến độ so với kế hoạch

### **Doctype ghi nhận lịch sử sản xuất Start/ Stop từng pattern**

#### Để thống kê thời gian/ sản lượng

#### Có chọn của máy cắt nào

## Ghi chú

### **Cắt sắt đồng bộ cho 1 container?**

#### **Cắt các chi tiết hàn đủ thành mảnh**

##### **Các mảnh đủ cho 1 bộ thành phẩm**

#### **Nếu cắt thiếu 1 loại đoạn sắt thì không thể ghép lại thành một mảnh**

##### **-> Tiến độ sản xuất thiếu 1 bộ thành phẩm**

## Cách BOM đa cấp được sinh ra (Logic)

### Backend chạy logic

#### For mỗi mảnh:
    tổng_mảnh = piece_qty x số lượng thành phẩm
    For mỗi chi tiết:
      tổng_chi_tiết = qty_per_piece x tổng_mảnh
  
  tổng chi tiết = số thành phẩm * số mảnh * số chi tiết/mảnh

### Kết quả

#### Gom theo Kế hoạch cắt sắt cho từng loại sắt (đồng bộ container)

## **Lộ trình làm App**

### Phase 1 (nền dữ liệu)

#### **Mục tiêu**: Chuẩn dữ liệu - chưa cần thuật toán

#### tạo DocType

##### Cutting Specification

##### Cutting Piece

##### Cutting Detail

#### Script

##### Auto tính total_qty

#### UI

##### Nhập liệu mảnh + chi tiết

#### **Kết quả**: Có BOM đa cấp hoàn chỉnh

### Phase 2 (BOM Engine)

#### **Mục tiêu**: Tổng hợp dữ liệu đúng

#### Server Script/ Python Module

##### Flatten BOM

##### Group theo Loại sắt

#### Hiển thị (optional)

##### Tổng chiều dài

##### Tổng số đoạn

#### Button: Generate Cutting Requirement

#### **Kết quả: **1 click ra danh sách cắt

### Phase 3 (kế hoạch cắt)

#### **Mục tiêu**: Từ BOM -> kế hoạch sản xuất

#### Doctype:

##### **Cutting Plan**

#### Logic

##### Gồm nhiều thành phẩm -> 1 plan

##### Tách theo Loại sắt

#### Trạng thái

##### Draft -> In Progress -> Done

### Phase 4 (Optimization Engine)

#### Input

##### Cutting Plan

#### Output

##### Pattern cắt

##### Hao hụt

##### Số cây

#### Gắn với

##### MC Laser

##### MC tự động

### Phase 5 (Thống kê & KPI)

#### Thời gian cắt

#### Hao hụt sắt

#### Hiệu suất máy

# Odoo vs ERPNext

## Odoo

### Marketing nhiều hơn

#### -> được biết rộng rãi hơn

### Có bán cho Enterprise

### Thời gian ra đời

## ERPNext

### Thời gian ra đời

## Tại sao Odoo nổi hơn ERPNext

[^1]: Thiết kế DocType cắt sắt
[^2]: TRIỂN KHAI