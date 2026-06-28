# REQUIREMENT.md — 每日回顧平台

## 1. 專案概述

**專案名稱**：每日回顧平台（Daily Review Platform）

**定位**：一個公開的 SaaS Web 應用，協助個人用戶透過每日固定結構的回顧表單，記錄任務完成情況、情緒狀態、感恩事項與習慣打卡，同時提供視覺化統計幫助使用者看見自己的成長軌跡。

**核心目標**：
- 降低每日回顧的摩擦力，讓記錄成為一個可持續的習慣
- 透過固定結構確保回顧品質，同時保留自由筆記空間
- 以統計視覺化讓使用者看到長期累積的成效

---

## 2. 目標使用者

- **主要對象**：希望養成每日回顧習慣的個人用戶
- **使用情境**：個人成長（情緒記錄、習慣養成、目標追蹤）+ 工作效率（任務回顧、進度追蹤）
- **語言**：繁體中文介面為主

---

## 3. 技術架構

| 層級 | 技術選型 |
|------|----------|
| 前端 | Next.js (React) + TypeScript |
| 後端 | Python + FastAPI |
| 資料庫 | PostgreSQL |
| 使用者驗證 | Email/密碼（bcrypt）+ Google OAuth + GitHub OAuth |
| 前端部署 | Vercel |
| 後端部署 | Railway 或 Render |

---

## 4. 功能需求

### F1 — 使用者系統

#### F1-1 註冊
- 使用 Email + 密碼進行註冊
- 密碼需符合最低強度要求（至少 8 碼）
- 寄送 Email 驗證信，驗證後才可登入

#### F1-2 登入
- Email + 密碼登入
- Google OAuth 登入
- GitHub OAuth 登入
- 登入後維持 Session（JWT Token）

#### F1-3 個人設定頁
- 修改顯示名稱
- 修改密碼（需輸入舊密碼）
- 設定每日提醒時間（預設 21:00）
- 開啟 / 關閉提醒通知

---

### F2 — 每日回顧（核心功能）

每天可建立一筆回顧紀錄，包含兩大區塊：

#### F2-1 固定結構區塊

**任務區**
- 輸入今日完成的任務（可多筆，每筆為一行）
- 輸入今日未完成的任務（可多筆，每筆為一行）
- 每筆任務可標記完成 ✓ 或未完成 ✗

**情緒區**
- 心情評分：1–5 分（1 = 非常差，5 = 非常好）
- 今日感恩：輸入 1–3 項感恩事項（文字輸入）

**習慣區**
- 顯示使用者目前所有啟用中的習慣
- 每個習慣可勾選完成（Yes）或不打勾（No/未做）

#### F2-2 自由筆記區塊
- 純文字自由輸入，無字數限制
- 支援基本 Markdown 格式（粗體、清單、標題）

#### F2-3 回顧規則
- 每位使用者每天只能有一筆回顧紀錄
- 當天的回顧可隨時修改
- 跨天後（超過當日 23:59）回顧自動鎖定為唯讀

---

### F3 — 習慣管理

#### F3-1 建立習慣
- 名稱（必填）
- 描述（選填）
- 開始日期（預設今日）

#### F3-2 編輯習慣
- 可修改名稱與描述

#### F3-3 封存習慣
- 封存後不再顯示於每日回顧的習慣區
- 封存習慣的歷史打卡記錄仍保留，用於統計

#### F3-4 打卡邏輯
- 每日回顧時一次打卡所有習慣（Yes/No）
- 打卡記錄附屬於當日的回顧紀錄

---

### F4 — 目標管理

#### F4-1 建立目標
- 標題（必填）
- 描述（選填）
- 截止日期（選填）
- 狀態：進行中（預設）/ 完成 / 封存

#### F4-2 編輯目標
- 可修改所有欄位、變更狀態

#### F4-3 目標與每日回顧的連結
- 每日回顧時，顯示目前「進行中」的目標清單
- 使用者可勾選「今日有推進此目標」（Yes/No）
- 此勾選記錄附屬於當日回顧

---

### F5 — 統計與視覺化（Dashboard）

#### F5-1 回顧熱圖
- GitHub 風格的年曆熱圖
- 有完成回顧的日期顯示深色格子，未完成顯示淺色
- 可切換顯示過去 1 年的資料

#### F5-2 習慣連續天數（Streak）
- 每個習慣顯示：
  - 當前連續打卡天數
  - 歷史最高連續天數

#### F5-3 心情趨勢折線圖
- X 軸為日期，Y 軸為心情評分（1–5）
- 可切換顯示區間：過去 7 天 / 過去 30 天

#### F5-4 心情分佈統計
- 顯示本週 / 本月的心情評分分佈（長條圖或圓餅圖）
- 例如：「本月 5 分天數：12 天，佔 40%」

#### F5-5 習慣完成率
- 顯示本月每個習慣的完成百分比
- 例如：「早起習慣：22/30 天，完成率 73%」

---

### F6 — 每日提醒通知

- 使用者可在個人設定頁設定每日提醒時間（預設 21:00）
- 系統於設定時間發送 Email 提醒使用者進行當日回顧
- 若當天已完成回顧，則不發送提醒
- **v1**：Email 通知
- **v2（未來）**：瀏覽器推播通知（Web Push）

---

## 5. 資料模型（概要）

```
users
  - id, email, password_hash, display_name
  - reminder_enabled (bool), reminder_time (time)
  - created_at, updated_at

user_oauth
  - id, user_id, provider (google/github), provider_user_id

daily_reviews
  - id, user_id, date (unique per user), free_note, mood_score (1-5)
  - is_locked (bool), created_at, updated_at

review_tasks
  - id, review_id, content, is_completed (bool), type (done/not_done)

gratitude_items
  - id, review_id, content, order (1-3)

habits
  - id, user_id, name, description, start_date, is_archived (bool)
  - created_at

habit_logs
  - id, review_id, habit_id, is_completed (bool)

goals
  - id, user_id, title, description, due_date, status (active/completed/archived)
  - created_at, updated_at

goal_daily_progress
  - id, review_id, goal_id, has_progressed (bool)
```

---

## 6. 非功能需求

| 項目 | 要求 |
|------|------|
| 響應式設計 | 桌面為主，平板為次，行動裝置基本可用 |
| 安全性 | HTTPS 強制、密碼 bcrypt 加密、JWT 有效期限管理 |
| 防濫用 | API rate limiting（尤其是登入與註冊端點） |
| 測試 | 後端核心 API 單元測試覆蓋（習慣打卡、回顧 CRUD、統計計算） |
| 效能 | Dashboard 統計查詢在 1 秒內回應（適當加索引） |

---

## 7. 範圍外（Out of Scope）

以下功能**不在 v1 範疇內**，列為未來規劃：

| 功能 | 說明 |
|------|------|
| AI 分析 / 建議 | AI 總結回顧內容、趨勢分析、個人化建議 |
| 行動 App | iOS / Android 原生應用 |
| 付費訂閱機制 | 免費試用 + 付費進階方案 |
| 多語言 i18n | 英文或其他語言介面 |
| 團隊 / 協作 | 多人共用、主管查看下屬回顧等功能 |
| 瀏覽器推播通知 | Web Push（v2 規劃） |
| 資料匯出 | 匯出 PDF / CSV 回顧紀錄 |
