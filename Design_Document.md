# 設計文件

## 技術堆疊
- 前端：HTML, JavaScript
- 樣式：Tailwind CSS
- 後端：Python, FastAPI
- API 託管：Google Cloud Run
- 資料庫：Google Cloud Firestore
- 網站託管：Google Firebase Hosting
- 原始碼保存：Github
- CI/CD：Github Actions

## 資料庫設計
- Users (使用者)
    - {LineId: {MemberId: string, MemberName: string (審核後隱碼), LineName: string, IsApproved: boolean, ApplyDate: Datetime, BindDate: Datetime}}
- Sessions (工作階段)
    - {MemberId: {SessionToken: string}}
- Members (會友)
    - {MemberId: {Name: string (已隱碼), BindDate: Datetime, isBind: boolean}}
- Devotions (奉獻明細)
    - {DevotionId: {MemberId: string, CategoryId: string, Amount: number, DevotionDate: Datetime}}
- Categories (奉獻類別)
    - {CategoryId: {CategoryName: string, Type: string}}
- AuditLogs (稽核日誌)
    - {LogId: {OperatorType: "Admin"|"User", OperatorId: string, Action: string, TargetId: string, Details: map, Timestamp: Datetime}}
    - *評估決策：考量專案規模與即時顯示需求，優先使用 Firestore 儲存日誌。BigQuery 做為未來長期分析之擴充選項。*
- UserStats (使用者統計快取)
    - {MemberId: {TotalAmount: number, TotalCount: number, LastDevotionDate: Datetime, LastUpdate: Datetime}}
    - *用於優化首頁載入效能，避免每次登入都重新計算所有明細。*

## 使用者介面設計
- 使用者介面：行動裝置優先設計
- 管理者介面：桌面裝置優先設計

## 安全性設計
- 登入：LINE Login
- 工作階段：JWT
- CSRF
- CORS
- 呼叫頻率限制 (Rate Limit)

## 架構限制
- 同時使用人數在10人以內時，載入時間小於3秒
- 沒有註冊登入的人員不可使用

## 未來增強功能
- 大量資料上傳優化：引入 Pub/Sub 非同步處理機制，以支援萬筆以上級別的匯入。
- 通知整合：串接 LINE Messaging API，於資料更新或綁定異動時推播通知。
- 進階分析：將 AuditLogs 與奉獻資料同步至 BigQuery，進行長期趨勢分析與視覺化報表。