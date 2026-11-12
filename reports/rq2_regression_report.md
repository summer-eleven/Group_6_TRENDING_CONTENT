# Báo Cáo Huấn Luyện Mô Hình Hồi Quy Độ Lan Tỏa Video (HT-06: Viral Regression JP)

## 1. Giới Thiệu & Mục Tiêu Nghiên Cứu
Báo cáo này phân tích thực nghiệm câu hỏi nghiên cứu **RQ2**: *Mức độ phản ứng cảm xúc của cộng đồng (đặc biệt là tỷ lệ bình luận tiêu cực 
egative_ratio / weighted_negative_ratio) ảnh hưởng như thế nào đến độ lan tỏa (virality - $\\log(1 + \\text{view\\_count})$) của video YouTube tại thị trường Nhật Bản?*

- **Biến mục tiêu (Target):** $\\log(1 + \\text{view\\_count})$
- **Số lượng quan sát:** 1,018 video hoàn chỉnh từ hệ thống rolling cohorts và registry mở rộng JP (loại bỏ video lỗi view = 0).
- **Phương pháp đánh giá:**
  1. Hồi quy tuyến tính bình phương tối thiểu thông thường (OLS) có kiểm định tham số: $-statistic, $-value, khoảng tin cậy 95% (95% CI).
  2. Hồi quy tuyến tính phạt L2 (Ridge Regression, $\\alpha=1.0$) với chuẩn hóa StandardScaler.
  3. Hồi quy phi tuyến Random Forest Regressor (=100$, $\\text{max\\_depth}=5$).
  4. Đánh giá kiểm chứng chéo 5-lần (5-Fold Cross Validation).

## 2. Kết Quả Mô Hình Hồi Quy Tuyến Tính OLS (Kiểm Định Tham Số)

| Biến Đặc Trưng | Hệ Số $\\beta$ (OLS) | Sai Số Chuẩn (Std Err) | Thống Kê $ | Giá Trị $-value | Khoảng Tin Cậy 95% |
|:---|:---:|:---:|:---:|:---:|:---:|
| **Hằng số (const)** | 9.7575 | 0.3205 | 30.44 | < 0.0001 | [9.1285, 10.3866] |
| **
egative_ratio** | **1.1425** | **0.3287** | **3.48** | **0.0005\*\*\*** | **[0.4975, 1.7874]** |
| **positive_ratio** | 1.2309 | 0.2611 | 4.71 | < 0.0001*** | [0.7186, 1.7432] |
| **like_to_view_ratio** | 0.9939 | 2.5082 | 0.40 | 0.6920 | [-3.9280, 5.9158] |
| **comment_to_view_ratio** | -2.8717 | 4.7645 | -0.60 | 0.5468 | [-12.2213, 6.4779] |
| **upload_hour_jst** | 0.0109 | 0.0076 | 1.44 | 0.1516 | [-0.0040, 0.0258] |
| **is_weekend** | -0.1770 | 0.1028 | -1.72 | 0.0854 | [-0.3786, 0.0247] |

*Ghi chú: ^2 = 0.1037$ (10.37%), ^2$ hiệu chỉnh $= 0.0867$, Thống kê  = 5.60$ ( < 0.0001$). Các biến phân loại thể loại video (category_id) được kiểm soát trong mô hình.*

## 3. So Sánh Hiệu Năng Giữa Hai Mô Hình Machine Learning (Report 4 Requirement)

| Thuật Toán ML | ^2$ Test Set (80/20) | MAE (Log Views) | RMSE (Log Views) | 5-Fold CV ^2$ (Mean $\\pm$ Std) |
|:---|:---:|:---:|:---:|:---:|
| **Ridge Regression (Chuẩn hóa L2)** | **0.0537** | **1.1347** | **1.4560** | -2.420 $\\pm$ 4.854 |
| **Random Forest Regressor (Phi tuyến)** | **0.2659** | **0.9834** | **1.2824** | **0.3094 $\\pm$ 0.0455** |

### Top biến quan trọng trong Random Forest:
1. comment_to_view_ratio (0.241)
2. like_to_view_ratio (0.218)
3. weighted_negative_ratio / 
egative_ratio (0.165)
4. positive_ratio (0.142)
5. upload_hour_jst (0.098)

## 4. Biện Luận Thống Kê & Giới Hạn Nghiên Cứu (Honest Statistical Interpretation)

1. **Về kiểm định giả thuyết:**
   - Biến 
egative_ratio có hệ số $\\beta = +1.1425$ ( = 3.48$,  = 0.0005 < 0.001$). Khoảng tin cậy 95% là $[0.4975, 1.7874]$ hoàn toàn nằm trên mức 0.
   - **Kết luận:** Có đủ cơ sở thống kê để **BÁC BỎ giả thuyết vô hiệu $** và **CHẤP NHẬN giả thuyết $**: Tỷ lệ bình luận tiêu cực có mối liên hệ tương quan dương có ý nghĩa thống kê với độ lan tỏa của video.
2. **Về khả năng giải thích của mô hình:**
   - Cần nhìn nhận trung thực: Mô hình tuyến tính chỉ giải thích được **.37\%$** (^2 = 0.1037$) biến thiên của lượt xem. Điều này cho thấy lượt xem YouTube chịu tác động của rất nhiều yếu tố ngoại sinh phức tạp (thuật toán đề xuất, mức độ đầu tư video, thương hiệu cá nhân của Creator) mà chỉ số cảm xúc bình luận chỉ đóng góp một phần khiêm tốn.
   - Mô hình Random Forest đạt ^2$ kiểm chứng chéo 5-lần trung bình **.94\%$**, cho thấy mối quan hệ giữa tương tác người xem và độ lan tỏa mang tính **phi tuyến (non-linear)** rõ rệt.
3. **Phân biệt tương quan và nhân quả:**
   - Kết quả này chỉ chứng minh **mối quan hệ tương quan (Correlation)** trong mẫu quan sát, **KHÔNG CHỨNG MINH quan hệ nhân quả (Causality)**. Không thể suy diễn rằng cố tình tạo ra bình luận tiêu cực sẽ tự động làm tăng lượt xem của video.
