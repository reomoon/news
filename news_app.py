import html

import streamlit as st

from app import ensure_dirs, refresh_rankings


st.set_page_config(
    page_title="Nate 랭킹 뷰어",
    page_icon="📰",
    layout="centered",
)


@st.cache_data(ttl=300, show_spinner=False)
def load_rankings() -> dict:
    ensure_dirs()
    return refresh_rankings()


def apply_style() -> None:
    st.markdown(
        """
        <style>
        .stApp { background: #ffffff; }
        .block-container { max-width: 760px; padding-top: 1rem; padding-bottom: 2rem; }
        .top-title { font-size: 1.5rem; font-weight: 800; margin-bottom: 0.15rem; }
        .top-sub { color: #667085; font-size: 0.85rem; margin-bottom: 0.75rem; }
        .rank-row {
            display: grid;
            grid-template-columns: 84px 1fr;
            gap: 10px;
            align-items: center;
            padding: 10px 0;
            border-bottom: 1px solid #eef1f4;
        }
        .rank-num {
            color: #0b57d0;
            font-weight: 800;
            font-size: 1.05rem;
            text-align: right;
            padding-right: 4px;
        }
        .rank-title {
            margin: 0;
            line-height: 1.35;
            font-size: 0.95rem;
            font-weight: 600;
        }
        .rank-title a {
            text-decoration: none;
            color: #111827;
        }
        .rank-title a:hover { text-decoration: underline; }
        .rank-meta {
            margin-top: 4px;
            color: #6b7280;
            font-size: 0.78rem;
        }
        .rank-thumb {
            width: 84px;
            height: 58px;
            object-fit: cover;
            border-radius: 6px;
            background: #f3f4f6;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_category(items: list[dict]) -> None:
    for item in items:
        rank = item.get("rank", "-")
        title = item.get("title", "제목 없음")
        media = item.get("media", "출처 미상")
        url = item.get("url", "")
        thumb = item.get("thumbnail", "")
        fallback_thumb = item.get("fallbackThumbnail", "")
        safe_title = html.escape(title)
        safe_media = html.escape(media)
        safe_thumb = html.escape(thumb, quote=True)
        safe_fallback_thumb = html.escape(fallback_thumb, quote=True)
        if safe_thumb:
            # 원문 썸네일 로딩 실패(핫링크 차단 등) 시 네이트 썸네일로 즉시 대체
            thumb_html = (
                f'<img class="rank-thumb" src="{safe_thumb}" alt="" '
                f'referrerpolicy="no-referrer" '
                f'onerror="this.onerror=null;this.src=\'{safe_fallback_thumb}\';" />'
            )
        else:
            thumb_html = "<div></div>"
        link = url if url else "#"

        st.markdown(
            f"""
            <div class="rank-row">
              <div>{thumb_html}</div>
              <div>
                <p class="rank-title"><span class="rank-num">{rank}</span> <a href="{link}" target="_blank">{safe_title}</a></p>
                <div class="rank-meta">{safe_media}</div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def main() -> None:
    apply_style()
    st.markdown('<div class="top-title">많이 본 랭킹</div>', unsafe_allow_html=True)
    st.markdown('<div class="top-sub">연예/경제 1~20위 | 5분 캐시 갱신</div>', unsafe_allow_html=True)

    try:
        data = load_rankings()
    except Exception as exc:
        st.error(f"데이터를 가져오는 중 오류가 발생했습니다: {exc}")
        if st.button("다시 시도"):
            st.cache_data.clear()
            st.rerun()
        return

    st.caption(f"업데이트: {data.get('updatedAt', '-')}")

    refresh_col, _ = st.columns([1, 3])
    with refresh_col:
        if st.button("지금 갱신"):
            st.cache_data.clear()
            st.rerun()

    tab_ent, tab_eco = st.tabs(["엔터", "경제"])

    with tab_ent:
        ent_items = data.get("categories", {}).get("ent", {}).get("items", [])
        render_category(ent_items)

    with tab_eco:
        eco_items = data.get("categories", {}).get("eco", {}).get("items", [])
        render_category(eco_items)


if __name__ == "__main__":
    main()
