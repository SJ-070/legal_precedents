"""
성능 테스트: TF-IDF 벡터화 방식 비교
- Word-based TF-IDF
- Character n-gram TF-IDF
- Hybrid (Word + Char)

실행: python test_vectorization_performance.py
"""

import json
import time
import tracemalloc
from typing import List, Dict, Tuple
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import re

# 법률 불용어 (utils.py에서 가져옴)
LEGAL_STOPWORDS = [
    # 기본 불용어
    '제', '것', '등', '때', '경우', '바', '수', '점', '면', '이', '그', '저', '은', '는', '을', '를', '에', '의', '으로',
    '따라', '또는', '및', '있다', '한다', '되어', '인한', '대한', '관한', '위한', '통한', '같은', '다른',

    # 법령 구조 불용어
    '조항', '규정', '법률', '법령', '조문', '항목', '세부', '내용', '사항', '요건', '기준', '방법', '절차',

    # 일반적인 동사/형용사
    '해당', '관련', '포함', '제외', '적용', '시행', '준용', '의하다', '하다', '되다', '있다', '없다', '같다'
]

class VectorizationMethod:
    """벡터화 방식 기본 클래스"""

    def __init__(self, name: str):
        self.name = name
        self.vectorizers = []
        self.tfidf_matrices = []
        self.vectorization_time = 0
        self.memory_usage = 0
        self.vocab_size = 0

    def fit_transform(self, corpus: List[str]) -> None:
        """코퍼스를 벡터화"""
        raise NotImplementedError

    def search(self, query: str, top_k: int = 10) -> Tuple[np.ndarray, np.ndarray]:
        """쿼리 검색 (인덱스, 유사도 반환)"""
        raise NotImplementedError


class WordBasedVectorizer(VectorizationMethod):
    """Word-based TF-IDF (현재 방식)"""

    def __init__(self):
        super().__init__("Word-based")

    def fit_transform(self, corpus: List[str]) -> None:
        tracemalloc.start()
        start_time = time.time()

        self.vectorizer = TfidfVectorizer(
            analyzer='word',
            ngram_range=(1, 2),
            stop_words=LEGAL_STOPWORDS,
            min_df=1,
            max_df=0.8,
            sublinear_tf=True,
            use_idf=True,
            smooth_idf=True,
            norm='l2'
        )

        self.tfidf_matrix = self.vectorizer.fit_transform(corpus)

        self.vectorization_time = time.time() - start_time
        current, peak = tracemalloc.get_traced_memory()
        self.memory_usage = peak / 1024 / 1024  # MB
        tracemalloc.stop()

        self.vocab_size = len(self.vectorizer.vocabulary_)

    def search(self, query: str, top_k: int = 10) -> Tuple[np.ndarray, np.ndarray]:
        start_time = time.time()

        query_vec = self.vectorizer.transform([query])
        similarities = cosine_similarity(query_vec, self.tfidf_matrix)[0]
        top_indices = similarities.argsort()[-top_k:][::-1]
        top_scores = similarities[top_indices]

        search_time = time.time() - start_time
        return top_indices, top_scores, search_time


class CharNgramVectorizer(VectorizationMethod):
    """Character n-gram TF-IDF"""

    def __init__(self):
        super().__init__("Char n-gram")

    def fit_transform(self, corpus: List[str]) -> None:
        tracemalloc.start()
        start_time = time.time()

        self.vectorizer = TfidfVectorizer(
            analyzer='char',
            ngram_range=(2, 4),
            max_df=0.9,
            min_df=1,
            max_features=50000,  # 차원 폭발 방지
            sublinear_tf=True,
            use_idf=True,
            smooth_idf=True,
            norm='l2'
        )

        self.tfidf_matrix = self.vectorizer.fit_transform(corpus)

        self.vectorization_time = time.time() - start_time
        current, peak = tracemalloc.get_traced_memory()
        self.memory_usage = peak / 1024 / 1024  # MB
        tracemalloc.stop()

        self.vocab_size = len(self.vectorizer.vocabulary_)

    def search(self, query: str, top_k: int = 10) -> Tuple[np.ndarray, np.ndarray]:
        start_time = time.time()

        query_vec = self.vectorizer.transform([query])
        similarities = cosine_similarity(query_vec, self.tfidf_matrix)[0]
        top_indices = similarities.argsort()[-top_k:][::-1]
        top_scores = similarities[top_indices]

        search_time = time.time() - start_time
        return top_indices, top_scores, search_time


class HybridVectorizer(VectorizationMethod):
    """Hybrid (Word 50% + Char 50%)"""

    def __init__(self, word_weight: float = 0.5):
        super().__init__(f"Hybrid (W:{word_weight:.0%}/C:{1-word_weight:.0%})")
        self.word_weight = word_weight
        self.char_weight = 1 - word_weight

    def fit_transform(self, corpus: List[str]) -> None:
        tracemalloc.start()
        start_time = time.time()

        # Word vectorizer
        self.word_vectorizer = TfidfVectorizer(
            analyzer='word',
            ngram_range=(1, 2),
            stop_words=LEGAL_STOPWORDS,
            min_df=1,
            max_df=0.8,
            sublinear_tf=True,
            use_idf=True,
            smooth_idf=True,
            norm='l2'
        )

        # Char vectorizer
        self.char_vectorizer = TfidfVectorizer(
            analyzer='char',
            ngram_range=(2, 4),
            max_df=0.9,
            min_df=1,
            max_features=50000,
            sublinear_tf=True,
            use_idf=True,
            smooth_idf=True,
            norm='l2'
        )

        self.word_matrix = self.word_vectorizer.fit_transform(corpus)
        self.char_matrix = self.char_vectorizer.fit_transform(corpus)

        self.vectorization_time = time.time() - start_time
        current, peak = tracemalloc.get_traced_memory()
        self.memory_usage = peak / 1024 / 1024  # MB
        tracemalloc.stop()

        self.vocab_size = len(self.word_vectorizer.vocabulary_) + len(self.char_vectorizer.vocabulary_)

    def search(self, query: str, top_k: int = 10) -> Tuple[np.ndarray, np.ndarray]:
        start_time = time.time()

        # Word similarity
        query_word_vec = self.word_vectorizer.transform([query])
        word_similarities = cosine_similarity(query_word_vec, self.word_matrix)[0]

        # Char similarity
        query_char_vec = self.char_vectorizer.transform([query])
        char_similarities = cosine_similarity(query_char_vec, self.char_matrix)[0]

        # Hybrid score
        similarities = self.word_weight * word_similarities + self.char_weight * char_similarities

        top_indices = similarities.argsort()[-top_k:][::-1]
        top_scores = similarities[top_indices]

        search_time = time.time() - start_time
        return top_indices, top_scores, search_time


class PerformanceEvaluator:
    """성능 평가 클래스"""

    @staticmethod
    def calculate_precision_at_k(retrieved: List[int], relevant: List[int], k: int) -> float:
        """Precision@K 계산"""
        if k == 0:
            return 0.0
        retrieved_k = retrieved[:k]
        relevant_retrieved = len(set(retrieved_k) & set(relevant))
        return relevant_retrieved / k

    @staticmethod
    def calculate_recall_at_k(retrieved: List[int], relevant: List[int], k: int) -> float:
        """Recall@K 계산"""
        if len(relevant) == 0:
            return 0.0
        retrieved_k = retrieved[:k]
        relevant_retrieved = len(set(retrieved_k) & set(relevant))
        return relevant_retrieved / len(relevant)

    @staticmethod
    def calculate_mrr(retrieved: List[int], relevant: List[int]) -> float:
        """Mean Reciprocal Rank 계산"""
        for i, doc_id in enumerate(retrieved):
            if doc_id in relevant:
                return 1.0 / (i + 1)
        return 0.0

    @staticmethod
    def calculate_ndcg_at_k(retrieved: List[int], relevant: List[int], k: int) -> float:
        """NDCG@K 계산"""
        dcg = 0.0
        for i, doc_id in enumerate(retrieved[:k]):
            if doc_id in relevant:
                dcg += 1.0 / np.log2(i + 2)  # i+2 because i starts from 0

        # Ideal DCG
        idcg = sum([1.0 / np.log2(i + 2) for i in range(min(len(relevant), k))])

        return dcg / idcg if idcg > 0 else 0.0


def preprocess_text(text: str) -> str:
    """텍스트 전처리"""
    if not text or not isinstance(text, str):
        return ""
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    return text


def extract_text_from_item(item: Dict, data_type: str) -> str:
    """데이터 아이템에서 텍스트 추출 (utils.py와 동일)"""
    if data_type == "court_case":
        text_parts = []
        for key in ['사건번호', '선고일자\n(종결일자)', '판결주문', '청구취지', '판결이유']:
            if key in item and item[key]:
                sub_text = f'{key}: {item[key]} \n\n'
                text_parts.append(sub_text)
        return ' '.join(text_parts)
    else:  # moleg
        text_parts = []
        field_weights = {
            '제목': 0.0625,
            '판례번호': 0.0625,
            '내용': 0.0625,
            '선고일자': 0.0625,
            '법원명': 0.0625,
            '사건유형': 0.0625,
            '판결요지': 0.5,
            '참조조문': 0.0625,
            '판결결과': 0.0625
        }

        for field, weight in field_weights.items():
            if field in item and item[field]:
                field_text = f'{field}: {item[field]} \n\n'
                repeat_count = max(1, int(weight * 10))
                for _ in range(repeat_count):
                    text_parts.append(field_text)

        return ' '.join(text_parts)


def load_test_data():
    """테스트 데이터 로드"""
    print("데이터 로딩 중...")

    with open("data_kcs.json", "r", encoding="utf-8") as f:
        court_cases = json.load(f)

    with open("data_moleg.json", "r", encoding="utf-8") as f:
        moleg_cases = json.load(f)

    # 전체 데이터 합치기
    all_data = court_cases + moleg_cases

    # 코퍼스 생성
    corpus = []
    for i, item in enumerate(all_data):
        if i < len(court_cases):
            text = extract_text_from_item(item, "court_case")
        else:
            text = extract_text_from_item(item, "moleg")
        corpus.append(preprocess_text(text))

    print(f"데이터 로드 완료: KCS {len(court_cases)}건 + MOLEG {len(moleg_cases)}건 = 총 {len(all_data)}건")
    return all_data, corpus


def create_test_queries():
    """테스트 쿼리 생성"""
    test_queries = [
        # 정확한 법조문 검색 (5개)
        {"query": "관세법 제241조", "type": "exact_match", "description": "정확한 법조문"},
        {"query": "관세법 제269조 밀수입죄", "type": "exact_match", "description": "법조문+죄명"},
        {"query": "관세 환급", "type": "exact_match", "description": "일반 법률 용어"},
        {"query": "수입신고", "type": "exact_match", "description": "관세 절차 용어"},
        {"query": "관세 납부 의무", "type": "exact_match", "description": "의무 관련"},

        # 형태소 변형 (5개)
        {"query": "관세법령", "type": "morphology", "description": "법+법령 변형"},
        {"query": "수입신고서", "type": "morphology", "description": "신고+서류"},
        {"query": "관세환급금", "type": "morphology", "description": "환급+금"},
        {"query": "밀수출입", "type": "morphology", "description": "밀수+출입"},
        {"query": "세관검사", "type": "morphology", "description": "세관+검사"},

        # 복합 법률 용어 (5개)
        {"query": "관세환급금 청구 절차", "type": "complex_term", "description": "환급 절차"},
        {"query": "밀수입 처벌 기준", "type": "complex_term", "description": "처벌 기준"},
        {"query": "수입신고 의무 위반", "type": "complex_term", "description": "의무 위반"},
        {"query": "과세가격 결정 방법", "type": "complex_term", "description": "과세 방법"},
        {"query": "원산지 증명서 제출", "type": "complex_term", "description": "증명서 제출"},

        # 오타 테스트 (3개)
        {"query": "관세뱁", "type": "typo", "description": "법→뱁 오타"},
        {"query": "수입신고서", "type": "typo", "description": "정상 (비교용)"},
        {"query": "관세완급", "type": "typo", "description": "환→완 오타"},

        # 부분 매칭 (2개)
        {"query": "수입신고", "type": "partial_match", "description": "수입신고의무자 검색"},
        {"query": "관세", "type": "partial_match", "description": "관세법 관련 전체"},
    ]

    return test_queries


def run_tests():
    """전체 테스트 실행"""
    print("="*70)
    print("TF-IDF 벡터화 방식 성능 비교 테스트")
    print("="*70)
    print()

    # 데이터 로드
    all_data, corpus = load_test_data()

    # 테스트 쿼리
    test_queries = create_test_queries()
    print(f"테스트 쿼리: {len(test_queries)}개\n")

    # 3가지 벡터화 방식
    methods = [
        WordBasedVectorizer(),
        CharNgramVectorizer(),
        HybridVectorizer(word_weight=0.5)
    ]

    # 각 방식으로 벡터화
    print("벡터화 수행 중...\n")
    for method in methods:
        print(f"  {method.name} 벡터화 중...", end=" ")
        method.fit_transform(corpus)
        print(f"완료 ({method.vectorization_time:.2f}초)")

    print()

    # 성능 비교 테이블
    print("="*70)
    print("1. 벡터화 성능 비교")
    print("="*70)
    print(f"{'방식':<20} {'벡터화 시간':<15} {'벡터 차원':<15} {'메모리(MB)':<15}")
    print("-"*70)
    for method in methods:
        print(f"{method.name:<20} {method.vectorization_time:>10.2f}초    {method.vocab_size:>10,}개    {method.memory_usage:>10.1f} MB")
    print()

    # 검색 성능 테스트
    print("="*70)
    print("2. 검색 정확도 비교")
    print("="*70)

    evaluator = PerformanceEvaluator()
    results = {method.name: {
        'precision@5': [],
        'recall@10': [],
        'mrr': [],
        'ndcg@10': [],
        'search_times': [],
        'query_results': []
    } for method in methods}

    # 각 쿼리에 대해 테스트
    for i, test_query in enumerate(test_queries):
        query = test_query['query']
        query_type = test_query['type']

        if i % 5 == 0:
            print(f"  진행: {i}/{len(test_queries)} 쿼리...", end="\r")

        # 각 방식으로 검색
        method_results = {}
        for method in methods:
            indices, scores, search_time = method.search(query, top_k=10)
            method_results[method.name] = {
                'indices': indices,
                'scores': scores,
                'search_time': search_time
            }
            results[method.name]['search_times'].append(search_time)

        # Ground truth 생성 (간단한 방법: 모든 방식의 상위 결과 합집합에서 점수 높은 것)
        # 실제로는 수동 라벨링이 필요하지만, 자동 평가를 위해 휴리스틱 사용
        all_top_indices = set()
        for method_name, result in method_results.items():
            # 유사도 > 0.1인 것만 관련 문서로 간주
            relevant_indices = result['indices'][result['scores'] > 0.1]
            all_top_indices.update(relevant_indices.tolist())

        # 각 방식의 정확도 계산
        for method_name, result in method_results.items():
            indices = result['indices'].tolist()
            relevant = list(all_top_indices)

            precision = evaluator.calculate_precision_at_k(indices, relevant, 5)
            recall = evaluator.calculate_recall_at_k(indices, relevant, 10)
            mrr = evaluator.calculate_mrr(indices, relevant)
            ndcg = evaluator.calculate_ndcg_at_k(indices, relevant, 10)

            results[method_name]['precision@5'].append(precision)
            results[method_name]['recall@10'].append(recall)
            results[method_name]['mrr'].append(mrr)
            results[method_name]['ndcg@10'].append(ndcg)

            results[method_name]['query_results'].append({
                'query': query,
                'type': query_type,
                'precision': precision,
                'recall': recall,
                'top_score': result['scores'][0] if len(result['scores']) > 0 else 0
            })

    print(f"  진행: {len(test_queries)}/{len(test_queries)} 쿼리... 완료!")
    print()

    # 평균 지표 출력
    print(f"{'방식':<20} {'Precision@5':<15} {'Recall@10':<15} {'MRR':<15} {'NDCG@10':<15} {'검색속도(ms)':<15}")
    print("-"*100)
    for method_name in results:
        avg_precision = np.mean(results[method_name]['precision@5'])
        avg_recall = np.mean(results[method_name]['recall@10'])
        avg_mrr = np.mean(results[method_name]['mrr'])
        avg_ndcg = np.mean(results[method_name]['ndcg@10'])
        avg_search_time = np.mean(results[method_name]['search_times']) * 1000  # ms

        print(f"{method_name:<20} {avg_precision:>10.3f}      {avg_recall:>10.3f}      {avg_mrr:>10.3f}      {avg_ndcg:>10.3f}      {avg_search_time:>10.2f} ms")

    print()

    # 쿼리 유형별 성능
    print("="*70)
    print("3. 쿼리 유형별 평균 정확도 (Precision@5)")
    print("="*70)

    query_types = set([q['type'] for q in test_queries])

    print(f"{'유형':<20} ", end="")
    for method_name in results:
        print(f"{method_name:<20} ", end="")
    print()
    print("-"*100)

    for qtype in query_types:
        print(f"{qtype:<20} ", end="")
        for method_name in results:
            type_precisions = [r['precision'] for r in results[method_name]['query_results'] if r['type'] == qtype]
            avg = np.mean(type_precisions) if type_precisions else 0
            print(f"{avg:>10.3f}          ", end="")
        print()

    print()

    # 최종 추천
    print("="*70)
    print("4. 최종 추천")
    print("="*70)

    # 종합 점수 계산 (Precision, Recall, MRR, NDCG 평균)
    composite_scores = {}
    for method_name in results:
        score = (
            np.mean(results[method_name]['precision@5']) * 0.3 +
            np.mean(results[method_name]['recall@10']) * 0.3 +
            np.mean(results[method_name]['mrr']) * 0.2 +
            np.mean(results[method_name]['ndcg@10']) * 0.2
        )
        composite_scores[method_name] = score

    # 최고 점수
    best_method = max(composite_scores, key=composite_scores.get)
    best_score = composite_scores[best_method]

    print(f"종합 점수 (가중 평균):")
    for method_name, score in sorted(composite_scores.items(), key=lambda x: x[1], reverse=True):
        star = " ⭐ 추천!" if method_name == best_method else ""
        print(f"  {method_name:<20} {score:.3f}{star}")

    print()
    print(f"최종 추천 방식: {best_method}")
    print()

    # 방식별 특징
    print("각 방식의 특징:")
    print("-" * 70)

    method_idx = list(results.keys()).index(best_method)
    best_method_obj = methods[method_idx]

    print(f"\n🏆 {best_method}")
    print(f"  - 종합 점수: {best_score:.3f}")
    print(f"  - Precision@5: {np.mean(results[best_method]['precision@5']):.3f}")
    print(f"  - Recall@10: {np.mean(results[best_method]['recall@10']):.3f}")
    print(f"  - 벡터화 시간: {best_method_obj.vectorization_time:.2f}초")
    print(f"  - 검색 속도: {np.mean(results[best_method]['search_times'])*1000:.2f}ms")
    print(f"  - 메모리 사용: {best_method_obj.memory_usage:.1f}MB")

    if "Word" in best_method:
        print(f"  - 장점: 빠른 속도, 정확한 법률 용어 매칭, 낮은 메모리 사용")
        print(f"  - 단점: 형태소 변형/오타에 취약")
        print(f"  - 권장: 정확한 법조문 검색 중심 환경")
    elif "Char" in best_method:
        print(f"  - 장점: 형태소 변형 자동 인식, 오타 강건성, 부분 매칭 우수")
        print(f"  - 단점: 높은 메모리/계산 비용, 정확도 다소 낮음")
        print(f"  - 권장: 사용자 입력 품질이 낮은 환경")
    else:  # Hybrid
        print(f"  - 장점: 정확도와 재현율 균형, 다양한 쿼리 대응")
        print(f"  - 단점: 가장 높은 메모리/계산 비용")
        print(f"  - 권장: 정확도가 중요한 프로덕션 환경")

    print()
    print("="*70)
    print("테스트 완료!")
    print("="*70)

    return results, methods


if __name__ == "__main__":
    import sys

    try:
        results, methods = run_tests()
    except FileNotFoundError as e:
        print(f"\n오류: 데이터 파일을 찾을 수 없습니다.")
        print(f"data_kcs.json과 data_moleg.json 파일이 현재 디렉토리에 있는지 확인하세요.")
        sys.exit(1)
    except Exception as e:
        print(f"\n오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
