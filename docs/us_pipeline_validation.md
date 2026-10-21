# US pipeline validation & runbook (NG-01, NG-02, NG-03, NG-06)

> Trang thai: TAI LIEU + CODE da viet va unit-test tren du lieu gia. Cac muc "Bang chung can dien"
> chi duoc coi la hoan thanh sau khi ban chay tren may co .env, Docker, SQL, MinIO that.

## 1. Thu tu chay (Windows PowerShell, tu thu muc goc)
```powershell
git pull origin main; uv sync; docker compose up -d; docker compose ps
.\run_us_daily_cohort.bat            # PLAN (xem "Known video IDs", so channel seed)
.\run_us_daily_cohort.bat apply      # batch nho: 20 ID, 80 channel, 3 video/channel (chi 1 lan/ngay)
.\run_us_t24.bat                     # dry-run;  .\run_us_t24.bat apply  khi da den han 24h
.\run_us_chart.bat                   # PLAN;     .\run_us_chart.bat apply  khi quota/DB san sang
uv run python -m src.processing.verify_us_consistency --region US
uv run python -m src.processing.audit_us_discovery --region US
```
Log nam o `logs\US_*.log`. Chi them Task Scheduler sau khi chay tay thanh cong.

## 2. Patch cho run_daily_cohort.py (NG-02, dung seed moi)
Trong `args_parser()` them:
```python
p.add_argument("--extra-seed-file", type=Path, default=None, help="Seed JSON tu us_seed_sources")
```
Trong `gather_candidates()`, ngay sau dong `all_channels = discovery.select_seed_channels(master, a.region, 1_000_000)`:
```python
if a.extra_seed_file:
    from src.ingestion.us_seed_sources import load_seed_file, merge_seeds
    all_channels = merge_seeds(all_channels, load_seed_file(a.extra_seed_file))
```
Quy trinh: `us_seed_sources` PLAN -> `--apply` -> chay 1 batch nho voi `--extra-seed-file` ->
`audit_us_discovery` so sanh confirmed_rate, requests_per_confirmed, effective_channels voi batch truoc.
Giu `--max-per-channel` de tranh lech vao it kenh. Chi so "confirmed_new" moi la tien do, khong phai so candidate.

## 3. Khoi phuc khi SQL/MinIO dung
1. Khong goi lai API neu `t0.json` da co o `data/raw/rolling_cohorts/US/<batch>/`.
2. `docker compose up -d`, doi `docker compose ps` healthy.
3. T0 chua dong bo: xoa KHONG; chay lai `run_daily_cohort --region US --apply` (no tu `sync_unfinished_t0` truoc khi tao batch moi, va bo qua neu hom nay da co batch). Dong bo thu cong: `python -m src.processing.sync_rolling_cohort --manifest <manifest> --phase T0 --apply` (idempotent: UNIQUE(batch_id, video_id, phase) + kiem tra ton tai).
4. T24: `run_us_t24.bat apply` (marker `.t24_synced` chong lap). Chart: `youtube_chart_monitor sync --file <json> --apply`.
5. Kiem tra: `verify_us_consistency` + `reports/assets/sql_us/us_validation.sql`.
Canh bao: khong chay `docker/db/rolling_cohort_chart_schema.sql` (dump, khong co IF NOT EXISTS) len DB dang co du lieu; sao luu truoc.

## 4. Bang chung can dien (sau khi chay that)
| Muc | Ket qua | Ngay | Ghi chu |
|---|---|---|---|
| US batch T0 confirmed (SQL COUNT DISTINCT) | ... | | |
| MinIO object t0.json | ... | | |
| T24 dong bo | ... | | |
| Chart run US (full pagination) | ... | | |
| verify_us_consistency all_consistent | ... | | |
