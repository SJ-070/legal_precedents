"""
Data Loading and Caching
데이터 로드 및 캐시 관리 모듈
"""

import streamlit as st
import json
import os
import zipfile
import tempfile
import pickle
import gzip
import logging


def check_data_files():
    """필요한 데이터 파일 존재 여부 확인"""
    court_file = "data_kcs.json"
    tax_file = "data_moleg.json"

    files_exist = True
    if not os.path.exists(court_file):
        st.sidebar.error(f"파일을 찾을 수 없습니다: {court_file}")
        files_exist = False
    if not os.path.exists(tax_file):
        st.sidebar.error(f"파일을 찾을 수 없습니다: {tax_file}")
        files_exist = False

    return files_exist


def extract_zip_file(zip_path):
    """ZIP 파일을 임시 디렉토리에 압축 해제하고 JSON 파일 내용 반환"""
    try:
        # 임시 디렉토리 생성
        with tempfile.TemporaryDirectory() as temp_dir:
            # ZIP 파일 압축 해제
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)

            # JSON 파일 찾기 (첫 번째 JSON 파일 사용)
            json_files = [f for f in os.listdir(temp_dir) if f.endswith('.json')]
            if not json_files:
                raise FileNotFoundError("ZIP 파일 내에 JSON 파일이 없습니다.")

            # JSON 파일 로드
            json_path = os.path.join(temp_dir, json_files[0])
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            return data
    except Exception as e:
        st.sidebar.error(f"ZIP 파일 처리 오류: {str(e)}")
        logging.error(f"ZIP 파일 처리 오류: {str(e)}")
        return []


def save_vectorization_cache(preprocessed_data):
    """벡터화 결과를 gzip 압축하여 저장 (로컬 환경 전용)"""
    cache_file = "vectorization_cache.pkl.gz"
    try:
        with gzip.open(cache_file, 'wb', compresslevel=9) as f:
            pickle.dump(preprocessed_data, f)

        # 압축 효과 로깅
        file_size = os.path.getsize(cache_file) / 1024 / 1024  # MB
        logging.info(f"벡터화 캐시 저장 완료: {cache_file} ({file_size:.2f} MB)")
        return True
    except (PermissionError, OSError) as e:
        # Streamlit Cloud는 읽기 전용 - 에러 무시
        logging.warning(f"캐시 저장 불가 (읽기 전용 환경): {str(e)}")
        return False


def load_vectorization_cache():
    """저장된 gzip 압축 벡터화 결과를 로드"""
    cache_file = "vectorization_cache.pkl.gz"

    # 하위 호환성: 기존 pkl 파일도 지원
    legacy_cache_file = "vectorization_cache.pkl"

    try:
        # gzip 압축 파일 우선 확인
        if os.path.exists(cache_file):
            with gzip.open(cache_file, 'rb') as f:
                preprocessed_data = pickle.load(f)
            file_size = os.path.getsize(cache_file) / 1024 / 1024  # MB
            logging.info(f"벡터화 캐시 로드 완료: {cache_file} ({file_size:.2f} MB)")
            return preprocessed_data

        # 기존 pkl 파일 확인 (하위 호환성)
        elif os.path.exists(legacy_cache_file):
            with open(legacy_cache_file, 'rb') as f:
                preprocessed_data = pickle.load(f)
            logging.info(f"레거시 캐시 로드 완료: {legacy_cache_file} (다음 저장 시 gzip으로 전환)")
            return preprocessed_data

        return None
    except Exception as e:
        logging.error(f"벡터화 캐시 로드 실패: {str(e)}")
        return None


@st.cache_data
def load_data():
    """판례 데이터 로드"""
    try:
        # 판례 데이터 로드1
        with open("data_kcs.json", "r", encoding="utf-8") as f:
            court_cases = json.load(f)
        st.sidebar.success(f"KCS 판례 데이터 로드 완료: {len(court_cases)}건")

        # 판례 데이터 로드2
        with open("data_moleg.json", "r", encoding="utf-8") as f:
            tax_cases = json.load(f)
        st.sidebar.success(f"MOLEG 판례 데이터 로드 완료: {len(tax_cases)}건")

        # 캐시된 벡터화 결과 확인
        preprocessed_data = load_vectorization_cache()

        if preprocessed_data is not None:
            st.sidebar.info("저장된 벡터화 인덱스를 로드했습니다.")
        else:
            # 캐시가 없으면 데이터 전처리 및 벡터화 수행
            st.sidebar.info("벡터화 인덱스를 생성 중입니다...")
            from .vectorizer import preprocess_data
            preprocessed_data = preprocess_data(court_cases, tax_cases)
            # 벡터화 결과 저장
            save_vectorization_cache(preprocessed_data)
            st.sidebar.success("벡터화 인덱스 생성 및 저장 완료!")

        return court_cases, tax_cases, preprocessed_data

    except FileNotFoundError as e:
        st.sidebar.error(f"파일을 찾을 수 없습니다: {e}")
        st.error("필수 데이터 파일을 찾을 수 없습니다. 애플리케이션 디렉토리에 필요한 파일이 있는지 확인하세요.")
        return [], [], {}
    except json.JSONDecodeError as e:
        st.sidebar.error(f"JSON 파일 파싱 오류: {e}")
        st.error("JSON 파일 형식이 올바르지 않습니다. 파일 형식을 확인하세요.")
        return [], [], {}
