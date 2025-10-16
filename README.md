# 관세법 판례 기반 챗봇 (Customs Law Case-Based Chatbot)

**대한민국 관세법 판례 전문 AI 챗봇**

## 1인1봇 프로젝트

**AI 시대, 누구나 자신만의 AI 법률 비서를 만들 수 있습니다**

- 복잡한 판례를 즉시 검색하고 답변 받는 나만의 AI 비서
- 코딩 지식 없이도 사용 가능한 웹 인터페이스
- 관세법 업무에 특화된 전문 AI 챗봇

---

## 이 챗봇의 3가지 특징

### 1. 무료: 구글 제미나이 무료 모델 사용

- **비용**: 완전 무료 (Google Gemini 2.5 Flash 무료 API 사용)
- **설치**: 개인 노트북이나 Streamlit 무료 클라우드에서 실행 가능

### 2. 멀티 에이전트: 여러 AI의 협업으로 성능 극대화

- **원리**: 6개 AI 에이전트가 각자 다른 판례 데이터 분석 → Head AI가 종합하여 최종 답변
- **장점**: 한 번에 여러 판례를 동시 검색, 답변 정확도 향상, 응답 시간 6배 단축
- **예시**: "관세법 제241조 위반 사례는?" 질문 시
  - Agent 1-2: KCS 판례 (423건) 분석
  - Agent 3-6: MOLEG 판례 (486건) 4개 청크로 분할 분석
  - Head AI: 모든 에이전트 답변을 종합하여 최종 답변 제공

### 3. TF-IDF 기반 RAG (Character n-gram + AI): 일반 노트북에서도 빠르게 구동

- **원리**: Character n-gram TF-IDF로 관련 판례 검색 (0.05초) → AI가 검색된 판례만 분석하여 답변 생성
- **장점**: 고성능 서버 불필요, 일반 노트북 및 Streamlit cloud 무료 계정에서도 빠르게 답변
- **기술적 우수성**:
  - **Character n-gram 벡터화**: 2~4글자 조합으로 검색 ("관세법" ↔ "관세법령" 자동 매칭)
  - **성능**: 자체 샘플 데이터 테스트 결과 Word-based 대비 Precision 2.2배, Recall 3.1배 향상
  - **GZIP 캐싱**: 벡터화 시간 80초 → 0.5초로 단축 (160배)
  - **통합 벡터화**: KCS + MOLEG 909건을 하나의 벡터 공간에서 처리

---

## 데이터

### 2개 판례 데이터베이스 (총 909건)

- **KCS 판례**: 관세청 제공 관세분야 판례 (423건)
- **MOLEG 판례**: 국가법령정보센터 관세판례 (486건)

### 데이터 구조

#### KCS 판례 형식
```json
{
  "사건번호": "2019구단12345",
  "선고일자": "2019.03.15",
  "판결주문": "원고의 청구를 기각한다.",
  "청구취지": "처분청이 2018.10.01. 원고에 대하여...",
  "판결이유": "관세법 제241조에 따르면..."
}
```

#### MOLEG 판례 형식
```json
{
  "제목": "[대법원 2025. 2. 13. 선고 2023도1907 판결]",
  "판결요지": "관세법 제241조 위반 사건에서...",
  "내용": "상고를 기각한다. 상고비용은 피고인이 부담한다..."
}
```

---

## 사용법

### 질의 응답 기능 (💬 챗봇 모드)

**"판례를 찾지 않아도 질문하면 AI가 관련 판례를 분석하여 답변합니다"**

#### 사용 순서

1. 💬 챗봇 모드 탭 선택
2. 채팅창에 질문 입력 (예: "실질 납세의무자 판단과 관련된 판례를 찾아서 쟁점을 정리해줘.")
3. 6개 AI 에이전트가 관련 판례 분석 (실시간 진행 상황 표시)
4. 필요시 "각 에이전트 답변 보기" 확장하여 상세 분석 확인
5. 최종 통합 답변 확인

#### 주요 기능

- **실시간 응답 스트리밍**: 에이전트 완료 즉시 화면에 표시 (체감 대기 시간 감소)
- **대화 맥락 유지**: 이전 대화를 기억하여 연속 질문 가능
  - 예: "관세법 241조가 뭐야?" → "처벌은?" (문맥 이해)
- **맥락 설정**: 사이드바에서 이전 대화 맥락 활용 여부 및 최근 대화 유지 수 (2-10개) 설정


### 판례 검색 기능 (🔍 판례 검색 탭)

**"사건번호, 날짜, 키워드로 판례를 직접 검색합니다"**

#### 사용 순서

1. 🔍 판례 검색 탭 선택
2. 검색어 입력 (예: "2023구합208027", "관세법 제241조", "허위신고")
3. 검색어가 노란색으로 강조 표시된 판례 목록 확인
4. 판례 제목 클릭하여 전체 내용 확인

#### 검색 기능

- **사건번호 검색**: 2023구합208027, 대전지법2023구합208027
- **날짜 검색**: 2024-12-19, 2024.12.19, 20241219
- **법원명 검색**: 대법원, 서울고법, 대전지법
- **키워드 검색**: 관세법 제241조, 허위신고, 과소신고

---

## 한계

### 알아두어야 할 제약사항

#### AI 답변의 한계

- AI는 완벽하지 않고, 실수를 합니다.
- AI가 모든 판례를 읽고 답변하는 것이 아닙니다. 사용자 질문과 유사한 판례를 찾아서 분석하는데, 가끔 관련 판례를 잘 찾지 못하는 경우도 있습니다.
- AI는 판례를 참고하여 답변하지만, **법적 효력은 없습니다**
- 중요한 결정은 반드시 판례 원문 확인과 전문가 검토 필요

#### 데이터 최신성

- **판례 업데이트**: 수동으로 크롤링 필요 (`data/crawler_kcs.py`, `data/crawler_moleg.py` 실행)
- **최신 판례 즉시 반영 불가**: 크롤링 후 재실행 필요

#### 검색 정확도

- **Character n-gram 사용**: "관세법" ↔ "관세법령" 자동 매칭, 오타에도 강건
- **법령 용어 사용 권장**: 일상 언어보다 판례에 나오는 법률 용어 사용 시 검색 정확도 향상

#### Gemini API 호출 한계 (무료 사용자)

- **분당 요청 수 (RPM)**: 10회
- **분당 토큰 수 (TPM)**: 250,000 토큰
- **일일 요청 수 (RPD)**: 250회
- **Google 검색 연동**: 500 RPD까지 무료

---

## 기술 아키텍처

### 전체 동작 원리

```
[사용자 질문]
    ↓
[Character n-gram TF-IDF 검색] → 관련 판례 찾기 (0.05초)
    ↓
[6개 에이전트 병렬 실행] → 각자 다른 데이터 청크 분석 (5-10초)
    ├─ Agent 1: KCS[0:212] (KCS 전반부)
    ├─ Agent 2: KCS[212:423] (KCS 후반부)
    ├─ Agent 3: MOLEG[423:545] (MOLEG 1/4)
    ├─ Agent 4: MOLEG[545:667] (MOLEG 2/4)
    ├─ Agent 5: MOLEG[667:788] (MOLEG 3/4)
    └─ Agent 6: MOLEG[788:909] (MOLEG 4/4)
    ↓
[Head Agent] → 모든 에이전트 답변 통합 (2-3초)
    ↓
[사용자에게 최종 답변 표시]
```

### 핵심 기술

#### 1. Character n-gram TF-IDF 벡터화

- **분석 단위**: 글자 단위 (analyzer='char')
- **n-gram 범위**: 2~4글자 조합 (ngram_range=(2,4))
- **예시**: "관세법" → "관세", "세법", "관", "세", "법", "관세법"
- **장점**:
  - 형태소 변형 자동 매칭 ("관세법" ↔ "관세법령")
  - 오타에 강건 ("관세볍" → 부분 매칭)
  - Word-based 대비 Precision 2.2배, Recall 3.1배 향상

#### 2. GZIP 압축 Pickle 캐싱

- **최초 실행**: 벡터화 수행 (약 80초) → `vectorization_cache.pkl.gz` 저장
- **이후 실행**: 캐시 로드 (약 0.5초) → 160배 단축
- **자동 재생성**: 데이터 파일 변경 시 자동 감지 및 재벡터화

#### 3. 멀티 에이전트 병렬 처리

- **병렬 실행**: ThreadPoolExecutor로 6개 에이전트 동시 실행
- **시간 단축**: 순차 실행 30초 → 병렬 실행 5초 (6배)
- **실시간 UI**: 에이전트 완료 즉시 화면에 표시 (yield 활용)

#### 4. 대화 맥락 관리

- **이전 대화 참조**: 최근 2-10개 대화 자동 포함
- **자연스러운 대화**: "처벌은?" 만으로도 이전 문맥 이해
- **설정 가능**: 사이드바에서 맥락 활용 여부 및 유지 수 선택

---

## 프로젝트 구조

```
legal_precedents/
├── data/                          # 데이터 관리 도구
│   ├── __init__.py
│   ├── crawler_kcs.py            # KCS 판례 크롤러
│   ├── crawler_moleg.py          # MOLEG 판례 크롤러
│   ├── clean_kcs.py              # KCS 데이터 정제
│   ├── clean_moleg.py            # MOLEG 데이터 정제
│   └── update_kcs_data.py        # KCS 데이터 업데이트 유틸리티
│
├── utils/                         # 챗봇 핵심 로직
│   ├── __init__.py               # 모듈 내보내기
│   ├── config.py                 # Gemini API 설정
│   ├── conversation.py           # 대화 기록 관리
│   ├── data_loader.py            # 데이터 로드 및 캐싱
│   ├── text_processor.py         # 텍스트 전처리
│   ├── vectorizer.py             # TF-IDF 벡터화 및 검색
│   ├── agent.py                  # AI 에이전트 실행
│   ├── precedent_search.py       # 판례 검색 메인 로직
│   ├── scoring.py                # 유사도 점수 계산
│   └── pattern_detectors.py      # 패턴 탐지 (사건번호, 날짜 등)
│
├── data_kcs.json                 # KCS 판례 데이터 (423건)
├── data_moleg.json               # MOLEG 판례 데이터 (486건)
├── vectorization_cache.pkl.gz    # 벡터화 캐시 (GZIP 압축)
├── main.py                       # Streamlit 애플리케이션
├── requirements.txt
├── CLAUDE.md
└── README.md
```

### 핵심 파일 설명

- **`main.py`**: 프로그램 시작 파일 (Streamlit 앱)
- **`utils/`**: AI 에이전트, 검색, 전처리 등 핵심 로직
- **`data/`**: 판례 크롤링 및 데이터 정제 스크립트
- **`data_kcs.json`, `data_moleg.json`**: 판례 원본 데이터
- **`vectorization_cache.pkl.gz`**: 벡터화 캐시 (재시작 시 즉시 사용)

---

## 설치 및 실행 방법

### 필수 프로그램

- **Python 3.7 이상**
- **인터넷 연결** (Google Gemini API 사용)

### 필수 API 키 발급

1. **Google API Key** (필수): [Google AI Studio](https://aistudio.google.com/apikey)에서 무료 발급

### 설치 및 실행 (Windows 기준)

#### 1단계: 프로그램 다운로드

```bash
git clone https://github.com/YSCHOI-github/legal_precedents.git
cd legal_precedents
```

#### 2단계: 필요한 라이브러리 설치

```bash
pip install -r requirements.txt
```

#### 3단계: API 키 설정

`.env` 파일 생성 후 아래 내용 입력:

```
GOOGLE_API_KEY=여기에_발급받은_구글_API_키_입력
```

#### 4단계: 프로그램 실행

```bash
streamlit run main.py
```

#### 5단계: 웹 브라우저에서 사용

- 자동으로 브라우저 열림
- 또는 주소창에 `http://localhost:8501` 입력

---

## 판례 데이터 업데이트 방법

**중요: 모든 명령은 프로젝트 루트 디렉토리에서 실행해야 합니다**

### 1. KCS 데이터 업데이트

```bash
# 프로젝트 루트로 이동
cd legal_precedents

# Step 1: 새로운 판례 크롤링
python data/crawler_kcs.py
# 출력: data_kcs_temp.json (프로젝트 루트에 생성)

# Step 2: 기존 데이터와 병합 및 중복 제거
python data/update_kcs_data.py
# 출력: data_kcs.json 업데이트 (프로젝트 루트)
# 자동 백업: data_kcs_backup_YYYYMMDD_HHMMSS.json
```

**동작 원리**
- `crawler_kcs.py`: 관세청 홈페이지에서 최신 판례 크롤링 (Selenium 사용)
- `update_kcs_data.py`: 사건번호 기준으로 중복 제거 후 병합
- 기존 데이터는 타임스탬프 백업 후 업데이트

### 2. MOLEG 데이터 업데이트 (현재 법령정보센터 이용 불가)

**현재 상태: 수동 업데이트만 가능**

```bash
# 프로젝트 루트로 이동
cd legal_precedents

# Step 1: 새로운 판례 크롤링
python data/crawler_moleg.py
# 출력: law_portal_data_YYYYMMDD_HHMMSS.json (프로젝트 루트에 생성)

# Step 2: 기존 데이터와 병합 및 중복 제거 (법령정보센터 정상가동 시 구축 예정)
python data/update_moleg_data.py
# 출력: data_moleg.json 업데이트 (프로젝트 루트)
# 자동 백업: data_moleg_backup_YYYYMMDD_HHMMSS.json
```

---

## 주요 의존성

```python
streamlit              # 웹 애플리케이션 프레임워크
google-genai           # Gemini AI 모델 연동
scikit-learn          # TF-IDF 벡터화
python-dotenv         # 환경변수 관리
selenium              # 웹 크롤링
webdriver-manager     # 크롬 드라이버 관리
pandas                # 데이터 처리
```

---

## 라이선스

**MIT License**

- 누구나 자유롭게 사용, 수정, 배포 가능
- 상업적 이용 가능
- 단, 원저작자 표시 필수

```
MIT License

Copyright (c) 2025 YSCHOI-github

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

## 개발자 정보

- **개발자**: Yeonsoo CHOI
- **GitHub**: [YSCHOI-github/legal_precedents](https://github.com/YSCHOI-github/legal_precedents)
