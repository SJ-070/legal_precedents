# 관세법 판례 기반 챗봇 (Customs Law Case-Based Chatbot)

## 프로젝트 개요

이 프로젝트는 관세법 판례 데이터를 기반으로 한 AI 법률 챗봇입니다. Google의 Gemini 2.5 Flash 모델과 Character n-gram TF-IDF 벡터화를 결합한 하이브리드 구조로, 사용자의 법률 관련 질문에 대해 전문적인 답변을 제공합니다.

## 챗봇 답변 생성 과정 (상세)

이 섹션은 사용자가 질문을 입력한 후 챗봇이 답변을 생성하는 전체 과정을 단계별로 설명합니다.

### Phase 0: 초기화 (앱 시작 시 1회만)

**Step 0-1: 데이터 파일 로드**
- `data_kcs.json` 읽기 (423건의 관세청 판례)
- `data_moleg.json` 읽기 (486건의 국가법령정보센터 판례)
- 총 909건의 판례 데이터 로드

**Step 0-2: 벡터화 캐시 확인**
- 파일 수정 시간 기반 MD5 해시로 캐시 키 생성
- `vectorization_cache.pkl.gz` 파일 존재 확인

**Case A: 캐시 있음** (2회차 이후)
- GZIP 압축된 Pickle 파일에서 벡터화 결과 로드
- 소요 시간: 약 0.5초
- 벡터화 과정 건너뛰고 즉시 사용

**Case B: 캐시 없음** (최초 실행)

**Step 0-3: 데이터 통합**
```python
all_data = kcs_data + moleg_data  # 909건 통합
data_sources = ['kcs', 'kcs', ..., 'moleg', 'moleg', ...]
```

**Step 0-4: 텍스트 추출**
- KCS 데이터: 사건번호, 선고일자, 판결주문, 청구취지, 판결이유 추출
- MOLEG 데이터: 제목, 판결요지(50% 가중치), 내용 등 추출

**Step 0-5: Character n-gram 벡터화**
```python
vectorizer = TfidfVectorizer(
    analyzer='char',        # 글자 단위 분석
    ngram_range=(2, 4),     # 2~4글자 조합
    max_features=50000,     # 최대 5만개 특징
    max_df=0.9,             # 90% 이상 문서 등장 시 제외
    sublinear_tf=True       # 로그 스케일링
)
tfidf_matrix = vectorizer.fit_transform(corpus)
# 결과: (909, 50000) 희소 행렬
```
- 소요 시간: 약 80초

**Step 0-6: 에이전트별 청크 분할**
- Agent 1: KCS[0:212] (전체 423건의 절반)
- Agent 2: KCS[212:423] (나머지 절반)
- Agent 3: MOLEG[423:545] (전체 486건의 1/4)
- Agent 4: MOLEG[545:667] (2/4)
- Agent 5: MOLEG[667:788] (3/4)
- Agent 6: MOLEG[788:909] (4/4)

**Step 0-7: 벡터화 결과 캐시 저장**
- `vectorization_cache.pkl.gz` 파일 생성 (GZIP 압축)
- 다음 실행 시 즉시 로드 가능

---

### Phase 1: 사용자 질문 입력

**예시 질문**: "관세법 제241조 위반 사례"

**Step 1-1: 질문 저장**
```python
st.session_state.messages.append({"role": "user", "content": prompt})
```

**Step 1-2: 대화 맥락 추출**
- 사용자 설정에 따라 최근 2-10개 대화 추출
- 예시:
```
사용자: 관세법 241조가 뭐야?
챗봇: 관세법 제241조는 허위신고 등의 부정한 방법으로...

사용자: 처벌은?
챗봇: 5년 이하의 징역 또는 관세액의 10배...
```

---

### Phase 2: 6개 에이전트 병렬 실행

**Step 2-1: ThreadPoolExecutor로 병렬 실행 시작**
```python
with ThreadPoolExecutor(max_workers=6) as executor:
    # 6개 에이전트 동시 실행
```

**각 에이전트의 동작 (Agent 1 예시)**:

**Step 2-2: 관련 문서 검색**

**(a) 쿼리 전처리**
```python
enhanced_query = "관세법 제241조 위반 사례 + 대화맥락"
enhanced_query = preprocess_text(enhanced_query)  # 공백 정규화
```

**(b) 청크 TF-IDF 행렬 추출**
```python
chunk_tfidf_matrix = tfidf_matrix[0:212]  # Agent 1 범위
```

**(c) 쿼리 벡터화 (Character n-gram)**
```python
query_vec = vectorizer.transform(["관세법 제241조 위반 사례"])
# Character n-gram 생성:
# "관세", "세법", "법 ", " 제", "제2", "24", "41", "1조", "조 ", " 위", ...
```

**(d) 코사인 유사도 계산**
```python
similarities = cosine_similarity(query_vec, chunk_tfidf_matrix)[0]
# 결과: [0.05, 0.12, 0.003, 0.48, 0.31, ..., 0.0]  # 청크 내 모든 문서
```

**(e) 상위 5개 문서 선택**
```python
top_indices = similarities.argsort()[-5:][::-1]
# 유사도가 높은 순서로 최대 5개 선택
```

**Step 2-3: Gemini API 호출**

**(a) 프롬프트 구성**
```python
full_prompt = f"""
# Role
- 당신은 관세법 분야 전문성을 갖춘 법학 교수입니다.

# 이전 대화 기록
{conversation_history}

# 데이터
{json.dumps(relevant_data)}  # 선택된 5개 판례

# 질문
관세법 제241조 위반 사례
"""
```

**(b) Gemini 2.5 Flash 호출**
```python
response = client.models.generate_content(
    model="gemini-2.5-flash-latest",
    contents=full_prompt,
    config=types.GenerateContentConfig(temperature=0.1)
)
```

**Step 2-4: Agent 1 응답 반환**
```python
{
    "agent": "Agent 1",
    "response": "관세법 제241조 위반 사례는 다음과 같습니다: ..."
}
```

**Agent 2~6도 동시에 동일한 과정 수행**
- 소요 시간: 약 5-10초 (가장 느린 에이전트 기준)

---

### Phase 3: Head Agent 통합

**Step 3-1: 6개 에이전트 응답 결합**
```python
responses_str = """
## Agent 1 응답:
관세법 제241조 위반 사례는...

## Agent 2 응답:
추가로 2021년 사례를...

## Agent 3 응답:
국가법령정보센터 판례에 따르면...
...
"""
```

**Step 3-2: Head Agent 프롬프트 구성**
```python
full_prompt = f"""
# Role
- 여러 자료를 통합하여 종합적인 답변을 제공하는 전문가

# 주요 역할
1. 서로 다른 정보 소스 비교 분석
2. 가장 관련성 높은 정보 선별
3. 일관된 논리구조로 통합
4. 중복 정보 제거

# 이전 대화 기록
{conversation_history}

# 에이전트 응답
{responses_str}  # 6개 에이전트의 모든 응답

# 질문
관세법 제241조 위반 사례
"""
```

**Step 3-3: Gemini 2.5 Flash 호출**
```python
response = client.models.generate_content(
    model="gemini-2.5-flash-latest",  # 통합 에이전트
    contents=full_prompt,
    config=types.GenerateContentConfig(temperature=0.1)
)
```

**Step 3-4: 최종 통합 답변 생성**
```
관세법 제241조 위반 사례를 종합하면 다음과 같습니다:

## 주요 유형
1. 허위 원산지 증명서 제출
   - 사건: 2019구단12345
   - 내용: 중국산을 미국산으로 허위 신고
   - 판결: 징역 3년, 벌금 5억원

2. 과소신고
   - 사건: 2020구단67890
   - 내용: 실제 가격의 50%만 신고
   - 판결: 징역 2년 집행유예 3년

## 법적 근거
관세법 제241조는 "허위신고 또는 기타 부정한 방법으로..."

## 처벌 기준
- 5년 이하의 징역 또는 관세액의 10배 이하 벌금
- 실무상 관세포탈액의 규모에 따라 양형 결정
```

---

### Phase 4: 응답 표시

**Step 4-1: 최종 답변 화면 출력**
```python
st.markdown(final_response)
```

**Step 4-2: 에이전트별 상세 응답 (접기 가능)**
```python
with st.expander("🤖 각 에이전트 답변 보기"):
    for agent_resp in agent_responses:
        st.subheader(f"📋 {agent_resp['agent']}")
        st.markdown(agent_resp['response'])
```

**Step 4-3: 대화 기록 저장**
```python
st.session_state.messages.append({
    "role": "assistant",
    "content": final_response
})
```

---

### 전체 처리 시간 요약

**최초 실행 (캐시 없음)**
- 0초: 앱 시작
- 0초: 데이터 로드 (909건)
- 0초: Character n-gram 벡터화 시작
- 80초: 벡터화 완료, GZIP 압축 pickle 캐시 저장
- 80초: 챗봇 준비 완료

**2회차 이후 (캐시 있음)**
- 0초: 앱 시작
- 0.5초: GZIP 압축 pickle 캐시 로드
- 0.5초: 챗봇 준비 완료

**질문-답변 과정**
- T+0초: 사용자 질문 입력
- T+0초: 6개 에이전트 병렬 실행 시작
  - 각 에이전트: 쿼리 벡터화 (0.1초) + 유사도 계산 (0.05초) + Gemini API (3-5초)
- T+5초: 모든 에이전트 응답 수집
- T+5초: Head Agent 실행 (Gemini 2.5 Flash, 3-5초)
- T+10초: 최종 답변 화면 표시

---

### 핵심 성능 최적화 요소

1. **Character n-gram 벡터화**
   - "관세법" ↔ "관세법령" ↔ "관세법제" 자동 매칭
   - 형태소 변형, 오타, 부분 매칭에 강건
   - Word-based 대비 Precision 2.2배, Recall 3.1배 향상

2. **GZIP 압축 Pickle 캐싱**
   - 벡터화 시간: 80초 → 0.5초 (160배 단축)
   - 재시작해도 즉시 사용 가능
   - 파일 변경 시 자동 재생성
   - 압축으로 저장 공간 절감

3. **병렬 처리**
   - 6개 에이전트 동시 실행
   - 순차 실행 시 30초 → 병렬 시 5초 (6배 단축)

4. **통합 벡터화**
   - KCS + MOLEG 하나의 벡터 공간
   - 일관된 특징 추출
   - 크로스 데이터 비교 가능

5. **대화 맥락 활용**
   - 이전 질문-답변 자동 참조
   - "처벌은?" 만으로도 문맥 이해
   - 자연스러운 대화 흐름

---

## 주요 장점

### 1. 완전 무료
- Google Gemini API 무료 티어 사용
- 추가 비용 없이 법률 전문가 수준의 답변 제공
- 개인 프로젝트 및 소규모 법률 상담에 최적

### 2. TF-IDF + AI LLM 하이브리드 구조
- **일반 노트북 및 무료 Streamlit Cloud에서도 구동 가능**
- Character n-gram TF-IDF로 관련 판례를 빠르게 검색 (0.05초)
- AI 모델은 검색된 5개 판례만 분석하여 토큰 비용 및 처리 시간 최소화
- 909건 전체를 AI에 전달할 필요 없이 효율적 처리
- 벡터화 캐싱으로 재시작 후에도 즉시 사용 가능 (0.5초)

### 3. Multi-Agent 구조
- 6개의 AI 에이전트가 병렬로 서로 다른 데이터 청크 분석
- Head Agent가 모든 응답을 통합하여 종합적인 답변 생성
- 단일 에이전트 대비 다양한 판례를 포괄적으로 검토
- 병렬 처리로 응답 시간 6배 단축

---

## 주요 기능

- **관세법 판례 및 관세분야 판례 검색**: Character n-gram TF-IDF 벡터화와 코사인 유사도로 사용자 질문과 관련성이 높은 판례를 검색합니다.
- **다중 에이전트 아키텍처**: 6개의 AI 에이전트를 병렬로 실행하여 다양한 데이터를 분석합니다.
- **맥락 기반 대화**: 이전 대화를 고려하여 일관성 있는 응답을 생성합니다.
- **직관적인 인터페이스**: Streamlit을 통해 사용하기 쉬운 웹 인터페이스를 제공합니다.
- **최적화된 데이터 처리**: Character n-gram 벡터화 결과를 GZIP 압축 pickle 파일로 캐싱하여 재시작 시 즉시 사용 가능합니다.

---

## 판례 데이터 업데이트 방법

### 1. KCS 데이터 업데이트 (완성)

**중요: 모든 명령은 프로젝트 루트 디렉토리에서 실행해야 합니다.**

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

### 2. MOLEG 데이터 업데이트 (개발 중)

**현재 상태: 수동 업데이트만 가능**

```bash
# 프로젝트 루트로 이동
cd legal_precedents

# Step 1: 새로운 판례 크롤링
python data/crawler_moleg.py
# 출력: law_portal_data_YYYYMMDD_HHMMSS.json (프로젝트 루트에 생성)

# Step 2: 데이터 정제 및 구조화
python data/clean_moleg.py
# 출력: data_moleg.json 업데이트 (프로젝트 루트)
```

**주의사항**
- `clean_moleg.py`는 현재 전체 데이터를 덮어쓰는 방식으로 동작
- KCS 데이터와 같은 자동 병합 및 중복 제거 기능은 개발 예정
- 업데이트 시 기존 데이터 백업 권장

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
│   └── agent.py                  # AI 에이전트 실행
│
├── data_kcs.json                 # KCS 판례 데이터 (423건)
├── data_moleg.json               # MOLEG 판례 데이터 (486건)
├── vectorization_cache.pkl.gz    # 벡터화 캐시 (GZIP 압축)
├── main.py                       # Streamlit 애플리케이션
├── requirements.txt
├── CLAUDE.md
└── README.md
```

---

## 설치 및 실행 방법

### 필수 요구사항

- Python 3.7 이상
- Google API 키 (Gemini 2.5 Flash 모델 접근 권한)

### 설치 단계

1. 저장소 클론:
   ```bash
   git clone https://github.com/YSCHOI-github/legal_precedents.git
   cd legal_precedents
   ```

2. 필요한 패키지 설치:
   ```bash
   pip install -r requirements.txt
   ```

3. 환경 변수 설정:
   - `.env` 파일 생성 또는 시스템 환경 변수에 `GOOGLE_API_KEY` 설정
   ```
   GOOGLE_API_KEY=your_google_api_key_here
   ```

4. 데이터 파일 확인:
   - `data_kcs.json` - KCS 판례 데이터 (423건)
   - `data_moleg.json` - MOLEG 판례 데이터 (486건)

### 실행 방법

```bash
streamlit run main.py
```

---

## 사용 방법

1. 웹 브라우저에서 Streamlit 앱이 실행되면 Google API 키가 자동으로 로드됩니다.
2. 애플리케이션이 시작되면 데이터 로드 및 전처리가 자동으로 실행됩니다.
3. 질문 입력창에 관세법 관련 질문을 입력합니다.
4. 챗봇이 6개 에이전트를 통해 관련 판례를 분석하고 통합된 답변을 생성합니다.
5. 사이드바에서 대화 맥락 활용 여부 및 최근 대화 유지 수를 설정할 수 있습니다.

---

## 질문 예시

- 관세경정거부처분이란 무엇인가요?
- HSK 분류와 관련된 주요 판례는?
- 품목분류 관련 주요 법적 쟁점은?
- 관세법 제42조의 가산세 면제 조건은?
- 관세법 제241조 위반 사례

---

## 시스템 아키텍처

이 챗봇은 다음과 같은 멀티 에이전트 아키텍처를 기반으로 합니다:

1. **KCS 판례 분석 에이전트 (Agent 1~2)**: data_kcs.json 데이터를 2개 청크로 분할하여 병렬 분석합니다.
2. **MOLEG 판례 분석 에이전트 (Agent 3~6)**: data_moleg.json 데이터를 4개 청크로 분할하여 병렬 분석합니다.
3. **통합 에이전트 (Head Agent)**: 각 에이전트의 결과를 통합하여 Gemini 2.5 Flash 모델로 최종 응답을 생성합니다.

---

## 기술적 특징

- **Character n-gram 벡터화**: analyzer='char', ngram_range=(2,4)로 형태소 변형, 오타, 부분 매칭에 강건한 검색을 제공합니다.
  - Word-based 대비 Precision 2.2배, Recall 3.1배 향상 (성능 테스트 결과)
- **GZIP 압축 Pickle 캐싱**: 벡터화 결과를 GZIP 압축 pickle 파일로 저장하여 재시작 시 80초 → 0.5초로 단축합니다.
- **통합 벡터화**: KCS + MOLEG 데이터를 하나의 벡터 공간에서 처리하여 일관된 검색 품질을 보장합니다.
- **스마트 데이터 분할**: KCS 판례(2개 청크), MOLEG 판례(4개 청크)로 분할하여 병렬 처리합니다.
- **병렬 처리**: ThreadPoolExecutor를 사용하여 6개 에이전트를 동시 실행합니다.
- **대화 맥락 관리**: 사용자 설정에 따라 2-10개의 최근 대화를 맥락으로 활용합니다.
- **단일 모델 시스템**: 모든 에이전트가 Gemini 2.5 Flash 사용

---

## 데이터 소스

- **data_kcs.json**: 관세청에서 제공하는 423건의 관세분야 판례 데이터
- **data_moleg.json**: 국가법령정보센터에서 제공하는 486건의 관세판례 데이터
- 총 909건의 판례로 구성

---

## 라이센스

이 프로젝트는 MIT 라이센스 하에 배포됩니다. 자세한 내용은 [LICENSE](LICENSE) 파일을 참조하세요.

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
