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
    - {LineId: {MemberId: string, MemberName: string, LineName: string, BindDate: Datetime}}
- Sessions (工作階段)
    - {MemberId: {SessionToken: string}}
- Members (會友)
    - {MemberId: {MemberName: string, BindDate: Datetime, isBind: boolean}}
- Devotions (奉獻明細)
    - {DevotionId: {MemberId: string, MemberName: string, CategoryId: string, Amount: number, DevotionDate: Datetime}}
- Categories (奉獻類別)
    - {CategoryId: {CategoryName: string, Type: string}}

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