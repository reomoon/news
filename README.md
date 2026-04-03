# Nate Ranking Viewer

네이트 랭킹뉴스(연예/경제)를 수집해서 모바일 반응형 웹으로 보여주는 간단한 Python 앱입니다.

## 주요 기능

- 연예(`ent`), 경제(`eco`) 랭킹 1~20위 수집
- 썸네일 표시 (목록/원문 메타 이미지 보강)
- 네이트 링크 대신 실제 언론사 원문 링크로 이동
- 모바일 반응형 UI + 탭 전환 + 좌측 햄버거 메뉴
- 1시간마다 자동 갱신 스케줄러

## 실행 방법

```bash
python app.py
```

실행 후 브라우저에서 아래 주소로 접속합니다.

- `http://localhost:8000`

## Streamlit 배포/실행

Streamlit Cloud에서는 `app.py`(내장 HTTP 서버)가 아니라 `streamlit_app.py`를 실행해야 합니다.

```bash
streamlit run streamlit_app.py
```

- Streamlit Cloud 설정
  - Main file path: `streamlit_app.py`
  - Python dependencies: `requirements.txt`

`streamlit_app.py`는 `@st.cache_data(ttl=3600)`을 사용해 1시간 캐시 갱신을 수행합니다.

## API

- `GET /api/rankings`
  - 현재 캐시 데이터(`data/rankings.json`) 반환
- `GET /api/refresh`
  - 즉시 재수집 후 최신 데이터 반환

## 데이터 파일

- `data/rankings.json`
  - 서버 시작 시 1회 생성/갱신
  - 이후 스케줄러가 1시간마다 덮어써서 최신 상태 유지

