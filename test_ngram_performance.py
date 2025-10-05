import json
import time
import sys
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from datetime import datetime
import psutil
import os

def load_test_data():
    """테스트용 데이터 로드"""
    print("데이터 로딩 중...")

    with open('data_kcs.json', 'r', encoding='utf-8') as f:
        kcs_data = json.load(f)

    with open('data_moleg.json', 'r', encoding='utf-8') as f:
        moleg_data = json.load(f)

    # 통합 데이터 생성 및 텍스트 추출
    texts = []
    all_data = []

    # KCS 데이터 처리 (한글 키)
    for item in kcs_data:
        text_parts = [
            item.get('사건명', ''),
            item.get('사건번호', ''),
            item.get('판결주문', ''),
            item.get('청구취지', ''),
            item.get('판결이유', '')
        ]
        texts.append(' '.join(filter(None, text_parts)))
        all_data.append(item)

    # MOLEG 데이터 처리 (영문 키)
    for item in moleg_data:
        text_parts = [
            item.get('title', ''),
            item.get('case_number', ''),
            item.get('summary', ''),
            item.get('content', ''),
            item.get('keywords', '')
        ]
        texts.append(' '.join(filter(None, text_parts)))
        all_data.append(item)

    print(f"총 {len(texts)}건의 데이터 로드 완료 (KCS: {len(kcs_data)}건, MOLEG: {len(moleg_data)}건)")
    return texts, all_data

def get_memory_usage():
    """현재 프로세스의 메모리 사용량 (MB)"""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024

def test_vectorization_performance(texts, ngram_range):
    """벡터화 성능 테스트"""
    print(f"\n{'='*60}")
    print(f"테스트 중: ngram_range={ngram_range}")
    print(f"{'='*60}")

    # 메모리 측정 시작
    mem_before = get_memory_usage()

    # 벡터화 시간 측정
    start_time = time.time()

    vectorizer = TfidfVectorizer(
        analyzer='char',
        ngram_range=ngram_range,
        max_features=None
    )

    tfidf_matrix = vectorizer.fit_transform(texts)

    vectorization_time = time.time() - start_time

    # 메모리 측정 종료
    mem_after = get_memory_usage()
    mem_used = mem_after - mem_before

    # 특징 개수
    n_features = len(vectorizer.get_feature_names_out())

    # 행렬 크기 (MB)
    matrix_size = tfidf_matrix.data.nbytes / 1024 / 1024

    results = {
        'ngram_range': ngram_range,
        'vectorization_time': round(vectorization_time, 3),
        'n_features': n_features,
        'matrix_size_mb': round(matrix_size, 2),
        'memory_used_mb': round(mem_used, 2),
        'matrix_shape': tfidf_matrix.shape,
        'matrix_density': round(tfidf_matrix.nnz / (tfidf_matrix.shape[0] * tfidf_matrix.shape[1]) * 100, 4)
    }

    print(f"벡터화 시간: {results['vectorization_time']}초")
    print(f"특징 개수: {results['n_features']:,}개")
    print(f"행렬 크기: {results['matrix_size_mb']:.2f} MB")
    print(f"메모리 사용: {results['memory_used_mb']:.2f} MB")
    print(f"행렬 밀도: {results['matrix_density']:.4f}%")

    return vectorizer, tfidf_matrix, results

def test_search_performance(vectorizer, tfidf_matrix, texts, test_queries):
    """검색 성능 테스트"""
    search_times = []

    for query in test_queries:
        start_time = time.time()

        # 쿼리 벡터화
        query_vector = vectorizer.transform([query])

        # 유사도 계산
        similarities = cosine_similarity(query_vector, tfidf_matrix)[0]

        # 상위 결과 추출
        top_indices = similarities.argsort()[-15:][::-1]

        search_time = time.time() - start_time
        search_times.append(search_time)

    avg_search_time = np.mean(search_times)

    print(f"평균 검색 시간: {avg_search_time*1000:.2f}ms")

    return avg_search_time

def test_search_quality(vectorizer, tfidf_matrix, all_data, test_queries, top_k=5):
    """검색 품질 테스트"""
    quality_results = []

    for query in test_queries:
        # 쿼리 벡터화
        query_vector = vectorizer.transform([query])

        # 유사도 계산
        similarities = cosine_similarity(query_vector, tfidf_matrix)[0]

        # 상위 결과 추출
        top_indices = similarities.argsort()[-top_k:][::-1]

        results = []
        for idx in top_indices:
            # 데이터 타입에 따라 제목 추출 (KCS는 한글 키, MOLEG는 영문 키)
            title = all_data[idx].get('사건명', all_data[idx].get('title', 'N/A'))[:100]
            results.append({
                'index': int(idx),
                'title': title,
                'similarity': round(float(similarities[idx]), 4)
            })

        quality_results.append({
            'query': query,
            'results': results
        })

    return quality_results

def compare_results(all_results):
    """결과 비교 및 출력"""
    print("\n" + "="*80)
    print("성능 비교 결과")
    print("="*80)

    # 표 헤더
    print(f"\n{'N-gram Range':<15} {'벡터화(초)':<12} {'특징 개수':<15} {'행렬 크기(MB)':<15} {'검색(ms)':<12}")
    print("-" * 80)

    # 각 결과 출력
    baseline = None
    for result in all_results:
        ngram = str(result['ngram_range'])
        vec_time = result['vectorization_time']
        n_features = result['n_features']
        matrix_size = result['matrix_size_mb']
        search_time = result['avg_search_time'] * 1000

        # 기준값 설정 (첫 번째를 기준으로)
        if baseline is None:
            baseline = result
            ratio_text = ""
        else:
            vec_ratio = vec_time / baseline['vectorization_time']
            feat_ratio = n_features / baseline['n_features']
            size_ratio = matrix_size / baseline['matrix_size_mb']
            search_ratio = search_time / (baseline['avg_search_time'] * 1000)
            ratio_text = f" (x{vec_ratio:.1f}, x{feat_ratio:.1f}, x{size_ratio:.1f}, x{search_ratio:.1f})"

        print(f"{ngram:<15} {vec_time:<12.3f} {n_features:<15,} {matrix_size:<15.2f} {search_time:<12.2f}{ratio_text}")

    print("\n* 괄호 안은 첫 번째 대비 배율 (벡터화 시간, 특징 개수, 행렬 크기, 검색 시간)")

def save_results(all_results, output_file='ngram_test_results.json'):
    """결과를 JSON 파일로 저장"""
    output = {
        'test_date': datetime.now().isoformat(),
        'results': all_results
    }

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n결과가 {output_file}에 저장되었습니다.")

def print_quality_comparison(all_quality_results):
    """검색 품질 비교 출력"""
    print("\n" + "="*80)
    print("검색 품질 비교 (첫 번째 쿼리 예시)")
    print("="*80)

    # 첫 번째 쿼리만 비교
    query_idx = 0

    for ngram_result in all_quality_results:
        ngram_range = ngram_result['ngram_range']
        query = ngram_result['quality_results'][query_idx]['query']
        results = ngram_result['quality_results'][query_idx]['results']

        print(f"\n[{ngram_range}] 쿼리: '{query}'")
        print("-" * 80)
        for i, result in enumerate(results, 1):
            print(f"{i}. (유사도: {result['similarity']:.4f}) {result['title']}")

def main():
    """메인 테스트 함수"""
    print("N-gram Range 성능 테스트 시작")
    print("="*80)

    # 데이터 로드
    texts, all_data = load_test_data()

    # 테스트 쿼리 정의
    test_queries = [
        "관세법 위반 부당환급",
        "수입신고 원산지 허위신고",
        "밀수입 물품 몰수",
        "통관 절차 위반 과태료",
        "보세구역 반출 승인",
        "관세 감면 요건",
        "FTA 원산지증명서 제출",
        "수출입 신고 정정",
        "관세환급 신청 기한",
        "부가가치세 면제 대상"
    ]

    print(f"\n테스트 쿼리 개수: {len(test_queries)}개")

    # 테스트할 n-gram 범위
    ngram_ranges = [(2,3), (2,4), (2,5), (2,6)]

    all_results = []
    all_quality_results = []

    for ngram_range in ngram_ranges:
        # 벡터화 성능 테스트
        vectorizer, tfidf_matrix, perf_results = test_vectorization_performance(texts, ngram_range)

        # 검색 성능 테스트
        avg_search_time = test_search_performance(vectorizer, tfidf_matrix, texts, test_queries)
        perf_results['avg_search_time'] = avg_search_time

        # 검색 품질 테스트
        quality_results = test_search_quality(vectorizer, tfidf_matrix, all_data, test_queries)

        all_results.append(perf_results)
        all_quality_results.append({
            'ngram_range': ngram_range,
            'quality_results': quality_results
        })

    # 결과 비교 및 출력
    compare_results(all_results)

    # 검색 품질 비교
    print_quality_comparison(all_quality_results)

    # 결과 저장
    save_results(all_results)

    print("\n" + "="*80)
    print("테스트 완료!")
    print("="*80)

if __name__ == "__main__":
    main()
