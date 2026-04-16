from __future__ import annotations

import datetime as dt
import html
import json
import math
import re
import textwrap
import urllib.request
from collections import Counter
from pathlib import Path

USER = "WangTingYeYe"
ROOT = Path("/home/ec2-user/projects/WangTingYeYe.github.io")
POSTS_DIR = ROOT / "posts"
ASSETS_DIR = ROOT / "assets"


def fetch_starred() -> list[dict]:
    page = 1
    items: list[dict] = []
    headers = {
        "Accept": "application/vnd.github.star+json",
        "User-Agent": "hermes-agent",
    }
    while True:
        url = f"https://api.github.com/users/{USER}/starred?per_page=100&page={page}"
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.load(resp)
        if not data:
            break
        items.extend(data)
        page += 1
    return items


def slugify(full_name: str) -> str:
    slug = full_name.lower().replace("/", "--")
    slug = re.sub(r"[^a-z0-9\-]+", "-", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug


def fmt_date(value: str | None) -> str:
    if not value:
        return "未知"
    try:
        return dt.datetime.fromisoformat(value.replace("Z", "+00:00")).strftime("%Y-%m-%d")
    except Exception:
        return value


def nice_num(n: int | None) -> str:
    if n is None:
        return "未知"
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n/1_000:.1f}k"
    return str(n)


def desc_text(repo: dict) -> str:
    desc = (repo.get("description") or "").strip()
    if desc:
        return desc
    return "这个仓库没有写很长的简介，但从公开信息看，它仍然值得单独留个书签和一篇介绍。"


def extract_cn_keywords(repo: dict) -> list[str]:
    text = " ".join([
        repo.get("name", ""),
        repo.get("full_name", ""),
        repo.get("description", "") or "",
        repo.get("language", "") or "",
        " ".join(repo.get("topics", []) or []),
    ]).lower()
    mapping = [
        ("AI Agent", ["agent", "agents", "ai-agent"]),
        ("工作流自动化", ["workflow", "automation", "automate", "pipeline"]),
        ("MCP", ["mcp"]),
        ("提示词工程", ["prompt", "prompts", "system prompt"]),
        ("设计系统", ["design-system", "design", "ui", "ux", "component"]),
        ("前端界面", ["frontend", "react", "vue", "nextjs", "css", "tailwind"]),
        ("命令行工具", ["cli", "terminal", "shell"]),
        ("知识库 / RAG", ["rag", "knowledge", "search", "retrieval", "vector"]),
        ("模型训练", ["training", "finetune", "fine-tuning", "lora", "rl"]),
        ("推理服务", ["inference", "serving", "vllm", "llama.cpp"]),
        ("数据库", ["database", "postgres", "mysql", "redis", "sql"]),
        ("可视化", ["graph", "diagram", "visual", "draw", "svg"]),
        ("文档系统", ["docs", "documentation", "mkdocs"]),
        ("浏览器能力", ["browser", "web"]),
        ("音视频", ["audio", "video", "speech", "voice"]),
        ("图像生成", ["image", "diffusion", "sd", "comfyui"]),
        ("开发效率", ["productivity", "tool", "tools", "setup"]),
        ("系统设计", ["system-design", "architecture"]),
        ("移动开发", ["ios", "android", "flutter", "react native"]),
    ]
    found: list[str] = []
    for label, keywords in mapping:
        if any(k in text for k in keywords):
            found.append(label)
    return found[:4]


def cn_summary(repo: dict, category: str) -> str:
    keys = extract_cn_keywords(repo)
    language = repo.get("language") or "通用技术栈"
    if keys:
        core = "、".join(keys[:3])
        return f"这是一个偏 {category} 方向的开源项目，核心关注 {core}，并且更适合作为 {language} 生态下的参考实现或灵感来源。"
    return f"这是一个偏 {category} 方向的开源项目。虽然公开简介不算特别长，但从仓库主题、语言和社区热度看，它已经具备被单独记录和后续跟进的价值。"


def infer_category(repo: dict) -> str:
    text = " ".join([
        repo.get("name", ""),
        repo.get("full_name", ""),
        repo.get("description", "") or "",
        repo.get("language", "") or "",
        " ".join(repo.get("topics", []) or []),
    ]).lower()
    rules = [
        ("AI / Agent", ["ai", "agent", "llm", "claude", "openai", "rag", "mcp", "prompt", "copilot", "gemini"]),
        ("前端 / 设计", ["react", "vue", "css", "tailwind", "frontend", "design", "ui", "nextjs", "component"]),
        ("数据 / 机器学习", ["pytorch", "tensorflow", "model", "machine learning", "ml", "dataset", "training", "evaluation"]),
        ("基础设施 / DevOps", ["docker", "kubernetes", "terraform", "infra", "devops", "cloud", "ci", "observability"]),
        ("数据库 / 存储", ["database", "postgres", "mysql", "redis", "vector", "search", "sql"]),
        ("移动 / 客户端", ["ios", "android", "swift", "kotlin", "flutter", "react native"]),
        ("开发工具", ["cli", "terminal", "editor", "plugin", "tool", "sdk", "library"]),
    ]
    for label, keywords in rules:
        if any(k in text for k in keywords):
            return label
    return "开源项目观察"


def infer_audience(category: str, repo: dict) -> str:
    language = repo.get("language") or "通用"
    mapping = {
        "AI / Agent": "适合正在关注 AI Agent、工作流自动化、LLM 工具链的开发者和产品人。",
        "前端 / 设计": "适合做前端界面、设计系统、组件库或个人站点的开发者。",
        "数据 / 机器学习": "适合做模型训练、推理、评测或数据工程的同学。",
        "基础设施 / DevOps": "适合负责部署、平台工程、CI/CD 与工程效率建设的人。",
        "数据库 / 存储": "适合需要处理检索、存储、数据库架构或数据基础设施的人。",
        "移动 / 客户端": "适合关注移动端体验、跨端开发或客户端架构的开发者。",
        "开发工具": f"适合想提升 {language} 开发效率、优化工具链或寻找顺手开源工具的人。",
        "开源项目观察": "适合把 GitHub 当作信息流和灵感来源，持续追踪优秀开源项目的人。",
    }
    return mapping.get(category, mapping["开源项目观察"])


def infer_interest(category: str, repo: dict) -> str:
    language = repo.get("language") or "技术栈"
    stars = repo.get("stargazers_count", 0)
    stars_text = nice_num(stars)
    desc = desc_text(repo)
    if category == "AI / Agent":
        return f"我会先 star 它，通常是因为它和 AI Agent / 自动化工作流高度相关，而且社区热度已经到了 {stars_text} 这个量级，说明它不只是一个零散 demo。"
    if category == "前端 / 设计":
        return f"这类项目对我来说最大的价值，是它能直接影响界面表达与交互方式。看到它已经积累了 {stars_text} 个 star，我会把它放进自己的设计和开发参考库。"
    if category == "开发工具":
        return f"我很容易被这类项目吸引，因为它往往能直接改变日常工作流。哪怕只是一个小工具，只要能明显提效，我都会记一笔。当前简介是：{desc}"
    return f"我 star 它，往往不是为了收藏数字，而是为了给以后真正需要的时候留一个入口。这个项目现在已经有 {stars_text} 个 star，也说明它已经被不少人验证过。"


def render_article(item: dict, total_count: int) -> tuple[str, str, str]:
    repo = item["repo"]
    full_name = repo["full_name"]
    slug = slugify(full_name)
    title = f"项目推荐：{full_name}"
    description = desc_text(repo)
    category = infer_category(repo)
    summary_cn = cn_summary(repo, category)
    audience = infer_audience(category, repo)
    interest = infer_interest(category, repo)
    topics = repo.get("topics", []) or []
    topics_html = "".join(f'<span class="chip">{html.escape(t)}</span>' for t in topics[:8]) or '<span class="chip">暂无 topics</span>'
    language = repo.get("language") or "未标注"
    starred_at = fmt_date(item.get("starred_at"))
    updated_at = fmt_date(repo.get("updated_at"))
    stars = nice_num(repo.get("stargazers_count"))
    forks = nice_num(repo.get("forks_count"))
    homepage = repo.get("homepage") or repo.get("html_url")

    summary = f"这是一篇写给未来自己的书签笔记：我在 {starred_at} 把 {full_name} 加入了 GitHub Star 列表。{summary_cn}"

    article_html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{html.escape(title)} · Yeah！Buddy</title>
  <meta name="description" content="{html.escape(description[:140])}" />
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet" />
  <link rel="stylesheet" href="../assets/blog.css" />
</head>
<body>
  <header class="site-header">
    <div class="container header-inner">
      <a class="brand" href="../index.html"><span class="brand-dot"></span><span>Yeah！Buddy</span></a>
      <nav class="nav">
        <a href="../index.html">首页</a>
        <a href="index.html">全部文章</a>
        <a href="{html.escape(repo['html_url'])}" target="_blank" rel="noreferrer">GitHub 仓库</a>
      </nav>
    </div>
  </header>

  <main class="container article-shell">
    <article class="article-card">
      <div class="article-meta-top">
        <span class="pill">{html.escape(category)}</span>
        <span>Star 时间：{starred_at}</span>
        <span>文章编号：{slug}</span>
      </div>
      <h1>{html.escape(title)}</h1>
      <p class="lead">{html.escape(summary)}</p>

      <section>
        <h2>项目是什么</h2>
        <p><strong>{html.escape(full_name)}</strong> 是一个我在 GitHub 上主动收藏的开源项目。{html.escape(summary_cn)} 从语言与主题来看，它更偏向 <strong>{html.escape(category)}</strong> 方向，目前主语言是 <strong>{html.escape(language)}</strong>。</p>
        <p class="quote-text"><strong>官方简介：</strong>{html.escape(description)}</p>
      </section>

      <section>
        <h2>我为什么会 Star 它</h2>
        <p>{html.escape(interest)}</p>
        <p>另一个很现实的原因是，这类项目通常代表着某个方向当前最活跃的做法。把它们写成博客而不只是点个 star，未来回看时更容易知道：我当时到底看中了它什么。</p>
      </section>

      <section>
        <h2>适合谁关注</h2>
        <p>{html.escape(audience)}</p>
      </section>

      <section>
        <h2>项目速览</h2>
        <ul class="stats-list">
          <li><strong>仓库：</strong><a href="{html.escape(repo['html_url'])}" target="_blank" rel="noreferrer">{html.escape(full_name)}</a></li>
          <li><strong>主页：</strong><a href="{html.escape(homepage)}" target="_blank" rel="noreferrer">{html.escape(homepage)}</a></li>
          <li><strong>主语言：</strong>{html.escape(language)}</li>
          <li><strong>Stars：</strong>{stars}</li>
          <li><strong>Forks：</strong>{forks}</li>
          <li><strong>最近更新：</strong>{updated_at}</li>
          <li><strong>总专栏规模：</strong>当前博客已生成 {total_count} 篇 Star 项目介绍</li>
        </ul>
      </section>

      <section>
        <h2>关键词</h2>
        <div class="chip-wrap">{topics_html}</div>
      </section>

      <section>
        <h2>我的备注</h2>
        <p>这篇文章基于 GitHub 上的公开仓库信息整理，目标不是替代官方文档，而是把「为什么它值得被我收藏」这件事写清楚。等我真正上手或深入读完代码后，可以继续把这篇文章补成更完整的使用心得。</p>
      </section>

      <div class="article-footer-links">
        <a class="button primary" href="index.html">查看全部文章</a>
        <a class="button secondary" href="{html.escape(repo['html_url'])}" target="_blank" rel="noreferrer">打开 GitHub 仓库</a>
      </div>
    </article>
  </main>
</body>
</html>
'''
    excerpt = cn_summary(repo, category)
    return slug, title, excerpt, article_html, category, starred_at


def render_posts_index(posts: list[dict], category_counts: Counter) -> str:
    cards = []
    for p in posts:
        cards.append(f'''
        <article class="post-card">
          <div class="post-card-top"><span class="pill">{html.escape(p['category'])}</span><span>{html.escape(p['starred_at'])}</span></div>
          <h3><a href="{html.escape(p['slug'])}.html">{html.escape(p['title'])}</a></h3>
          <p>{html.escape(p['excerpt'])}</p>
          <div class="post-card-bottom"><a href="{html.escape(p['slug'])}.html">阅读全文</a><span>{html.escape(p['full_name'])}</span></div>
        </article>
        ''')
    category_html = ''.join(f'<span class="chip">{html.escape(k)} · {v}</span>' for k, v in category_counts.most_common())
    return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>GitHub Star 项目文章归档 · Yeah！Buddy</title>
  <meta name="description" content="我把 GitHub Star 过的项目，逐个整理成博客文章。" />
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet" />
  <link rel="stylesheet" href="../assets/blog.css" />
</head>
<body>
  <header class="site-header">
    <div class="container header-inner">
      <a class="brand" href="../index.html"><span class="brand-dot"></span><span>Yeah！Buddy</span></a>
      <nav class="nav">
        <a href="../index.html">首页</a>
        <a href="#all">全部文章</a>
        <a href="https://github.com/{USER}?tab=stars" target="_blank" rel="noreferrer">我的 Stars</a>
      </nav>
    </div>
  </header>

  <main class="container archive-shell" id="all">
    <section class="hero-block">
      <span class="eyebrow">GitHub Stars → Blog Posts</span>
      <h1>我把 GitHub Star 过的项目，逐个写成了博客介绍。</h1>
      <p class="lead">目前共整理 <strong>{len(posts)}</strong> 篇，目标不是机械罗列，而是把「这个项目为什么值得我专门留一笔」记录下来，方便以后检索、回顾和继续扩写。</p>
      <div class="chip-wrap">{category_html}</div>
    </section>

    <section class="cards-grid posts-grid">
      {''.join(cards)}
    </section>
  </main>
</body>
</html>
'''


def render_home(posts: list[dict], category_counts: Counter, total_count: int) -> str:
    featured = posts[:6]
    featured_html = ''.join(
        f'''
        <article class="post-card compact">
          <div class="post-card-top"><span class="pill">{html.escape(p['category'])}</span><span>{html.escape(p['starred_at'])}</span></div>
          <h3><a href="posts/{html.escape(p['slug'])}.html">{html.escape(p['title'])}</a></h3>
          <p>{html.escape(p['excerpt'])}</p>
          <div class="post-card-bottom"><a href="posts/{html.escape(p['slug'])}.html">阅读全文</a><span>{html.escape(p['full_name'])}</span></div>
        </article>
        ''' for p in featured
    )
    cats = ''.join(f'<span class="chip">{html.escape(k)} · {v}</span>' for k, v in category_counts.most_common(6))
    return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Yeah！Buddy — 个人博客</title>
  <meta name="description" content="把 GitHub Star 过的项目逐个写成博客介绍的个人博客。" />
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet" />
  <link rel="stylesheet" href="assets/blog.css" />
</head>
<body>
  <header class="site-header">
    <div class="container header-inner">
      <a class="brand" href="index.html"><span class="brand-dot"></span><span>Yeah！Buddy</span></a>
      <nav class="nav">
        <a href="#latest">最新文章</a>
        <a href="posts/index.html">Star 专栏</a>
        <a href="#about">关于</a>
        <a class="button small primary" href="https://github.com/{USER}?tab=stars" target="_blank" rel="noreferrer">我的 Stars</a>
      </nav>
    </div>
  </header>

  <main>
    <section class="container hero-block homepage-hero">
      <span class="eyebrow">Personal Blog · Starred Projects Notebook</span>
      <h1>我把 GitHub Star 的每个项目，都写成了一篇博客介绍。</h1>
      <p class="lead">这版博客不再只是一个自我介绍页，而是一个真正会持续增长的内容首页。现在已经收录 <strong>{total_count}</strong> 篇项目文章，来自我在 GitHub 上收藏过的全部公开 Star 项目。</p>
      <div class="hero-actions">
        <a class="button primary" href="posts/index.html">浏览全部 {total_count} 篇文章</a>
        <a class="button secondary" href="#latest">先看最新发布</a>
      </div>
      <div class="chip-wrap">{cats}</div>
    </section>

    <section class="container section-block" id="latest">
      <div class="section-heading">
        <div>
          <h2>最新发布</h2>
          <p>按 Star 时间倒序整理。每一篇都是一个未来可继续补充的项目笔记入口。</p>
        </div>
        <a class="text-link" href="posts/index.html">查看全部文章 →</a>
      </div>
      <div class="cards-grid posts-grid">{featured_html}</div>
    </section>

    <section class="container two-col-block" id="about">
      <div class="panel-card">
        <h2>关于这个博客</h2>
        <p>我在 GitHub 上经常用 Star 记录感兴趣的项目，但单纯点星标很容易忘。于是这次我把所有公开 Star 项目都转成了博客文章：每个项目一篇，尽量写清楚它是什么、为什么值得关注、适合谁看，以及我为什么会把它留下来。</p>
        <p>这让博客从“展示页”变成了真正的知识索引：首页看的是最近更新，归档页看的是全部收藏，单篇文章则是以后可以继续补体验和复盘的入口。</p>
      </div>
      <div class="panel-card">
        <h2>关于我</h2>
        <p><strong>Yeah！Buddy</strong> / <strong>@{USER}</strong></p>
        <p>主要关注 AI Agent、MCP、自动化工作流、开发工具、个人产品实验，以及那些值得长期追踪的开源项目。</p>
        <div class="chip-wrap">
          <span class="chip">AI Agent</span>
          <span class="chip">MCP</span>
          <span class="chip">Automation</span>
          <span class="chip">Open Source</span>
          <span class="chip">Personal Blog</span>
        </div>
      </div>
    </section>
  </main>
</body>
</html>
'''


def render_css() -> str:
    return textwrap.dedent('''
    :root {
      --bg: #ffffff;
      --surface: #ffffff;
      --surface-alt: #f6f5f4;
      --text: rgba(0,0,0,0.95);
      --text-soft: #615d59;
      --text-faint: #a39e98;
      --line: rgba(0,0,0,0.1);
      --blue: #0075de;
      --blue-dark: #005bab;
      --blue-soft: #f2f9ff;
      --shadow: rgba(0,0,0,0.04) 0px 4px 18px, rgba(0,0,0,0.027) 0px 2px 8px, rgba(0,0,0,0.02) 0px 1px 3px;
      --max: 1080px;
      --radius: 16px;
      --pill: 9999px;
    }
    * { box-sizing: border-box; }
    html { scroll-behavior: smooth; }
    body {
      margin: 0;
      font-family: 'Inter', system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif;
      color: var(--text);
      background: linear-gradient(180deg, #fff 0%, #fff 60%, #fbfbfa 100%);
      line-height: 1.68;
    }
    a { color: inherit; text-decoration: none; }
    .container { width: min(calc(100% - 32px), var(--max)); margin: 0 auto; }
    .site-header {
      position: sticky; top: 0; z-index: 10;
      background: rgba(255,255,255,0.88); backdrop-filter: blur(14px);
      border-bottom: 1px solid var(--line);
    }
    .header-inner { min-height: 68px; display:flex; align-items:center; justify-content:space-between; gap:18px; }
    .brand { display:inline-flex; align-items:center; gap:12px; font-size:15px; font-weight:700; letter-spacing:-0.02em; }
    .brand-dot { width:10px; height:10px; border-radius:50%; background:var(--blue); box-shadow: 0 0 0 6px rgba(0,117,222,0.12); }
    .nav { display:flex; align-items:center; gap:18px; flex-wrap:wrap; color:var(--text-soft); font-size:14px; font-weight:600; }
    .nav a:hover, .text-link:hover { color: var(--text); }
    .hero-block, .article-card, .panel-card, .post-card {
      background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius); box-shadow: var(--shadow);
    }
    .homepage-hero, .hero-block { padding: 28px; margin-top: 32px; }
    .hero-block h1, .article-card h1 { margin: 16px 0 12px; font-size: clamp(36px, 7vw, 60px); line-height: 1.02; letter-spacing: -0.05em; }
    .lead { font-size: 19px; color: var(--text-soft); margin: 0; max-width: 820px; }
    .eyebrow, .pill {
      display:inline-flex; align-items:center; gap:8px; padding:6px 10px; border-radius: var(--pill); font-size:12px; font-weight:700;
    }
    .eyebrow { background: var(--blue-soft); color: var(--blue); letter-spacing:0.04em; text-transform: uppercase; }
    .pill { background: var(--blue-soft); color: var(--blue); }
    .button {
      display:inline-flex; align-items:center; justify-content:center; gap:8px; padding:10px 16px; border-radius:6px; font-size:14px; font-weight:600; border:1px solid transparent; transition:.2s ease;
    }
    .button.small { padding: 9px 14px; }
    .button.primary { background: var(--blue); color: #fff; box-shadow: var(--shadow); }
    .button.primary:hover { background: var(--blue-dark); transform: translateY(-1px); }
    .button.secondary { background: rgba(0,0,0,0.04); border-color: var(--line); color: var(--text); }
    .button.secondary:hover { background: rgba(0,0,0,0.06); }
    .hero-actions { display:flex; gap:12px; flex-wrap:wrap; margin: 24px 0 18px; }
    .chip-wrap { display:flex; flex-wrap:wrap; gap:10px; margin-top: 16px; }
    .chip { padding: 6px 10px; border-radius: var(--pill); border: 1px solid var(--line); background: var(--surface-alt); font-size: 12px; font-weight: 600; }
    .section-block { padding: 26px 0 56px; }
    .section-heading { display:flex; justify-content:space-between; align-items:end; gap:18px; margin-bottom:20px; }
    .section-heading h2, .panel-card h2, .article-card h2 { margin:0 0 8px; font-size: clamp(28px, 5vw, 40px); line-height:1.05; letter-spacing:-0.04em; }
    .section-heading p, .panel-card p, .article-card p { color: var(--text-soft); }
    .cards-grid { display:grid; gap:16px; }
    .posts-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    .post-card { padding: 20px; display:grid; gap:12px; }
    .post-card.compact h3 { font-size: 24px; }
    .post-card-top, .post-card-bottom, .article-meta-top { display:flex; justify-content:space-between; gap:12px; align-items:center; flex-wrap:wrap; color: var(--text-faint); font-size:13px; }
    .post-card h3 { margin:0; font-size: 28px; line-height:1.15; letter-spacing:-0.03em; }
    .post-card p { margin:0; color: var(--text-soft); }
    .two-col-block { display:grid; grid-template-columns: 1.1fr 0.9fr; gap:18px; padding: 0 0 64px; }
    .panel-card { padding: 22px; }
    .article-shell { padding: 32px 0 64px; }
    .article-card { padding: 28px; }
    .article-card section { margin-top: 28px; }
    .quote-text { padding: 14px 16px; background: var(--surface-alt); border-left: 3px solid var(--blue); border-radius: 10px; }
    .stats-list { padding-left: 18px; color: var(--text-soft); }
    .stats-list li { margin: 8px 0; }
    .article-footer-links { display:flex; gap:12px; flex-wrap:wrap; margin-top: 28px; }
    .archive-shell { padding: 32px 0 64px; }
    @media (max-width: 900px) {
      .posts-grid, .two-col-block { grid-template-columns: 1fr; }
      .section-heading { flex-direction:column; align-items:start; }
    }
    @media (max-width: 720px) {
      .header-inner { min-height: unset; padding: 14px 0; align-items:start; flex-direction: column; }
      .nav { gap: 12px; }
      .homepage-hero, .hero-block, .article-card, .panel-card, .post-card { padding: 18px; }
      .hero-block h1, .article-card h1 { font-size: clamp(32px, 12vw, 44px); }
      .lead { font-size: 17px; }
      .post-card h3 { font-size: 22px; }
    }
    ''').strip() + "\n"


def main() -> None:
    POSTS_DIR.mkdir(parents=True, exist_ok=True)
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)

    starred = fetch_starred()
    posts = []
    categories = Counter()

    for item in starred:
        slug, title, excerpt, article_html, category, starred_at = render_article(item, len(starred))
        full_name = item['repo']['full_name']
        (POSTS_DIR / f"{slug}.html").write_text(article_html, encoding="utf-8")
        posts.append({
            "slug": slug,
            "title": title,
            "excerpt": excerpt,
            "category": category,
            "starred_at": starred_at,
            "full_name": full_name,
        })
        categories[category] += 1

    (ASSETS_DIR / "blog.css").write_text(render_css(), encoding="utf-8")
    (POSTS_DIR / "index.html").write_text(render_posts_index(posts, categories), encoding="utf-8")
    (ROOT / "index.html").write_text(render_home(posts, categories, len(posts)), encoding="utf-8")
    (ROOT / "starred_repos.json").write_text(json.dumps(starred, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps({
        "posts_generated": len(posts),
        "categories": categories,
        "sample_posts": posts[:3],
    }, ensure_ascii=False, default=lambda x: dict(x)))


if __name__ == "__main__":
    main()
