from __future__ import annotations

from io import BytesIO

import streamlit as st

from database import SupabaseNotConfigured, app_base_url, create_invite, download_original, get_invite
from image_utils import (
    apply_adjustments,
    bytes_to_image,
    compress_image,
    create_result_card,
    image_to_png_bytes,
    load_image,
)


st.set_page_config(page_title="Color Us", page_icon="🎞️", layout="centered", initial_sidebar_state="collapsed")


CSS = """
<style>
  #MainMenu, footer, header, [data-testid="stSidebar"] { display: none !important; }
  .stApp {
    background:
      radial-gradient(circle at 18% 8%, rgba(255, 218, 189, .72), transparent 34%),
      radial-gradient(circle at 88% 18%, rgba(197, 150, 126, .25), transparent 32%),
      linear-gradient(180deg, #fff8ef 0%, #f4e2d5 100%);
    color: #302721;
  }
  .block-container { max-width: 520px; padding: 1.8rem 1.05rem 3rem; }
  h1, h2, h3, p { letter-spacing: .01em; }
  .hero, .panel, .result-panel {
    border: 1px solid rgba(92, 64, 50, .13);
    background: rgba(255, 252, 247, .76);
    box-shadow: 0 24px 70px rgba(88, 56, 38, .12);
    backdrop-filter: blur(18px);
    border-radius: 30px;
    padding: 28px 23px;
  }
  .hero { min-height: 78vh; display: flex; flex-direction: column; justify-content: center; }
  .eyebrow { color: #9c7463; font-size: .82rem; text-transform: uppercase; letter-spacing: .18em; }
  .title { font-size: 3.6rem; line-height: .9; margin: .6rem 0 .5rem; font-weight: 700; }
  .subtitle { font-size: 1.08rem; color: #5d4a42; margin-bottom: 2.5rem; }
  .poem { font-size: 1.12rem; line-height: 2; color: #69564d; margin: 1.8rem 0 2.3rem; }
  .hint { color: #8a7267; font-size: .92rem; line-height: 1.7; }
  .share-link {
    word-break: break-all; padding: 14px 16px; border-radius: 18px;
    background: #f6e8dd; color: #5c463d; border: 1px dashed rgba(93, 63, 49, .28);
  }
  div[data-testid="stButton"] > button, div[data-testid="stDownloadButton"] > button {
    width: 100%; border-radius: 999px; border: 0; padding: .95rem 1rem;
    background: linear-gradient(135deg, #2f2723, #8c5d4d); color: #fff8ef;
    box-shadow: 0 14px 28px rgba(87, 48, 35, .2); font-weight: 700;
  }
  div[data-testid="stButton"] > button:hover, div[data-testid="stDownloadButton"] > button:hover {
    color: white; border: 0; transform: translateY(-1px);
  }
  .stSlider [data-baseweb="slider"] { padding-top: .25rem; }
  img { border-radius: 24px; }
  .color-chip { height: 74px; border-radius: 22px; border: 5px solid rgba(255,255,255,.78); }
</style>
"""


def main() -> None:
    st.markdown(CSS, unsafe_allow_html=True)
    invite = st.query_params.get("invite")
    if invite:
        render_b_flow(invite)
    else:
        render_a_flow()


def render_a_flow() -> None:
    if not st.session_state.get("started"):
        st.markdown(
            """
            <div class="hero">
              <div class="eyebrow">A two-person photo ritual</div>
              <div class="title">Color<br>Us</div>
              <div class="subtitle">你把我的世界染成了什么颜色？</div>
              <div class="poem">同一张风景，<br>因为你的存在，<br>有了不一样的颜色。</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("开始我们的调色", type="primary"):
            st.session_state.started = True
            st.rerun()
        return

    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.subheader("上传一张风景")
    st.caption("这张照片会成为你们共同调色的原片。建议使用横向或有天空、海面、街景的照片。")
    uploaded = st.file_uploader("选择 JPG / JPEG / PNG", type=["jpg", "jpeg", "png"], label_visibility="collapsed")

    if uploaded is None:
        st.info("上传后，你可以先调出自己眼中的颜色，再生成邀请链接。")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    original = load_image(uploaded)
    compressed = compress_image(original)
    original = bytes_to_image(compressed)

    params = adjustment_controls("a")
    preview = apply_adjustments(original, **params)
    st.image(preview, caption="你的调色预览", use_container_width=True)

    if st.button("提交我的颜色，生成邀请链接"):
        try:
            token = create_invite(compressed, params)
            st.session_state.share_link = f"{app_base_url()}/?invite={token}"
        except SupabaseNotConfigured:
            st.error("还没有配置 Supabase。请先填写 `.streamlit/secrets.toml` 或 Streamlit Cloud Secrets。")
        except Exception as exc:
            st.error(f"保存失败：{exc}")

    if st.session_state.get("share_link"):
        st.success("邀请链接已生成。把它发给对方，对方会基于同一张原图独立调色。")
        st.markdown(f'<div class="share-link">{st.session_state.share_link}</div>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)


def render_b_flow(token: str) -> None:
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown("## Color Us")
    st.caption("对方已经留下了自己的颜色。现在请你看同一张风景，但不要看 TA 的答案。")

    try:
        invite = get_invite(token)
        if invite is None:
            st.error("这个邀请链接不存在或已失效。")
            st.markdown("</div>", unsafe_allow_html=True)
            return
        original = bytes_to_image(download_original(invite["image_path"]))
    except SupabaseNotConfigured:
        st.error("还没有配置 Supabase，无法跨设备读取邀请。")
        st.markdown("</div>", unsafe_allow_html=True)
        return
    except Exception as exc:
        st.error(f"读取邀请失败：{exc}")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    params = adjustment_controls("b")
    preview = apply_adjustments(original, **params)
    st.image(preview, caption="你的调色预览", use_container_width=True)

    if st.button("生成我们的颜色"):
        a_params = {
            "temperature": int(invite["a_temperature"]),
            "saturation": int(invite["a_saturation"]),
            "brightness": int(invite["a_brightness"]),
        }
        card, a_color, b_color, blended, hex_color = create_result_card(original, a_params, params)
        st.session_state.result_card = image_to_png_bytes(card)
        st.session_state.result_hex = hex_color
        st.session_state.a_color = a_color
        st.session_state.b_color = b_color
        st.session_state.blended = blended

    if st.session_state.get("result_card"):
        render_result()
    st.markdown("</div>", unsafe_allow_html=True)


def adjustment_controls(prefix: str) -> dict[str, int]:
    st.markdown("### 调出你眼中的颜色")
    temperature = st.slider("色温", -100, 100, 0, key=f"{prefix}_temperature")
    saturation = st.slider("饱和度", 0, 200, 100, key=f"{prefix}_saturation")
    brightness = st.slider("亮度", 0, 200, 100, key=f"{prefix}_brightness")
    return {"temperature": temperature, "saturation": saturation, "brightness": brightness}


def render_result() -> None:
    st.markdown("---")
    st.markdown("## OUR COLOR")
    hex_color = st.session_state.result_hex
    st.markdown(
        f'<div class="color-chip" style="background:{hex_color}"></div><p class="hint">你们的关系代表色：<b>{hex_color}</b></p>',
        unsafe_allow_html=True,
    )
    st.image(BytesIO(st.session_state.result_card), caption="结果卡片", use_container_width=True)
    st.download_button(
        "保存我们的颜色",
        data=st.session_state.result_card,
        file_name=f"color-us-{hex_color.strip('#')}.png",
        mime="image/png",
    )


if __name__ == "__main__":
    main()
