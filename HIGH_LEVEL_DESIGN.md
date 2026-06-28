# HIGH_LEVEL_DESIGN.md — 每日回顧平台

## 目錄

1. [系統概述](#1-系統概述)
2. [技術架構總覽](#2-技術架構總覽)
3. [系統架構圖](#3-系統架構圖)
4. [前端架構設計](#4-前端架構設計)
5. [後端架構設計](#5-後端架構設計)
6. [資料庫設計](#6-資料庫設計)
7. [API 設計概覽](#7-api-設計概覽)
8. [認證與安全設計](#8-認證與安全設計)
9. [功能模組設計](#9-功能模組設計)
10. [UI/UX 風格設計](#10-uiux-風格設計)
11. [非功能需求設計](#11-非功能需求設計)
12. [部署架構](#12-部署架構)
13. [開發優先級與分階段計畫](#13-開發優先級與分階段計畫)

---

## 1. 系統概述

### 1.1 產品定位

**每日回顧平台（Daily Review Platform）** 是一個公開的 SaaS Web 應用，透過固定結構的每日回顧表單，協助個人用戶養成持續記錄的習慣，並以視覺化統計呈現長期成長軌跡。

### 1.2 核心設計原則

| 原則 | 說明 |
|------|------|
| **低摩擦力** | 回顧表單結構固定，最少點擊即可完成當日記錄 |
| **固定 + 彈性** | 固定區塊確保回顧品質，自由筆記保留個人空間 |
| **可見成長** | 視覺化統計讓使用者感知長期累積的成效 |
| **安全可信** | 個人資料嚴格保護，僅使用者本人可存取 |

### 1.3 目標使用者

- 希望養成每日回顧習慣的個人用戶
- 使用情境：個人成長（情緒、習慣、目標）＋工作效率（任務回顧）
- 主要語言：繁體中文介面

---

## 2. 技術架構總覽

### 2.1 技術選型

| 層級 | 技術選型 | 選型理由 |
|------|----------|----------|
| **前端框架** | Next.js 14 (App Router) + TypeScript | SSR/SSG 支援、SEO 友善、React 生態系成熟 |
| **前端樣式** | Tailwind CSS + shadcn/ui | 快速開發、元件一致性、易於客製化 |
| **後端框架** | Python 3.11 + FastAPI | 高效能非同步、自動 OpenAPI 文件、類型驗證 |
| **資料庫** | PostgreSQL 15 | 關聯資料模型、強一致性、豐富查詢能力 |
| **ORM** | SQLAlchemy 2.0 + Alembic | 資料庫遷移管理、型別安全 |
| **驗證** | Email/bcrypt + Google OAuth + GitHub OAuth | 多元登入方式、JWT 維持 Session |
| **Email 服務** | SendGrid（或 AWS SES） | 驗證信與提醒通知發送 |
| **前端部署** | Vercel | Next.js 原生支援、邊緣函數、CDN 加速 |
| **後端部署** | Railway 或 Render | 簡易 Docker 部署、自動擴縮 |
| **排程任務** | APScheduler（內嵌於後端）| 每日提醒 Email 定時任務 |

### 2.2 開發工具

| 工具 | 用途 |
|------|------|
| Git + GitHub | 版本控制、協作 |
| GitHub Actions | CI/CD 自動化測試與部署 |
| Docker | 本地開發環境一致性 |
| pytest | 後端 API 單元測試 |
| Vitest / Testing Library | 前端元件測試 |

---

## 3. 系統架構圖

```
┌──────────────────────────────────────────────────────────────────┐
│                        使用者瀏覽器                               │
│               Next.js App (Vercel CDN)                           │
│  ┌────────────┐  ┌────────────┐  ┌───────────┐  ┌────────────┐  │
│  │  Auth 頁面  │  │  回顧填寫  │  │  習慣管理  │  │ Dashboard  │  │
│  └────────────┘  └────────────┘  └───────────┘  └────────────┘  │
└─────────────────────────┬────────────────────────────────────────┘
                          │ HTTPS / REST API
                          ▼
┌──────────────────────────────────────────────────────────────────┐
│                     FastAPI Backend (Railway)                     │
│                                                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────────┐  │
│  │ Auth     │  │ Review   │  │ Habit /  │  │  Stats /       │  │
│  │ Router   │  │ Router   │  │ Goal     │  │  Dashboard     │  │
│  │          │  │          │  │ Router   │  │  Router        │  │
│  └──────────┘  └──────────┘  └──────────┘  └────────────────┘  │
│                                                                  │
│  ┌─────────────────────┐  ┌────────────────────────────────────┐│
│  │   JWT Middleware     │  │  APScheduler (每日提醒 Email 任務)  ││
│  └─────────────────────┘  └────────────────────────────────────┘│
└─────────────────────────┬────────────────────────────────────────┘
                          │
          ┌───────────────┴──────────────┐
          ▼                              ▼
┌──────────────────┐          ┌──────────────────────┐
│  PostgreSQL DB   │          │  Email Service        │
│  (Railway / PG)  │          │  (SendGrid / AWS SES) │
└──────────────────┘          └──────────────────────┘
          │
          ▼
┌──────────────────────────────────────────────┐
│              外部 OAuth 服務                   │
│   Google OAuth 2.0    GitHub OAuth 2.0        │
└──────────────────────────────────────────────┘
```

### 3.1 資料流說明

```
使用者操作 → Next.js 前端 → API 請求 (Bearer JWT)
    → FastAPI 後端 → JWT 驗證 Middleware
    → 對應 Router → Service 層業務邏輯
    → SQLAlchemy ORM → PostgreSQL
    → 回傳 JSON → 前端渲染
```

---

## 4. 前端架構設計

### 4.1 目錄結構

```
frontend/
├── app/                        # Next.js App Router
│   ├── (auth)/                 # 驗證相關頁面群組
│   │   ├── login/page.tsx
│   │   ├── register/page.tsx
│   │   └── verify-email/page.tsx
│   ├── (dashboard)/            # 主應用頁面群組（需登入）
│   │   ├── layout.tsx          # 共用 Layout（導覽列）
│   │   ├── today/page.tsx      # 今日回顧填寫
│   │   ├── history/page.tsx    # 歷史回顧瀏覽
│   │   ├── habits/page.tsx     # 習慣管理
│   │   ├── goals/page.tsx      # 目標管理
│   │   ├── stats/page.tsx      # 統計 Dashboard
│   │   └── settings/page.tsx   # 個人設定
│   ├── layout.tsx              # 根 Layout
│   └── page.tsx                # 首頁（登入導向）
├── components/
│   ├── ui/                     # shadcn/ui 基礎元件
│   ├── review/                 # 回顧表單相關元件
│   │   ├── TaskSection.tsx
│   │   ├── MoodSection.tsx
│   │   ├── HabitCheckSection.tsx
│   │   ├── GoalProgressSection.tsx
│   │   └── FreeNoteSection.tsx
│   ├── stats/                  # 統計圖表元件
│   │   ├── ReviewHeatmap.tsx
│   │   ├── MoodTrendChart.tsx
│   │   ├── HabitStreakCard.tsx
│   │   └── MoodDistributionChart.tsx
│   └── shared/                 # 通用共用元件
│       ├── Navbar.tsx
│       └── ProtectedRoute.tsx
├── lib/
│   ├── api/                    # API 呼叫函數
│   │   ├── auth.ts
│   │   ├── reviews.ts
│   │   ├── habits.ts
│   │   ├── goals.ts
│   │   └── stats.ts
│   ├── hooks/                  # 自訂 React Hooks
│   └── utils.ts
├── types/                      # TypeScript 型別定義
└── public/
```

### 4.2 狀態管理策略

| 狀態類型 | 管理方式 |
|----------|----------|
| 使用者 Session | Next.js Cookies + JWT（儲存於 HttpOnly Cookie） |
| 伺服器資料 | React Query（TanStack Query）快取與同步 |
| 表單狀態 | React Hook Form + Zod 驗證 |
| 全域 UI 狀態 | React Context（輕量，僅主題與通知） |

### 4.3 頁面路由規劃

| 路徑 | 頁面 | 說明 |
|------|------|------|
| `/` | 首頁 | 已登入導向今日回顧，未登入導向登入頁 |
| `/login` | 登入 | Email/密碼 + OAuth 登入 |
| `/register` | 註冊 | Email 註冊表單 |
| `/verify-email` | Email 驗證 | 驗證信連結導向頁 |
| `/today` | 今日回顧 | 核心功能，當日回顧填寫 |
| `/history` | 歷史紀錄 | 瀏覽過去回顧（唯讀） |
| `/habits` | 習慣管理 | CRUD 習慣清單 |
| `/goals` | 目標管理 | CRUD 目標清單 |
| `/stats` | 統計儀表板 | 視覺化圖表 |
| `/settings` | 個人設定 | 帳號資訊與提醒設定 |

---

## 5. 後端架構設計

### 5.1 目錄結構

```
backend/
├── app/
│   ├── main.py                 # FastAPI 應用入口
│   ├── config.py               # 環境變數與設定
│   ├── database.py             # 資料庫連線與 Session
│   ├── dependencies.py         # 共用依賴（get_db, get_current_user）
│   ├── models/                 # SQLAlchemy ORM 模型
│   │   ├── user.py
│   │   ├── review.py
│   │   ├── habit.py
│   │   └── goal.py
│   ├── schemas/                # Pydantic 請求/回應 Schema
│   │   ├── auth.py
│   │   ├── review.py
│   │   ├── habit.py
│   │   ├── goal.py
│   │   └── stats.py
│   ├── routers/                # API 路由
│   │   ├── auth.py
│   │   ├── reviews.py
│   │   ├── habits.py
│   │   ├── goals.py
│   │   ├── stats.py
│   │   └── users.py
│   ├── services/               # 業務邏輯層
│   │   ├── auth_service.py
│   │   ├── review_service.py
│   │   ├── habit_service.py
│   │   ├── goal_service.py
│   │   ├── stats_service.py
│   │   └── email_service.py
│   ├── core/
│   │   ├── security.py         # JWT、密碼加密
│   │   └── oauth.py            # Google/GitHub OAuth 處理
│   └── scheduler/
│       └── reminder.py         # APScheduler 每日提醒任務
├── migrations/                 # Alembic 資料庫遷移檔
├── tests/
│   ├── test_auth.py
│   ├── test_reviews.py
│   ├── test_habits.py
│   ├── test_stats.py
│   └── conftest.py
├── requirements.txt
└── Dockerfile
```

### 5.2 分層架構

```
Router（路由層）
    ↓  請求/回應 Schema 驗證
Service（業務邏輯層）
    ↓  資料存取
Model / ORM（資料層）
    ↓
PostgreSQL
```

- **Router**：負責 HTTP 方法映射、路徑參數解析、權限檢查注入
- **Service**：封裝所有業務規則（如回顧鎖定邏輯、習慣 streak 計算）
- **Model**：SQLAlchemy 定義資料表結構與關聯

### 5.3 Middleware

| Middleware | 功能 |
|------------|------|
| CORS | 允許前端域名跨域請求 |
| JWT Auth | 驗證 Bearer Token，注入 `current_user` |
| Rate Limiting | 登入/註冊端點每 IP 每分鐘限制請求次數 |
| Request Logging | 記錄每次請求方法、路徑、狀態碼 |

---

## 6. 資料庫設計

### 6.1 Entity-Relationship 概觀

```
users ──┬── user_oauth (1:N)
        ├── daily_reviews (1:N) ──┬── review_tasks (1:N)
        │                         ├── gratitude_items (1:N)
        │                         ├── habit_logs (1:N) ──── habits
        │                         └── goal_daily_progress (1:N) ── goals
        ├── habits (1:N)
        └── goals (1:N)
```

### 6.2 資料表定義

#### users

| 欄位 | 型別 | 說明 |
|------|------|------|
| id | UUID (PK) | 主鍵 |
| email | VARCHAR(255) UNIQUE | 電子信箱 |
| password_hash | VARCHAR(255) NULLABLE | bcrypt 加密（OAuth 用戶為 NULL） |
| display_name | VARCHAR(100) | 顯示名稱 |
| is_email_verified | BOOLEAN | Email 驗證狀態 |
| reminder_enabled | BOOLEAN | 提醒通知開關（預設 true） |
| reminder_time | TIME | 提醒時間（預設 21:00） |
| created_at | TIMESTAMP | 建立時間 |
| updated_at | TIMESTAMP | 更新時間 |

**索引**：`email`（UNIQUE）

#### user_oauth

| 欄位 | 型別 | 說明 |
|------|------|------|
| id | UUID (PK) | 主鍵 |
| user_id | UUID (FK → users) | 關聯使用者 |
| provider | VARCHAR(20) | `google` 或 `github` |
| provider_user_id | VARCHAR(255) | OAuth 提供者的使用者 ID |
| created_at | TIMESTAMP | 建立時間 |

**索引**：`(provider, provider_user_id)`（UNIQUE）

#### daily_reviews

| 欄位 | 型別 | 說明 |
|------|------|------|
| id | UUID (PK) | 主鍵 |
| user_id | UUID (FK → users) | 關聯使用者 |
| date | DATE | 回顧日期 |
| mood_score | SMALLINT | 心情評分（1–5） |
| free_note | TEXT NULLABLE | 自由筆記（Markdown） |
| is_locked | BOOLEAN | 是否鎖定（跨天後 true） |
| created_at | TIMESTAMP | 建立時間 |
| updated_at | TIMESTAMP | 更新時間 |

**索引**：`(user_id, date)`（UNIQUE）；`user_id`；`date`

#### review_tasks

| 欄位 | 型別 | 說明 |
|------|------|------|
| id | UUID (PK) | 主鍵 |
| review_id | UUID (FK → daily_reviews) | 關聯回顧 |
| content | TEXT | 任務內容 |
| is_completed | BOOLEAN | 是否完成 |
| task_type | VARCHAR(20) | `done`（已完成）或 `not_done`（未完成） |
| sort_order | INTEGER | 排序 |

**索引**：`review_id`

#### gratitude_items

| 欄位 | 型別 | 說明 |
|------|------|------|
| id | UUID (PK) | 主鍵 |
| review_id | UUID (FK → daily_reviews) | 關聯回顧 |
| content | TEXT | 感恩內容 |
| item_order | SMALLINT | 順序（1–3） |

**索引**：`review_id`

#### habits

| 欄位 | 型別 | 說明 |
|------|------|------|
| id | UUID (PK) | 主鍵 |
| user_id | UUID (FK → users) | 關聯使用者 |
| name | VARCHAR(100) | 習慣名稱 |
| description | TEXT NULLABLE | 習慣描述 |
| start_date | DATE | 習慣開始日期 |
| is_archived | BOOLEAN | 是否封存（預設 false） |
| created_at | TIMESTAMP | 建立時間 |

**索引**：`user_id`；`(user_id, is_archived)`

#### habit_logs

| 欄位 | 型別 | 說明 |
|------|------|------|
| id | UUID (PK) | 主鍵 |
| review_id | UUID (FK → daily_reviews) | 關聯回顧 |
| habit_id | UUID (FK → habits) | 關聯習慣 |
| is_completed | BOOLEAN | 是否打卡完成 |

**索引**：`(review_id, habit_id)`（UNIQUE）；`habit_id`

#### goals

| 欄位 | 型別 | 說明 |
|------|------|------|
| id | UUID (PK) | 主鍵 |
| user_id | UUID (FK → users) | 關聯使用者 |
| title | VARCHAR(200) | 目標標題 |
| description | TEXT NULLABLE | 目標描述 |
| due_date | DATE NULLABLE | 截止日期 |
| status | VARCHAR(20) | `active`、`completed`、`archived` |
| created_at | TIMESTAMP | 建立時間 |
| updated_at | TIMESTAMP | 更新時間 |

**索引**：`(user_id, status)`；`user_id`

#### goal_daily_progress

| 欄位 | 型別 | 說明 |
|------|------|------|
| id | UUID (PK) | 主鍵 |
| review_id | UUID (FK → daily_reviews) | 關聯回顧 |
| goal_id | UUID (FK → goals) | 關聯目標 |
| has_progressed | BOOLEAN | 今日是否有推進 |

**索引**：`(review_id, goal_id)`（UNIQUE）；`goal_id`

### 6.3 鎖定機制說明

`daily_reviews.is_locked` 由後端在每次存取時自動判斷：
- 若 `date < 今日日期（UTC+8）`，回應時附帶 `is_locked: true`
- 前端鎖定後顯示唯讀模式
- 後端 UPDATE 端點亦驗證此條件，鎖定後拒絕修改（回傳 403）

---

## 7. API 設計概覽

所有 API 路徑前綴為 `/api/v1`，回應格式統一為 JSON。

### 7.1 Auth（驗證）

| Method | 路徑 | 說明 | 需驗證 |
|--------|------|------|--------|
| POST | `/auth/register` | Email 註冊 | ✗ |
| POST | `/auth/login` | Email 登入，回傳 JWT | ✗ |
| GET | `/auth/verify-email` | 驗證 Email Token | ✗ |
| GET | `/auth/google` | Google OAuth 啟動 | ✗ |
| GET | `/auth/google/callback` | Google OAuth Callback | ✗ |
| GET | `/auth/github` | GitHub OAuth 啟動 | ✗ |
| GET | `/auth/github/callback` | GitHub OAuth Callback | ✗ |
| POST | `/auth/logout` | 登出（JWT 黑名單） | ✓ |

### 7.2 Users（使用者）

| Method | 路徑 | 說明 | 需驗證 |
|--------|------|------|--------|
| GET | `/users/me` | 取得當前使用者資訊 | ✓ |
| PATCH | `/users/me` | 更新顯示名稱 / 提醒設定 | ✓ |
| POST | `/users/me/change-password` | 修改密碼 | ✓ |

### 7.3 Reviews（每日回顧）

| Method | 路徑 | 說明 | 需驗證 |
|--------|------|------|--------|
| GET | `/reviews/today` | 取得今日回顧（不存在則回傳 404） | ✓ |
| POST | `/reviews/today` | 建立今日回顧 | ✓ |
| PUT | `/reviews/today` | 更新今日回顧（已鎖定則 403） | ✓ |
| GET | `/reviews` | 取得歷史回顧清單（分頁） | ✓ |
| GET | `/reviews/{date}` | 取得特定日期回顧 | ✓ |

### 7.4 Habits（習慣）

| Method | 路徑 | 說明 | 需驗證 |
|--------|------|------|--------|
| GET | `/habits` | 取得所有習慣（含封存篩選） | ✓ |
| POST | `/habits` | 建立習慣 | ✓ |
| PATCH | `/habits/{id}` | 編輯習慣名稱/描述 | ✓ |
| POST | `/habits/{id}/archive` | 封存習慣 | ✓ |

### 7.5 Goals（目標）

| Method | 路徑 | 說明 | 需驗證 |
|--------|------|------|--------|
| GET | `/goals` | 取得所有目標（依狀態篩選） | ✓ |
| POST | `/goals` | 建立目標 | ✓ |
| PATCH | `/goals/{id}` | 編輯目標（含狀態變更） | ✓ |

### 7.6 Stats（統計）

| Method | 路徑 | 說明 | 需驗證 |
|--------|------|------|--------|
| GET | `/stats/heatmap` | 年曆熱圖資料（過去 365 天） | ✓ |
| GET | `/stats/mood-trend` | 心情趨勢（`?days=7` 或 `30`） | ✓ |
| GET | `/stats/mood-distribution` | 心情分佈（`?period=week/month`） | ✓ |
| GET | `/stats/habit-streaks` | 習慣連續天數統計 | ✓ |
| GET | `/stats/habit-completion` | 習慣本月完成率 | ✓ |

---

## 8. 認證與安全設計

### 8.1 JWT 策略

```
登入成功
    → 後端簽發 Access Token（有效期 1 小時）
    → 後端簽發 Refresh Token（有效期 7 天，儲存於 HttpOnly Cookie）
    → 前端以 Bearer Token 攜帶 Access Token 進行 API 請求
    → Access Token 過期後，前端以 Refresh Token 換取新 Access Token
```

- **Access Token**：存於前端記憶體（非 localStorage，防 XSS）
- **Refresh Token**：存於 HttpOnly Cookie（防 JavaScript 存取）
- **Token Rotation**：每次 Refresh 後失效舊 Token

### 8.2 OAuth 流程

```
使用者點擊「Google 登入」
    → 後端產生 OAuth state（CSRF 保護）
    → 導向 Google OAuth 授權頁
    → Google 回調後端 Callback URL
    → 後端驗證 state，取得 user info
    → 若 email 已存在 → 關聯帳號或直接登入
    → 若 email 不存在 → 建立新使用者
    → 回傳 JWT，重導向前端
```

### 8.3 密碼安全

- 使用 `bcrypt`（work factor ≥ 12）加密儲存
- 密碼強度最低要求：8 碼以上
- 修改密碼需輸入舊密碼驗證
- Email 驗證 Token 使用 UUID v4，有效期 24 小時

### 8.4 API 安全

| 措施 | 實作方式 |
|------|----------|
| HTTPS 強制 | Vercel / Railway 自動啟用 TLS |
| CORS 限制 | 僅允許前端域名，明確列出允許 Origin |
| Rate Limiting | `slowapi` 套件，登入/註冊端點：每 IP 每分鐘 10 次 |
| SQL Injection | SQLAlchemy ORM 參數化查詢 |
| XSS 防護 | React 預設 escape、不直接 dangerouslySetInnerHTML |
| CSRF | JWT Bearer Token（非 Cookie-based）+ SameSite Cookie |

---

## 9. 功能模組設計

### 9.1 F1 — 使用者系統模組

**Email 驗證流程**：
```
註冊 → 後端存入 users（is_email_verified=false）
     → Email Service 發送驗證信（含 UUID token）
     → 使用者點擊連結 → GET /auth/verify-email?token=<uuid>
     → 後端更新 is_email_verified=true
     → 導向登入頁
```

**個人設定更新**：支援部分更新（PATCH），每欄位獨立驗證。

### 9.2 F2 — 每日回顧模組

**每日回顧生命週期**：
```
當日 00:00 → 可建立新回顧
當日 23:59 → 回顧仍可編輯
次日 00:00 → is_locked = true（後端判斷，不存資料庫）
```

**回顧建立/更新邏輯**：
- 前端送出回顧時，一次性包含所有區塊（tasks、mood、gratitude、habits、goals、free_note）
- 後端使用資料庫事務（Transaction）確保原子性寫入
- 每位使用者每日唯一限制由 `(user_id, date)` 的 UNIQUE 索引保障

**Markdown 渲染**：
- 前端使用 `react-markdown` 套件渲染自由筆記
- 支援：粗體、斜體、清單（有序/無序）、標題（H1-H3）

### 9.3 F3 — 習慣管理模組

**習慣打卡邏輯**：
- 每日回顧時，前端從 `GET /habits?archived=false` 取得啟用中習慣
- 習慣勾選狀態附屬於當日回顧（`habit_logs`），非獨立打卡
- 封存習慣：`is_archived=true`，不再出現於回顧習慣區，歷史記錄保留

**Streak 計算（後端 Service）**：
```python
def calculate_streak(habit_id, today):
    # 從今日往前連續查詢 habit_logs
    # 找到第一個 is_completed=false 或無記錄的日期即停止
    # 回傳 current_streak 與 max_streak
```

### 9.4 F4 — 目標管理模組

**目標進度連結**：
- 回顧填寫時，顯示所有 `status=active` 的目標
- 使用者勾選「今日有推進此目標」→ 寫入 `goal_daily_progress`
- 目標狀態變更（`active` → `completed` / `archived`）透過 PATCH 端點

### 9.5 F5 — 統計 Dashboard 模組

**熱圖資料結構**：
```json
GET /stats/heatmap
Response: {
  "data": [
    { "date": "2025-01-01", "has_review": true },
    { "date": "2025-01-02", "has_review": false },
    ...
  ]
}
```

**心情趨勢**：
```json
GET /stats/mood-trend?days=30
Response: {
  "data": [
    { "date": "2025-05-01", "mood_score": 4 },
    ...
  ]
}
```

**效能優化**：統計查詢使用 `daily_reviews.date` 欄位索引 + 日期範圍查詢，確保 1 秒內回應。

### 9.6 F6 — 每日提醒通知模組

**APScheduler 排程策略**：
```
每分鐘觸發排程 → 查詢當前時間與各時區使用者的 reminder_time 比對
              → 篩選出需要發送提醒且當天尚未完成回顧的使用者
              → 批次呼叫 Email Service 發送提醒信
```

**Email 內容**：
- 主旨：「提醒您：今日回顧尚未完成」
- 內文：簡短說明 + 直達回顧頁面的連結
- 條件：`reminder_enabled=true` 且當日 `daily_reviews` 不存在

---

## 10. UI/UX 風格設計

### 10.1 設計系統

| 元素 | 規格 |
|------|------|
| **設計語言** | 簡潔、現代、低刺激（Minimal & Calm） |
| **主色調** | 靛藍色系（Indigo）#4F46E5 — 代表專注與沉靜 |
| **輔助色** | 成功綠 #10B981、警示橘 #F59E0B、錯誤紅 #EF4444 |
| **背景色** | 淺灰 #F9FAFB（Light）/ 深藍灰 #0F172A（Dark） |
| **文字色** | 主文字 #111827、次文字 #6B7280 |
| **字型** | 主要：Noto Sans TC（中文）/ Inter（英文）|
| **圓角** | 小元件 4px，卡片 8px，大型容器 12px |
| **陰影** | 輕微陰影（`shadow-sm`），避免視覺雜亂 |

### 10.2 響應式設計策略

| 斷點 | 說明 | 優先級 |
|------|------|--------|
| `lg` (1024px+) | 桌面版，側邊導覽列 | **主要** |
| `md` (768px+) | 平板版，可收合導覽列 | 次要 |
| `sm` (640px+) | 大手機，單欄排版 | 基本可用 |

### 10.3 核心頁面佈局

**今日回顧頁（桌面版）**：
```
┌─────────────────────────────────────────────┐
│  Sidebar        │  主內容區                  │
│  ───────────    │  ─────────────────────────  │
│  今日回顧        │  [日期標題]                 │
│  歷史紀錄        │                             │
│  習慣管理        │  任務區（已完成 / 未完成）  │
│  目標管理        │  情緒區（評分 + 感恩）      │
│  統計Dashboard   │  習慣打卡區                 │
│  個人設定        │  目標進度區                 │
│                 │  自由筆記區                  │
│                 │  [儲存按鈕]                  │
└─────────────────────────────────────────────┘
```

**統計 Dashboard（桌面版）**：
```
┌───────────────────────────────────────────────────┐
│  年曆熱圖（全寬）                                   │
├─────────────────────┬─────────────────────────────┤
│  心情趨勢折線圖      │  心情分佈圓餅圖               │
│  [7天 / 30天切換]   │  [本週 / 本月切換]            │
├─────────────────────┴─────────────────────────────┤
│  習慣完成率卡片群（水平捲動）                        │
│  [習慣1: 73%] [習慣2: 90%] [習慣3: 60%] ...       │
└───────────────────────────────────────────────────┘
```

### 10.4 互動設計原則

- **即時反饋**：表單送出時顯示 Loading Spinner，成功/失敗皆有 Toast 通知
- **防呆設計**：離開回顧頁面前，若有未儲存變更，跳出確認提示
- **鍵盤友善**：Tab 順序正確，Enter 可觸發主要操作
- **唯讀模式**：鎖定的回顧以灰色背景與鎖頭圖示明確標示不可編輯
- **空狀態設計**：首次使用時各頁面顯示引導說明與快速開始按鈕

### 10.5 圖表套件

| 圖表 | 套件 |
|------|------|
| 年曆熱圖 | `react-calendar-heatmap` |
| 折線圖 / 長條圖 | `recharts` |
| 圓餅圖 / 甜甜圈圖 | `recharts` |

---

## 11. 非功能需求設計

### 11.1 效能

| 指標 | 目標 |
|------|------|
| Dashboard 統計 API 回應時間 | ≤ 1 秒（P95） |
| 今日回顧頁面初次載入 | ≤ 2 秒（含 SSR） |
| 前端 LCP (Largest Contentful Paint) | ≤ 2.5 秒 |

**效能優化手段**：
- PostgreSQL 針對所有查詢的 `user_id`、`date` 欄位加索引
- 統計查詢使用 SQL 聚合函數（`COUNT`、`AVG`、`GROUP BY`）替代應用層計算
- Next.js SSR 預渲染初始頁面資料
- React Query 快取 API 回應，避免重複請求

### 11.2 安全性

詳見第 8 節。遵循 OWASP Top 10 防護原則。

### 11.3 測試策略

| 層次 | 工具 | 覆蓋目標 |
|------|------|----------|
| 後端單元測試 | pytest + pytest-asyncio | 核心業務邏輯（習慣 streak、統計計算、鎖定判斷） |
| 後端 API 整合測試 | pytest + httpx | 所有 API 端點（含驗證、邊界條件） |
| 前端元件測試 | Vitest + Testing Library | 核心表單元件、圖表資料處理 |
| E2E 測試（選配） | Playwright | 主要使用者旅程（註冊→填寫回顧→查看統計） |

### 11.4 監控與日誌

| 工具 | 用途 |
|------|------|
| Railway / Render 內建日誌 | API 請求日誌、錯誤追蹤 |
| Sentry（選配） | 前後端錯誤回報 |
| Vercel Analytics | 前端效能監控 |

---

## 12. 部署架構

### 12.1 環境規劃

| 環境 | 前端 | 後端 | 資料庫 |
|------|------|------|--------|
| **開發（Local）** | `npm run dev` | `uvicorn --reload` | Docker PostgreSQL |
| **預覽（Preview）** | Vercel Preview URL | Railway PR 環境 | Railway DB（測試用） |
| **正式（Production）** | Vercel Production | Railway Production | Railway PostgreSQL |

### 12.2 CI/CD 流程

```
Push to GitHub
    → GitHub Actions 觸發
    → 後端：pytest 測試
    → 前端：TypeScript 型別檢查 + Vitest
    → 測試通過 → 自動部署
        - 前端 → Vercel（自動偵測 Next.js）
        - 後端 → Railway（Docker build & deploy）
```

### 12.3 環境變數管理

**後端（`.env`）**：
```
DATABASE_URL=postgresql://...
SECRET_KEY=<JWT 簽名金鑰>
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=7
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
GITHUB_CLIENT_ID=...
GITHUB_CLIENT_SECRET=...
SENDGRID_API_KEY=...
FRONTEND_URL=https://your-app.vercel.app
```

**前端（`.env.local`）**：
```
NEXT_PUBLIC_API_URL=https://your-api.railway.app
```

---

## 13. 開發優先級與分階段計畫

### Phase 1 — 核心 MVP（週 1-3）

**目標**：可完整執行一次每日回顧的最小可用版本

| 功能 | 模組 |
|------|------|
| Email 註冊/登入 | F1 |
| 建立、更新今日回顧（任務區、情緒區、自由筆記） | F2 |
| 回顧鎖定機制 | F2 |
| 習慣建立與每日打卡 | F3 |

### Phase 2 — 功能完善（週 4-5）

| 功能 | 模組 |
|------|------|
| Google / GitHub OAuth 登入 | F1 |
| 目標管理與每日進度連結 | F4 |
| 基本統計（熱圖、心情趨勢） | F5 |
| 個人設定頁 | F1 |

### Phase 3 — 統計完整 + 通知（週 6-7）

| 功能 | 模組 |
|------|------|
| 習慣 Streak 統計 | F5 |
| 心情分佈、習慣完成率 | F5 |
| 每日 Email 提醒排程 | F6 |
| 歷史回顧瀏覽頁 | F2 |

### Phase 4 — 品質加固（週 8）

| 工作項目 | 說明 |
|----------|------|
| 後端 API 測試覆蓋率 ≥ 80% | 核心端點全覆蓋 |
| 效能優化 | 索引調整、查詢優化 |
| 安全審查 | Rate Limit、CORS、HTTPS 確認 |
| 響應式樣式調整 | 平板與手機基本可用 |

---

*文件版本：v1.0*
*建立日期：2026-06-28*
