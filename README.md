# 카카오 DART 재무분석 — YoonA_0827

대상 저장소: https://github.com/bonai887-lab/YoonA_0827

## 현재 상태
이 패키지는 실행 가능한 수집·계산 코드와 배포 구성을 제공합니다. **실제 카카오 수치는 아직 수집되지 않았고 GitHub에 업로드·배포되지 않았습니다.** 인증키를 넣고 워크플로를 실행해야 수치와 분석이 생성됩니다. 초기 화면에는 가짜 예시 수치가 없습니다.

## 설치 순서
1. ZIP을 풀고 파일과 폴더를 저장소의 최상위에 올립니다. ZIP 파일 자체를 업로드하면 실행되지 않습니다.
2. `.github/workflows/dart.yml`도 반드시 포함합니다. 파일 이름 앞의 점 때문에 숨김 파일처럼 보일 수 있습니다.
3. 저장소 Settings → Secrets and variables → Actions → New repository secret에서 이름 `DART_API_KEY`, 값은 OpenDART 인증키로 등록합니다. 채팅, README, 코드에 인증키를 적지 마세요.
4. Settings → Pages → Build and deployment → Source를 **GitHub Actions**로 설정합니다.
5. Settings → Actions → General → Workflow permissions에서 쓰기 권한을 허용합니다. 조직 정책이나 브랜치 보호가 push를 금지하면 관리자 승인이 필요합니다.
6. Actions → Collect Kakao DART and deploy → Run workflow를 실행합니다. 기본 연도는 실행 시점의 전년도까지 5개년입니다. 2026년에 실행하면 2021~2025년입니다. 원하면 start_year와 end_year에 연도를 입력합니다.
7. 성공한 deploy 작업에 표시되는 주소로 접속합니다. 이후 매월 7일 09:00 KST 자동 갱신됩니다.

## 웹에서 숨김 폴더를 올리기 어려우면
GitHub Add file → Create new file에서 `.github/workflows/dart.yml` 경로를 입력하고 같은 파일 내용을 붙여 넣습니다. 나머지 폴더는 압축을 푼 상태로 업로드합니다.

## 파일 구성
- `scripts/collect.py`: 종목코드 035720으로 고유번호를 조회한 뒤 연결 사업보고서 전체 계정 수집
- `data/raw/<연도>/financials.json`: API 응답 원본
- `data/raw/<연도>/mapping_audit.json`: 계정 매핑·통화·당기/전기 값 감사 기록
- `reports/<연도>_<접수번호>.zip`: 해당 재무제표 응답의 접수번호에 대응하는 DART 공시 원문 ZIP (PDF가 아닌 원본 XML 패키지)
- `data/financials.json`, `data/financials.csv`: 주요 수치·비율
- `web/template.html`: 대시보드 템플릿
- `index.html`: 데이터가 내장된 대시보드. 직접 열어도 동작하며 차트는 CDN 접속 필요
- `.github/workflows/dart.yml`: 수집, 저장소 커밋, Pages 배포

## 계산과 검증
첨부 '재무제표_재무비율_실무가이드.docx'의 정의를 반영했습니다. 통화 KRW, CFS, 사업보고서 11011만 사용합니다. 계정ID 우선, 명칭 정확 일치 차선이며 애매하거나 충돌한 계정은 null입니다. 매출증가율은 동일 공시에 기재된 전기 매출, 평균 자산·지배주주지분도 동일 공시의 비교 금액을 사용합니다. 연도 사이 비교 수치가 재작성되었을 수 있으므로 원본을 검토해야 합니다.

기본 지표: 매출, 영업이익, 순이익, 지배주주순이익, 자산·부채·자본, 유동자산·유동부채, 현금, CFO. CAPEX는 유형·무형자산 취득 현금 두 항목이 모두 확인될 때만 계산하며 FCF = CFO − CAPEX입니다. 해당 정의에는 인수대금이나 리스 원금상환은 포함하지 않습니다. 취득 항목이 누락되면 0으로 간주하지 않습니다.

비율: 성장률, 영업·순이익률, ROA, 지배주주 ROE, 유동비율, 부채비율, 자기자본비율, 자산회전율, CFO/순이익. 분모가 0 또는 음수이면 표시하지 않습니다. 손실인 경우 성장·회복은 금액과 원문을 함께 검토합니다.

매출총이익률, EBITDA, 차입금·순차입금, 이자보상배율, ROIC, CCC, PER·PBR·EV/EBITDA는 자동으로 추정하지 않습니다. 주석에서 구성 항목과 중복 포함 여부를 확인하거나 시점이 일치하는 주가·주식수·자본비용 자료가 추가로 필요합니다. 금융 계열사를 포함하는 연결 범위 때문에 비금융기업 일반 지표를 기계적으로 판단해서는 안 됩니다.

공시 API가 반환한 접수번호에 연결된 원문을 보관합니다. 공시 목록 전체 이력이나 모든 정정공시 버전을 별도로 수집하는 도구는 아닙니다. API 무자료(013)는 누락 연도로 기록하고 다른 오류는 배포를 중단합니다. 데이터는 재수집 시 최신 스냅샷으로 교체되며 Git 이력에 이전 결과가 남습니다.

## 테스트 / 제약
`python -m unittest discover -s tests -v`
합성 자료 단위 테스트와 Python·JavaScript 구문 검사를 수행했습니다. 실제 인증키를 이용한 DART 수집, GitHub Actions 및 브라우저 렌더링은 실행하지 않았습니다. 원문 파일이 GitHub 파일 크기 제한을 넘으면 별도 보관이나 Git LFS가 필요합니다. DART 접근 IP 제한이 있으면 GitHub 호스팅 실행기의 접속이 거절될 수 있습니다.

## 공식 참고
- 전체 재무제표: https://opendart.fss.or.kr/guide/detail.do?apiGrpCd=DS003&apiId=2019020
- 고유번호: https://opendart.fss.or.kr/guide/detail.do?apiGrpCd=DS001&apiId=2019018
- 공시 원문: https://opendart.fss.or.kr/guide/detail.do?apiGrpCd=DS001&apiId=2019003
