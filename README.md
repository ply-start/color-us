# Color Us

中文名：你把我的世界染成了什么颜色？

一个可部署到 Streamlit Community Cloud 的 H5 双人互动小游戏。玩家 A 上传同一张风景照片并调色，生成邀请链接；玩家 B 打开链接后基于同一张原图独立调色，系统融合两人的代表色并生成可下载结果卡片。

## 文件结构

```text
.
├── app.py
├── image_utils.py
├── database.py
├── requirements.txt
├── README.md
├── supabase_schema.sql
├── .gitignore
└── .streamlit
    ├── config.toml
    └── secrets.toml.example
```

## 本地启动

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .streamlit\secrets.toml.example .streamlit\secrets.toml
streamlit run app.py
```

启动前需要先完成 Supabase 配置，否则首页可以打开，但无法生成跨设备邀请链接。

## Supabase 配置

1. 新建 Supabase Project。
2. 进入 SQL Editor，执行 `supabase_schema.sql`。
3. 进入 Storage，创建 public bucket：`color-us-photos`。
4. 确认 `supabase_schema.sql` 中的 Storage policies 已执行成功。
5. 在 Project Settings > API 获取 `Project URL` 和 `anon public` key。
6. 本地复制 `.streamlit/secrets.toml.example` 为 `.streamlit/secrets.toml`，填写：

```toml
SUPABASE_URL = "https://your-project.supabase.co"
SUPABASE_ANON_KEY = "your-anon-key"
SUPABASE_BUCKET = "color-us-photos"
APP_BASE_URL = "http://localhost:8501"
```

## Streamlit Community Cloud 部署

1. 将项目推送到 GitHub。
2. 在 Streamlit Community Cloud 新建 App，入口文件选择 `app.py`。
3. 在 App settings > Secrets 中填写与本地一致的 secrets。
4. 将 `APP_BASE_URL` 改为部署后的应用地址，例如：

```toml
APP_BASE_URL = "https://your-app.streamlit.app"
```

5. 部署后，用手机打开首页上传照片，生成邀请链接，再用另一台设备打开链接测试 B 流程。

## 数据说明

数据库表 `color_us_invites` 保存：

- `token`
- `image_path`
- `a_temperature`
- `a_saturation`
- `a_brightness`
- `created_at`

Storage bucket `color-us-photos` 保存压缩后的原始照片。B 只能根据 token 读取原图，不会看到 A 的调色预览。

## 尚需人工测试

- Supabase 真实项目的匿名插入、读取和 Storage 上传下载权限。
- Streamlit Cloud 部署域名下邀请链接是否正确跳转。
- iOS Safari、Android Chrome 的上传、滑块拖动和图片下载体验。
- 大尺寸照片在目标手机上的上传耗时。
