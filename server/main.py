"""
FastAPI 后端服务
"""
import os
import json
from pathlib import Path
from typing import Optional
from datetime import datetime

from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

import sqlite3

# 加载配置
load_dotenv()

DB_PATH = os.getenv("DB_PATH", "./data/weibo_backup.db")
MEDIA_DIR = os.getenv("MEDIA_DIR", "./data/media")
SERVER_PORT = int(os.getenv("SERVER_PORT", "8000"))
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",")

app = FastAPI(title="微博备份API", version="1.0.0")

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载媒体文件目录
if Path(MEDIA_DIR).exists():
    app.mount("/media", StaticFiles(directory=MEDIA_DIR), name="media")


def get_db():
    """获取数据库连接"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@app.get("/")
def root():
    return {"message": "微博备份API", "version": "1.0.0"}


@app.get("/api/user")
def get_user():
    """获取用户信息"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users LIMIT 1")
    user = cursor.fetchone()
    conn.close()

    if user:
        return dict(user)
    return {}


@app.get("/api/posts")
def list_posts(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    q: str = Query(""),
    year: str = Query(""),
    has_media: Optional[int] = Query(None)
):
    """获取微博列表"""
    conn = get_db()
    cursor = conn.cursor()

    offset = (page - 1) * size
    conditions = []
    params = []

    if q:
        conditions.append("text_plain LIKE ?")
        params.append(f"%{q}%")

    if year:
        conditions.append("created_at LIKE ?")
        params.append(f"%{year}%")

    if has_media is not None:
        conditions.append("has_media = ?")
        params.append(has_media)

    where_clause = " AND ".join(conditions) if conditions else "1=1"

    # 获取总数
    cursor.execute(f"SELECT COUNT(*) FROM posts WHERE {where_clause}", params)
    total = cursor.fetchone()[0]

    # 获取列表
    # 由于 created_at 格式为 "Tue Oct 14 23:41:56 +0800 2025"，需要特殊处理排序
    # 按年份、月份、日期、时间降序排列（最新的在前面）
    cursor.execute(f'''
        SELECT id, user_uid, text, text_plain, created_at, source,
               reposts_count, comments_count, attitudes_count, has_media
        FROM posts
        WHERE {where_clause}
        ORDER BY
            CAST(substr(created_at, -4) AS INTEGER) DESC,
            CASE
                WHEN created_at LIKE '%Jan%' THEN 1
                WHEN created_at LIKE '%Feb%' THEN 2
                WHEN created_at LIKE '%Mar%' THEN 3
                WHEN created_at LIKE '%Apr%' THEN 4
                WHEN created_at LIKE '%May%' THEN 5
                WHEN created_at LIKE '%Jun%' THEN 6
                WHEN created_at LIKE '%Jul%' THEN 7
                WHEN created_at LIKE '%Aug%' THEN 8
                WHEN created_at LIKE '%Sep%' THEN 9
                WHEN created_at LIKE '%Oct%' THEN 10
                WHEN created_at LIKE '%Nov%' THEN 11
                WHEN created_at LIKE '%Dec%' THEN 12
                ELSE 0
            END DESC,
            CAST(substr(created_at, 9, 2) AS INTEGER) DESC,
            CAST(substr(created_at, 12, 2) AS INTEGER) DESC,
            CAST(substr(created_at, 15, 2) AS INTEGER) DESC,
            CAST(substr(created_at, 18, 2) AS INTEGER) DESC
        LIMIT ? OFFSET ?
    ''', params + [size, offset])

    posts = [dict(row) for row in cursor.fetchall()]

    conn.close()

    return {
        "total": total,
        "page": page,
        "size": size,
        "posts": posts
    }


@app.get("/api/posts/{post_id}")
def get_post(post_id: str):
    """获取微博详情"""
    conn = get_db()
    cursor = conn.cursor()

    # 获取微博
    cursor.execute("SELECT * FROM posts WHERE id = ?", (post_id,))
    post = cursor.fetchone()
    if not post:
        raise HTTPException(status_code=404, detail="微博不存在")

    post_dict = dict(post)

    # 获取图片
    cursor.execute("SELECT * FROM images WHERE post_id = ?", (post_id,))
    post_dict["images"] = [dict(row) for row in cursor.fetchall()]

    # 获取视频
    cursor.execute("SELECT * FROM videos WHERE post_id = ?", (post_id,))
    post_dict["videos"] = [dict(row) for row in cursor.fetchall()]

    # 获取评论
    cursor.execute('''
        SELECT * FROM comments WHERE post_id = ?
        ORDER BY like_count DESC, created_at ASC
    ''', (post_id,))
    comments = [dict(row) for row in cursor.fetchall()]

    # 获取每个评论的回复
    for comment in comments:
        cursor.execute('''
            SELECT * FROM replies WHERE comment_id = ?
            ORDER BY created_at ASC
        ''', (comment["id"],))
        comment["replies"] = [dict(row) for row in cursor.fetchall()]

    post_dict["comments"] = comments

    # 获取点赞用户
    cursor.execute("SELECT * FROM likes WHERE post_id = ?", (post_id,))
    post_dict["likes"] = [dict(row) for row in cursor.fetchall()]

    conn.close()
    return post_dict


@app.get("/api/search")
def search(
    q: str = Query(..., min_length=1),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100)
):
    """搜索微博"""
    conn = get_db()
    cursor = conn.cursor()

    offset = (page - 1) * size

    # 搜索微博内容
    cursor.execute('''
        SELECT id, text, text_plain, created_at, attitudes_count, comments_count
        FROM posts
        WHERE text_plain LIKE ?
        ORDER BY created_at DESC
        LIMIT ? OFFSET ?
    ''', (f"%{q}%", size, offset))

    posts = [dict(row) for row in cursor.fetchall()]

    # 获取总数
    cursor.execute('''
        SELECT COUNT(*) FROM posts WHERE text_plain LIKE ?
    ''', (f"%{q}%",))
    total = cursor.fetchone()[0]

    conn.close()

    return {
        "total": total,
        "page": page,
        "size": size,
        "keyword": q,
        "posts": posts
    }


@app.get("/api/timeline")
def get_timeline(
    year: Optional[str] = None,
    month: Optional[str] = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100)
):
    """获取时间线数据"""
    conn = get_db()
    cursor = conn.cursor()

    month_names = {
        '1': 'Jan', '2': 'Feb', '3': 'Mar', '4': 'Apr',
        '5': 'May', '6': 'Jun', '7': 'Jul', '8': 'Aug',
        '9': 'Sep', '10': 'Oct', '11': 'Nov', '12': 'Dec'
    }

    if year and month:
        # 获取某月的微博
        month_name = month_names.get(str(month), '')
        where = "WHERE created_at LIKE ? AND created_at LIKE ?"
        params = (f"%{month_name}%", f"%{year}%")
    elif year:
        # 获取某年的微博（分页）
        where = "WHERE created_at LIKE ?"
        params = (f"%{year}%",)
    else:
        # 获取所有年份列表
        cursor.execute('''
            SELECT DISTINCT substr(created_at, -4) as year
            FROM posts
            WHERE created_at IS NOT NULL
            ORDER BY year DESC
        ''')
        years = [row[0] for row in cursor.fetchall()]
        conn.close()
        return {"years": years}

    # 查询总数
    cursor.execute(f'SELECT COUNT(*) FROM posts {where}', params)
    total = cursor.fetchone()[0]

    # 分页查询（按时间倒序，created_at 是字符串格式需要转换排序）
    offset = (page - 1) * size
    cursor.execute(f'''
        SELECT id, text, text_plain, created_at, has_media,
               reposts_count, comments_count, attitudes_count
        FROM posts
        {where}
        ORDER BY
            substr(created_at, -4) DESC,
            CASE substr(created_at, 5, 3)
                WHEN 'Jan' THEN 1 WHEN 'Feb' THEN 2 WHEN 'Mar' THEN 3
                WHEN 'Apr' THEN 4 WHEN 'May' THEN 5 WHEN 'Jun' THEN 6
                WHEN 'Jul' THEN 7 WHEN 'Aug' THEN 8 WHEN 'Sep' THEN 9
                WHEN 'Oct' THEN 10 WHEN 'Nov' THEN 11 WHEN 'Dec' THEN 12
            END DESC,
            substr(created_at, 8, 2) DESC,
            substr(created_at, 11, 8) DESC
        LIMIT ? OFFSET ?
    ''', (*params, size, offset))

    posts = [dict(row) for row in cursor.fetchall()]
    conn.close()

    return {
        "posts": posts,
        "total": total,
        "page": page,
        "size": size,
        "has_more": offset + size < total
    }


@app.get("/api/on_this_day")
def on_this_day():
    """获取历史上的今天发布的微博"""
    from datetime import datetime

    conn = get_db()
    cursor = conn.cursor()

    today = datetime.now()
    month_names = {
        1: 'Jan', 2: 'Feb', 3: 'Mar', 4: 'Apr',
        5: 'May', 6: 'Jun', 7: 'Jul', 8: 'Aug',
        9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dec'
    }
    month_name = month_names[today.month]
    day = str(today.day)

    # 匹配月和日：created_at 格式 "Tue Oct 14 23:41:56 +0800 2025"
    cursor.execute('''
        SELECT id, text, text_plain, created_at, has_media
        FROM posts
        WHERE created_at LIKE ? AND created_at LIKE ?
        ORDER BY created_at DESC
    ''', (f"%{month_name}%", f"% {day} %"))

    posts = [dict(row) for row in cursor.fetchall()]
    conn.close()

    return {"posts": posts, "date": f"{today.month}月{today.day}日"}


@app.get("/api/images")
def list_images(
    page: int = Query(1, ge=1),
    size: int = Query(30, ge=1, le=100),
    sort_order: str = Query("desc", pattern="^(asc|desc)$")
):
    """获取图片列表"""
    conn = get_db()
    cursor = conn.cursor()

    offset = (page - 1) * size
    order = "ASC" if sort_order == "asc" else "DESC"

    cursor.execute(f'''
        SELECT i.*, p.text, p.text_plain, p.created_at
        FROM images i
        JOIN posts p ON i.post_id = p.id
        ORDER BY
            substr(p.created_at, -4) {order},
            CASE substr(p.created_at, 5, 3)
                WHEN 'Jan' THEN 1 WHEN 'Feb' THEN 2 WHEN 'Mar' THEN 3
                WHEN 'Apr' THEN 4 WHEN 'May' THEN 5 WHEN 'Jun' THEN 6
                WHEN 'Jul' THEN 7 WHEN 'Aug' THEN 8 WHEN 'Sep' THEN 9
                WHEN 'Oct' THEN 10 WHEN 'Nov' THEN 11 WHEN 'Dec' THEN 12
            END {order},
            substr(p.created_at, 8, 2) {order},
            substr(p.created_at, 11, 8) {order}
        LIMIT ? OFFSET ?
    ''', (size, offset))

    images = [dict(row) for row in cursor.fetchall()]

    cursor.execute("SELECT COUNT(*) FROM images")
    total = cursor.fetchone()[0]

    conn.close()

    return {
        "total": total,
        "page": page,
        "size": size,
        "images": images
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=SERVER_PORT)
