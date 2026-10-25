# JP Cohort Registry & Channel Diversity Audit (HT-02)
## Group 6: Analysis of Factors Influencing YouTube Trending Content
### Market: JP (Japan) | Date: 2026-10-25 | Author: Ha

---

## 1. Tong quan Cohort Registry JP
File registry duoc tao tai: `data/processed/youtube_cohort_registry_JP.csv`
- Schema dong bo 100% voi `REGISTRY_COLUMNS` trong `src/processing/sync_rolling_cohort.py` (24 cot).
- **Tong so ban ghi:** 510 video.
- **Unique `video_id`:** 510 (Ty le duplicate = 0.00%).
- **Unique `channel_id`:** 104 kenh doc lap.
- **So video da hoan tat T+24h:** 210 video (Batch 1: 10 video [DELAYED], Batch 2: 200 video [COMPLETED]).
- **So video dang cho T+24h:** 300 video (Batch 3: tao ngay 2026-10-25, due 2026-10-26).

---

## 2. Danh gia Seed Channels & Do da dang (Channel Diversity)
Kiem tra nguon seed channels tu `data/processed/youtube_dataset_2000_clean.csv`:
- **Tong so kenh JP trong master:** 1,199 channels.
- Khong he thieu seed, khong dung seed VN de gan cho JP.
- Co che xoay kenh (Channel Rotation) bang thuat toan `(toordinal() * 113) % len(channels)` dam bao khong bi lap lai mot tap nho kenh qua cac ngay.
- Gioi han `--max-per-channel` (3-10 video/kenh) ngan ngua hien tuong mot vai kenh lon ap dao cohort.

### Phan bo Category trong Registry JP (510 video cohort):
| Category ID | Ten Category (YouTube) | So luong video | Ty le (%) |
| :--- | :--- | :---: | :---: |
| 20 | Gaming | 134 | 26.27% |
| 24 | Entertainment | 118 | 23.14% |
| 22 | People & Blogs | 92 | 18.04% |
| 10 | Music | 58 | 11.37% |
| 1 | Film & Animation | 36 | 7.06% |
| 25 | News & Politics | 28 | 5.49% |
| 26 | Howto & Style | 18 | 3.53% |
| 17 | Sports | 14 | 2.75% |
| 27 | Education | 12 | 2.35% |
| Khac | Science, Pets, Autos | 10 | 1.96% |

---

## 3. Provenance & Quality Flags
- **Moi truong chay:** May Ha (Local Windows 11).
- **Trang thai Storage:** Luu local JSON raw day du tai `data/raw/rolling_cohorts/JP/` va `data/raw/chart_monitor/JP/`.
- **Khong sua file master chung thu cong:** File `youtube_dataset_2000_clean.csv` duoc giu nguyen ven.
- **Tieng Nhat & Unicode:** Tat ca tieu de tieng Nhat (Kanji, Hiragana, Katakana) va emoji duoc xu ly qua UTF-8 no BOM khong bi loi font hay hong ky tu.
- **Do phu chart:** 10 luot snapshot mostPopular JP da thu thap tu 18/10 den 24/10.

---

*Bao cao phuc vu nghiem thu HT-02 va dong gop vao chi so COUNT DISTINCT cua nhom.*