# Cat Sat Documentation

## Documentation Index

### 📦 SKU & Product Management

- **[SKU_System_Documentation.md](./SKU_System_Documentation.md)** - Tài liệu đầy đủ chi tiết về hệ thống SKU
  - Kiến trúc hệ thống
  - Cấu trúc dữ liệu  
  - Ba Cases mapping (A, B, C)
  - Quy trình tạo dữ liệu
  - Best practices
  - Ví dụ thực tế dòng J55

- **[SKU_Quick_Reference.md](./SKU_Quick_Reference.md)** - Cheat sheet nhanh cho SKU system
  - Code snippets
  - Decision tree
  - Common queries
  - Checklist tạo sản phẩm mới
  - API calls

### ⚙️ Cutting System (Phần Mềm Cắt Sắt)

- **[Cutting_System_Documentation.md](./Cutting_System_Documentation.md)** - **MỚI!** Tài liệu toàn diện về hệ thống cắt sắt
  - Tổng quan hệ thống & workflow
  - Master data setup (Steel Profiles, Cutting Specs)
  - Quy trình sản xuất (Cutting Plan → Cutting Order)
  - Optimization & Planning (OR-Tools algorithm)
  - Production Tracking (Start/Stop, time logging)
   - Progress Monitoring (Dashboard, Sync Report)
  - Reports & Analytics
  - Best Practices & Troubleshooting

### 🖼️ Diagrams

- **[sku_system_architecture.png](./sku_system_architecture.png)** - Sơ đồ kiến trúc SKU system
- **[case_a_multi_sku.png](./case_a_multi_sku.png)** - Minh họa Case A: Nhiều SKU → 1 Item

---

## Quick Start

### SKU System

Xem tổng quan nhanh về 3 cases mapping:

| Case | Customer Code? | Cutting Spec | Khi nào dùng |
|------|----------------|--------------|--------------|
| **A - Chung** | ❌ | Inherit | **NHIỀU SKU KHÁC NHAU** nhưng sản phẩm giống hệt |
| **B - Riêng BOM** | ✅ | Inherit | Khác BOM phụ kiện, cùng định mức cắt sắt |
| **C - Riêng Spec** | ✅ | Override | Khác cả định mức cắt sắt |

### Cutting System

Flow cơ bản:

```
1. Setup Master Data
   ↓
2. Create Cutting Plan + Items
   ↓
3. Create Cutting Orders
   ↓
4. Run Optimization
   ↓
5. Production Tracking
   ↓
6. Monitor Progress
```

---

## Demo Scripts

### Tạo Demo Data SKU J55

```python
# Trong bench console
frappe.call({
    method: "cat_sat.api.j55_demo.create_j55_demo"
})
```

Hoặc:

```bash
bench --site erp.dongnama.app console
```

```python
import cat_sat.api.j55_demo as j55
j55.create_j55_demo()
```

---

## File Structure

```
docs/
├── README.md                           # This file
├── SKU_System_Documentation.md         # SKU system (33KB)
├── SKU_Quick_Reference.md              # SKU cheat sheet (12KB)
├── Cutting_System_Documentation.md     # Cutting system (60KB) 🆕
├── sku_system_architecture.png         # Diagram (570KB)
└── case_a_multi_sku.png                # Case A diagram (572KB)
```

---

**Cập nhật:** 2026-01-16  
**Version:** 2.0
