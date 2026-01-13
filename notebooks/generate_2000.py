# V3 대규모 데이터 생성기 - 2000개 비즈니스 시나리오
import json
import random
import os
from kelron_config import SYSTEM_PROMPTS

# 부서별 시나리오 템플릿
SCENARIOS = {
    "ko": {
        "재무": [
            ("거래처 {company}에서 대금 지급이 {days}일째 늦어지고 있어. 독촉 메일 써줘. 정중하지만 기한 내 미입금 시 서비스 중단 경고 포함.", 
             "제목: [중요] 미지급 대금 관련 입금 요청\n\n{company} 담당자님께,\n\n안녕하십니까, Cokee 재무팀입니다.\n\n발행된 송장 관련 입금이 {days}일 경과되어 안내드립니다.\n\n• 송장번호: [번호]\n• 금액: [금액]\n• 납부기한: [기한]\n\n{deadline}까지 입금 확인이 필요하며, 기한 내 미입금 시 서비스 일시 중단이 불가피합니다.\n\n문의사항이 있으시면 연락 부탁드립니다.\n\n감사합니다."),
            ("이번 분기 예산이 {percent}% 소진됐어. 각 부서장에게 긴축 운영 요청 메일 써줘.", 
             "제목: [중요] Q{quarter} 예산 현황 및 긴축 요청\n\n각 부서장님께,\n\n현재 분기 예산 {percent}% 소진되어 긴축 운영 요청드립니다.\n\n■ 요청사항\n• 필수 경비 외 지출 보류\n• 신규 품의 사전 협의\n• 출장/접대비 최소화\n\n협조 감사드립니다."),
            ("{month}월 경비 정산 마감 안내 공지 써줘. 기한은 {deadline}까지고, 미제출 시 다음 달 급여 반영 안 된다고.",
             "제목: [필독] {month}월 경비정산 마감 안내 ({deadline}까지)\n\n임직원 여러분께,\n\n{month}월 경비정산 마감일 안내드립니다.\n\n• 마감: {deadline} 18:00\n• 방법: 경비정산 시스템 제출\n\n⚠️ 기한 후 제출 시 익월 급여 반영 불가\n\n경리팀 드림"),
        ],
        "인사": [
            ("신입사원 {count}명 온보딩 일정 짜줘. 오전 OT, 점심 회식, 오후 장비세팅이랑 멘토 배정.",
             "신입사원 온보딩 일정\n\n■ 대상: 신입 {count}명\n\n[오전]\n• 09:00 출근/자리 안내\n• 09:30-11:30 OT (회사소개, 조직도, 보안교육)\n• 11:30 사원증 발급\n\n[점심]\n• 12:00-13:30 환영 회식\n\n[오후]\n• 13:30-15:00 장비 세팅\n• 15:00-16:00 멘토 배정 및 1:1\n• 16:00-17:00 부서 투어"),
            ("퇴직자 {name}님 송별회 안내 메일 써줘. {date}에 {place}에서.",
             "제목: [{name}님 송별회] 안내\n\n안녕하세요,\n\n{name}님 송별회를 아래와 같이 진행합니다.\n\n• 일시: {date}\n• 장소: {place}\n• 회비: [금액]\n\n많은 참석 부탁드립니다.\n\n인사팀 드림"),
            ("연차 사용 촉진 안내 공지 써줘. 잔여 연차 {days}일 이상인 직원 대상.",
             "제목: [안내] 연차 사용 촉진\n\n잔여 연차 {days}일 이상 직원분들께,\n\n연차 소진 촉진 안내드립니다. 연말까지 미사용 시 소멸됩니다.\n\n• 대상: 잔여 {days}일 이상\n• 권장: 분기 내 50% 사용\n\n일정 조율 후 사용 부탁드립니다.\n\n인사팀"),
        ],
        "IT": [
            ("전사 비밀번호 변경 공지 써줘. {deadline}까지 필수고, 미변경 시 계정 잠금.",
             "제목: [필독] 비밀번호 변경 필수 ({deadline}까지)\n\n전 임직원께,\n\n보안 정책에 따라 비밀번호 변경 시행합니다.\n\n• 기한: {deadline} 18:00\n• 방법: 마이페이지 → 비밀번호 변경\n• 규칙: 8자 이상 (대/소/숫자/특수)\n\n⚠️ 미변경 시 계정 자동 잠금\n\nIT보안팀"),
            ("시스템 점검 안내 써줘. {date} {time}부터 {duration}시간 동안 서비스 중단.",
             "제목: [공지] 시스템 정기점검 안내\n\n안녕하세요,\n\n아래와 같이 시스템 점검 예정입니다.\n\n• 일시: {date} {time} ~ ({duration}시간 소요)\n• 영향: 전 서비스 접속 불가\n• 조치: 사전 데이터 저장 요망\n\n불편 양해 바랍니다.\n\nIT팀"),
            ("피싱 메일 경고 공지 써줘. '{subject}' 제목으로 오는 메일 주의.",
             "제목: 🚨 피싱 메일 주의\n\n전 임직원께,\n\n'{subject}' 제목의 피싱 메일이 유포 중입니다.\n\n■ 특징\n• 외부 도메인 발신\n• 링크 클릭 유도\n\n■ 조치\n• 클릭 금지, 즉시 삭제\n• 클릭 시 IT보안팀 연락\n\nIT보안팀"),
        ],
        "영업": [
            ("{company}에 보낸 제안서 팔로업 메일 써줘. 2주 지났고, 이번 달 내 결정 요청.",
             "제목: 제안서 검토 현황 문의 ({company})\n\n{company} 담당자님께,\n\n안녕하세요, Cokee 영업팀입니다.\n\n2주 전 송부드린 제안서 검토 현황 문의드립니다.\n\n이번 달 내 결정 주시면 현 조건 유지 가능합니다.\n\n궁금한 점 있으시면 연락 부탁드립니다.\n\n감사합니다."),
            ("경쟁사 대비 우리 제품 장점 정리해줘. 가격, 기능, A/S 측면에서. 경쟁사는 {comp1}, {comp2}.",
             "경쟁사 대비 비교표\n\n| 항목 | Cokee | {comp1} | {comp2} |\n|------|-------|--------|--------|\n| 가격 | 월 9.9만 | 월 12.9만 | 월 8.9만 |\n| 핵심기능 | AI+리포트 | 기본 | AI만 |\n| 사용자 | 무제한 | 10명 | 50명 |\n| A/S | 24h | 48h | 72h |\n\n**강점**: 가성비, 빠른 A/S"),
            ("신규 거래처 {company} 첫 미팅 후 감사 메일 써줘.",
             "제목: 미팅 감사드립니다 ({company})\n\n{company} 담당자님께,\n\n오늘 미팅 감사드립니다.\n\n말씀하신 사항 정리하여 제안서 송부드리겠습니다.\n\n추가 문의사항 있으시면 연락 부탁드립니다.\n\n감사합니다.\nCokee 영업팀"),
        ],
        "마케팅": [
            ("{month}월 SNS 광고 성과 보고서 써줘. 클릭률 {ctr}% 상승, 전환율 {cvr}% 상승, 예산은 {budget}% 증가.",
             "제목: {month}월 SNS 광고 성과 보고\n\n■ 주요 지표 (전월 대비)\n• 클릭률: +{ctr}%\n• 전환율: +{cvr}%\n• 예산: +{budget}%\n\n■ 분석\n성과 개선되었으나 예산 증가율 대비 효율성 제고 필요\n\n■ 개선안\n• 고성과 크리에이티브 집중\n• 타겟 세분화"),
            ("신제품 {product} 런칭 보도자료 초안 써줘.",
             "보도자료\n\nCokee, {product} 출시… \"업계 혁신 이끈다\"\n\n- {product} 주요 특징 및 가격\n- CEO 코멘트\n- 출시 일정 및 구매처\n\n[문의]\nCokee 마케팅팀\npress@cokee.io"),
            ("{event} 행사 참가 안내 메일 써줘. {date}에 {location}에서.",
             "제목: [{event}] 참가 안내\n\n안녕하세요,\n\nCokee가 {event}에 참가합니다.\n\n• 일시: {date}\n• 장소: {location}\n• 부스: [번호]\n\n많은 관심 부탁드립니다.\n\n마케팅팀"),
        ],
        "총무": [
            ("사무실 이전 안내 써줘. {date}부터 {address}로. 전날은 재택.",
             "제목: [공지] 사무실 이전 ({date}~)\n\n■ 신규 주소: {address}\n■ 이사일: 전날 (재택근무)\n■ 출근일: {date}~\n\n개인 물품 박스 정리 부탁드립니다.\n\n총무팀"),
            ("에어컨 점검 안내 써줘. {date} 오전 중 공조 정지.",
             "제목: [안내] 공조 점검 ({date} 오전)\n\n{date} 오전 9-12시 공조 점검으로 냉난방 정지됩니다.\n\n조절 가능한 복장 권장드립니다.\n\n총무팀"),
            ("회의실 예약 규정 변경 안내 써줘. 최대 {hours}시간, 당일취소 페널티.",
             "제목: [안내] 회의실 예약 규정 변경\n\n■ 변경사항\n• 최대 예약: {hours}시간\n• 당일 취소: 페널티 부과\n• 노쇼 3회: 예약 제한\n\n효율적 사용 협조 바랍니다.\n\n총무팀"),
        ],
        "개발": [
            ("버그 수정 완료 안내 메일 써줘. '{bug}' 이슈 해결됨.",
             "제목: [완료] '{bug}' 수정 안내\n\n안녕하세요,\n\n'{bug}' 이슈 수정 완료 안내드립니다.\n\n• 원인: [원인]\n• 조치: [조치]\n• 배포: 완료\n\n재발 방지 모니터링 강화했습니다.\n\n개발팀"),
            ("신규 기능 내부 릴리즈 노트 써줘. 기능명 '{feature}', 주요 변경사항 3가지.",
             "# 릴리즈 노트: {feature}\n\n## 주요 변경\n1. [변경1]\n2. [변경2]\n3. [변경3]\n\n## 영향범위\n• API: /api/v2/{feature}\n• 롤아웃: 베타 먼저\n\n## 문의\n#dev-support"),
            ("장애 발생 시 고객 공지문 써줘. '{issue}' 현상, 복구 중.",
             "【장애 안내】\n\n'{issue}' 현상 발생 중입니다.\n\n• 발생: [시각]\n• 영향: 일부 접속 불가\n• 상태: 복구 작업 중\n\n복구 완료 시 재안내드리겠습니다.\n\n이용에 불편드려 죄송합니다."),
        ],
        "법무": [
            ("NDA 체결 요청 메일 써줘. {company}와 협력 전.",
             "제목: NDA 체결 요청 ({company})\n\n{company} 담당자님께,\n\n협력 진행 전 NDA 체결 요청드립니다.\n\n• 첨부: NDA 계약서\n• 회신기한: 2주 내\n\n문의사항 있으시면 연락 부탁드립니다.\n\n법무팀"),
            ("계약서 검토 요청 내부 메일 써줘. {type} 계약, {deadline}까지.",
             "제목: [검토요청] {type} 계약서 ({deadline}까지)\n\n법무팀 검토 요청드립니다.\n\n• 계약유형: {type}\n• 상대방: [회사명]\n• 기한: {deadline}\n\n첨부파일 확인 부탁드립니다."),
        ],
        "고객지원": [
            ("VIP 고객 불만 사과 메일 써줘. '{complaint}' 건, 보상 포함.",
             "제목: [사과] 불편사항 안내\n\n{name} 고객님께,\n\n'{complaint}' 관련 불편드려 죄송합니다.\n\n■ 개선조치\n• [조치내용]\n\n■ 보상\n• 프리미엄 1개월 연장\n• 포인트 10,000P\n\n다시 한번 사과드립니다."),
            ("서비스 점검 사전 안내 메일 써줘. {date} {time}.",
             "제목: [안내] 서비스 점검 예정 ({date})\n\n안녕하세요,\n\n{date} {time} 점검 예정입니다.\n\n• 소요: 약 2시간\n• 영향: 일시 접속 불가\n\n양해 부탁드립니다.\n\n고객지원팀"),
        ],
    },
    "en": {
        "Finance": [
            ("Payment from {company} is {days} days overdue. Write a polite but firm collection email.",
             "Subject: Payment Reminder - Invoice #{invoice}\n\nDear {company} Team,\n\nThis is a reminder that payment for Invoice #{invoice} is {days} days overdue.\n\n• Amount: ${amount}\n• Due Date: {date}\n\nPlease process payment within 5 business days to avoid service interruption.\n\nQuestions? Contact billing@cokee.com.\n\nBest regards,\nCokee Finance"),
            ("Write a Q{quarter} budget alert email. We've used {percent}% of quarterly budget.",
             "Subject: Q{quarter} Budget Alert - {percent}% Utilized\n\nDear Department Heads,\n\nQ{quarter} budget is {percent}% consumed with {weeks} weeks remaining.\n\n**Action Required:**\n• Freeze non-essential spending\n• Pre-approve all new expenses\n• Delay discretionary purchases\n\nContact Finance for exceptions.\n\nRegards,\nFinance Team"),
        ],
        "HR": [
            ("Write onboarding schedule for {count} new hires. Include orientation, lunch, equipment setup.",
             "New Hire Onboarding Schedule\n\n**Date:** [Date] | **Attendees:** {count} new hires\n\n**Morning**\n• 9:00 Welcome & Workspace Setup\n• 9:30-11:30 Orientation (Company overview, policies)\n• 11:30 ID Badge & System Access\n\n**Lunch**\n• 12:00-1:30 Team Welcome Lunch\n\n**Afternoon**\n• 1:30-3:00 Equipment Setup\n• 3:00-4:00 Mentor Introduction\n• 4:00-5:00 Q&A"),
            ("Write PTO reminder. Employees with {days}+ days must use by year-end.",
             "Subject: PTO Reminder - Use It or Lose It\n\nTeam,\n\nEmployees with {days}+ PTO days: please schedule time off before year-end.\n\nUnused days will not carry over.\n\nQuestions? Contact HR.\n\nHR Team"),
        ],
        "IT": [
            ("Write password reset notice. Deadline {deadline}, accounts lock if not changed.",
             "Subject: ACTION REQUIRED: Password Reset by {deadline}\n\nAll Employees,\n\nYou must reset your password by {deadline}.\n\n**Requirements:**\n• 8+ characters\n• Upper/lowercase, number, symbol\n\n⚠️ Accounts will be locked after deadline.\n\nReset here: [link]\n\nIT Security"),
            ("Write security alert about phishing emails with subject '{subject}'.",
             "Subject: 🚨 SECURITY ALERT: Phishing Attack\n\nTeam,\n\nPhishing emails with subject '{subject}' detected.\n\n**Do NOT:**\n• Click links\n• Enter credentials\n\n**If clicked:** Call IT Security immediately.\n\nDelete suspicious emails.\n\nIT Security"),
        ],
        "Sales": [
            ("Write follow-up email to {company}. Proposal sent 2 weeks ago, pricing expires end of month.",
             "Subject: Following Up - Proposal for {company}\n\nHi [Name],\n\nFollowing up on the proposal sent 2 weeks ago.\n\n**Note:** Current pricing valid through month-end.\n\nHappy to schedule a call to discuss.\n\nBest,\nCokee Sales"),
            ("Write thank you email after first meeting with {company}.",
             "Subject: Great Meeting Today - {company}\n\nHi [Name],\n\nThank you for your time today.\n\nI'll send the proposal by [date]. Let me know if you need anything else.\n\nBest regards,\nCokee Sales"),
        ],
        "Marketing": [
            ("Write {month} ad performance report. CTR up {ctr}%, CVR up {cvr}%, spend up {budget}%.",
             "# {month} Advertising Performance\n\n**Key Metrics (MoM)**\n| Metric | Change |\n|--------|--------|\n| CTR | +{ctr}% |\n| CVR | +{cvr}% |\n| Spend | +{budget}% |\n\n**Analysis:** Strong growth but efficiency needs improvement.\n\n**Recommendations:**\n• Focus budget on top performers\n• Refine targeting"),
        ],
    },
    "jp": {
        "総務": [
            ("オフィス移転のお知らせを書いて。{date}から{address}へ。前日は在宅。",
             "件名: オフィス移転のお知らせ ({date}～)\n\n社員各位\n\n新オフィスへ移転いたします。\n\n■新住所: {address}\n■移転日: {date}\n■前日: 在宅勤務\n\n私物の梱包をお願いいたします。\n\n総務部"),
            ("会議室予約ルール変更のお知らせ。最大{hours}時間、当日キャンセルはペナルティ。",
             "件名: 会議室予約ルール変更\n\n■変更点\n・最大予約: {hours}時間\n・当日キャンセル: ペナルティ\n・ノーショー3回: 予約制限\n\nご協力お願いいたします。\n\n総務部"),
        ],
        "人事": [
            ("新入社員{count}名のオンボーディング日程を作成して。午前OT、昼食歓迎会、午後機器セットアップとメンター配属。",
             "新入社員オンボーディング日程\n\n■対象: 新入社員{count}名\n\n【午前】\n・9:00 出社案内\n・9:30-11:30 OT（会社紹介、規定説明）\n・11:30 社員証発行\n\n【昼食】\n・12:00-13:30 歓迎会\n\n【午後】\n・13:30-15:00 PC設定\n・15:00-16:00 メンター面談\n\n人事部"),
            ("有給消化促進のお知らせ。残日数{days}日以上の社員向け。",
             "件名: 有給休暇消化のお願い\n\n残有給{days}日以上の皆様へ\n\n年末までに消化をお願いいたします。未消化分は消滅いたします。\n\n計画的な取得をお願いいたします。\n\n人事部"),
        ],
        "IT": [
            ("パスワード変更のお知らせ。{deadline}まで必須、未変更はアカウントロック。",
             "件名: 【重要】パスワード変更のお願い ({deadline}まで)\n\n全社員へ\n\nセキュリティポリシーによりパスワード変更が必要です。\n\n・期限: {deadline} 18:00\n・ルール: 8文字以上（英大小、数字、記号）\n\n⚠️ 期限後は自動ロック\n\nIT部"),
            ("システム障害のお詫び文を書いて。'{issue}'現象、復旧中。",
             "【障害のお知らせ】\n\n'{issue}'の障害が発生しております。\n\n・発生: [時刻]\n・影響: 一部接続不可\n・状況: 復旧作業中\n\n復旧次第ご案内いたします。\n\nご不便おかけし申し訳ございません。"),
        ],
        "営業": [
            ("{company}へのご提案フォローアップメール。2週間経過、今月中の判断をお願いする内容。",
             "件名: ご提案の件（{company}様）\n\n{company} ご担当者様\n\nいつもお世話になっております。\n\n2週間前にお送りしたご提案書の件、ご検討状況をお伺いできればと存じます。\n\n今月中にご判断いただければ、現条件でのご提供が可能です。\n\nご不明点がございましたらご連絡ください。\n\nよろしくお願いいたします。"),
        ],
        "経理": [
            ("{month}月経費精算締め切りのお知らせ。{deadline}まで、未提出は翌月給与反映不可。",
             "件名: 【重要】{month}月経費精算締め切り ({deadline})\n\n社員各位\n\n{month}月経費精算の締め切りをご案内いたします。\n\n・期限: {deadline} 18:00\n・方法: 経費精算システム\n\n⚠️ 期限後提出は翌月給与反映不可\n\n経理部"),
        ],
    },
}

# 변수 값 풀
VARS = {
    "company": ["ABC Corp", "XYZ Inc", "GlobalTech", "MegaSoft", "DataFlow", "CloudPro", "TechVision", "NextGen", "AlphaBiz", "BetaCorp"],
    "days": ["5", "7", "10", "14", "21", "30"],
    "percent": ["75", "80", "85", "90", "95"],
    "quarter": ["1", "2", "3", "4"],
    "month": ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12"],
    "deadline": ["이번 주 금요일", "다음 주 월요일", "이달 말", "15일", "20일", "25일"],
    "count": ["2", "3", "4", "5"],
    "name": ["김철수", "이영희", "박민수", "정수진", "John", "Sarah", "田中", "佐藤"],
    "date": ["1월 15일", "2월 1일", "3월 10일", "Jan 15", "Feb 1", "1月15日", "2月1日"],
    "place": ["회사 근처 식당", "회의실 A", "본사 1층", "Conference Room B"],
    "hours": ["2", "3", "4"],
    "time": ["02:00", "03:00", "22:00", "23:00"],
    "duration": ["2", "3", "4"],
    "subject": ["긴급: 비밀번호 변경", "계정 정지 안내", "Urgent: Password Reset"],
    "comp1": ["A사", "CompA"],
    "comp2": ["B사", "CompB"],
    "ctr": ["10", "15", "20", "25"],
    "cvr": ["5", "8", "10", "12"],
    "budget": ["15", "20", "25", "30"],
    "product": ["Kelron Pro", "Kelron Enterprise", "새로운 AI 솔루션"],
    "event": ["Tech Summit 2026", "AI Expo", "비즈니스 컨퍼런스"],
    "location": ["코엑스", "BEXCO", "San Francisco"],
    "address": ["강남구 테헤란로 123", "서초구 서초대로 456"],
    "bug": ["로그인 오류", "페이지 로딩 실패", "데이터 동기화 문제"],
    "feature": ["AI 검색", "실시간 알림", "대시보드 개선"],
    "issue": ["로그인 불가", "접속 지연", "데이터 오류"],
    "type": ["서비스 이용", "업무 위탁", "라이선스"],
    "complaint": ["응대 지연", "서비스 오류", "품질 불만"],
    "weeks": ["4", "6", "8"],
    "amount": ["10000", "25000", "50000"],
    "invoice": ["INV-2026-001", "INV-2026-002", "INV-2026-003"],
}


def fill_template(template, used_vars=None):
    """템플릿 변수 채우기"""
    if used_vars is None:
        used_vars = {}
    
    result = template
    for var, values in VARS.items():
        placeholder = "{" + var + "}"
        if placeholder in result:
            if var in used_vars:
                value = used_vars[var]
            else:
                value = random.choice(values)
                used_vars[var] = value
            result = result.replace(placeholder, value)
    return result, used_vars


def generate_dataset(target=2000, output_path="/Users/ohe/Projects/Kelron/data/kelron_train_final.jsonl"):
    """데이터셋 생성"""
    data = []
    
    # 기존 데이터 로드
    if os.path.exists(output_path):
        with open(output_path, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    data.append(json.loads(line))
                except:
                    pass
        print(f"기존 데이터: {len(data)}개")
    
    # 언어별 비율
    lang_ratios = {"ko": 0.5, "en": 0.25, "jp": 0.25}
    
    generated = 0
    while generated < target:
        for lang, scenarios in SCENARIOS.items():
            if lang not in lang_ratios:
                continue
            
            lang_target = int(target * lang_ratios[lang])
            lang_generated = 0
            
            for dept, templates in scenarios.items():
                for q_template, a_template in templates:
                    # 여러 변형 생성
                    for _ in range(max(1, lang_target // (len(scenarios) * len(templates) * 3))):
                        used_vars = {}
                        q, used_vars = fill_template(q_template, used_vars)
                        a, _ = fill_template(a_template, used_vars)
                        
                        entry = {
                            "category": f"business_{lang}_{dept}",
                            "messages": [
                                {"role": "system", "content": SYSTEM_PROMPTS.get(lang, SYSTEM_PROMPTS["ko"])},
                                {"role": "user", "content": q},
                                {"role": "assistant", "content": a}
                            ]
                        }
                        
                        # 중복 체크
                        is_dup = any(
                            d["messages"][1]["content"] == q and d["messages"][2]["content"] == a
                            for d in data
                        )
                        
                        if not is_dup:
                            data.append(entry)
                            generated += 1
                            lang_generated += 1
                        
                        if generated >= target:
                            break
                    if generated >= target:
                        break
                if generated >= target:
                    break
            if generated >= target:
                break
    
    # 저장
    random.shuffle(data)
    with open(output_path, 'w', encoding='utf-8') as f:
        for item in data:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
    
    print(f"✅ 총 {len(data)}개 저장 완료: {output_path}")
    return data


if __name__ == "__main__":
    generate_dataset(2000)
