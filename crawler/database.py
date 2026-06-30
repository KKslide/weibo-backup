"""
数据库操作模块
"""
import sqlite3
import json
from datetime import datetime
from pathlib import Path


class Database:
    def __init__(self, db_path: str):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.init_db()

    def get_conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        """初始化数据库表结构"""
        conn = self.get_conn()
        cursor = conn.cursor()

        # 用户信息表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                uid TEXT PRIMARY KEY,
                screen_name TEXT,
                avatar_url TEXT,
                description TEXT,
                followers_count INTEGER DEFAULT 0,
                follow_count INTEGER DEFAULT 0,
                statuses_count INTEGER DEFAULT 0,
                verified INTEGER DEFAULT 0,
                verified_reason TEXT,
                raw_json TEXT,
                crawled_at TEXT,
                comment_count INTEGER DEFAULT 0,
                repost_count INTEGER DEFAULT 0,
                like_count INTEGER DEFAULT 0,
                total_engagement INTEGER DEFAULT 0
            )
        ''')

        # 微博主表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS posts (
                id TEXT PRIMARY KEY,
                user_uid TEXT,
                text TEXT,
                text_plain TEXT,
                created_at TEXT,
                source TEXT,
                reposts_count INTEGER DEFAULT 0,
                comments_count INTEGER DEFAULT 0,
                attitudes_count INTEGER DEFAULT 0,
                topics TEXT,
                at_users TEXT,
                has_media INTEGER DEFAULT 0,
                is_retweet INTEGER DEFAULT 0,
                retweet_id TEXT,
                raw_json TEXT,
                crawled_at TEXT,
                FOREIGN KEY (user_uid) REFERENCES users(uid)
            )
        ''')

        # 图片表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS images (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                post_id TEXT NOT NULL,
                url TEXT NOT NULL,
                local_path TEXT,
                width INTEGER,
                height INTEGER,
                FOREIGN KEY (post_id) REFERENCES posts(id)
            )
        ''')

        # 视频表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS videos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                post_id TEXT NOT NULL,
                url TEXT,
                cover_url TEXT,
                local_path TEXT,
                duration INTEGER,
                FOREIGN KEY (post_id) REFERENCES posts(id)
            )
        ''')

        # 评论表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS comments (
                id TEXT PRIMARY KEY,
                post_id TEXT NOT NULL,
                user_uid TEXT,
                user_name TEXT,
                user_avatar TEXT,
                text TEXT,
                created_at TEXT,
                like_count INTEGER DEFAULT 0,
                floor_number INTEGER DEFAULT 0,
                raw_json TEXT,
                FOREIGN KEY (post_id) REFERENCES posts(id)
            )
        ''')

        # 评论回复表（楼中楼）
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS replies (
                id TEXT PRIMARY KEY,
                comment_id TEXT NOT NULL,
                post_id TEXT NOT NULL,
                user_uid TEXT,
                user_name TEXT,
                reply_to_uid TEXT,
                reply_to_name TEXT,
                text TEXT,
                created_at TEXT,
                raw_json TEXT,
                FOREIGN KEY (comment_id) REFERENCES comments(id),
                FOREIGN KEY (post_id) REFERENCES posts(id)
            )
        ''')

        # 点赞表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS likes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                post_id TEXT NOT NULL,
                user_uid TEXT,
                user_name TEXT,
                user_avatar TEXT,
                raw_json TEXT,
                FOREIGN KEY (post_id) REFERENCES posts(id)
            )
        ''')

        # 爬取进度表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS crawl_progress (
                task_type TEXT PRIMARY KEY,
                last_id TEXT,
                last_page INTEGER DEFAULT 0,
                updated_at TEXT
            )
        ''')

        conn.commit()
        conn.close()

        # 执行迁移
        self._migrate()

    def _migrate(self):
        """数据库迁移 - 为现有表添加新字段"""
        conn = self.get_conn()
        cursor = conn.cursor()

        # 检查 users 表是否有新字段，没有则添加
        cursor.execute("PRAGMA table_info(users)")
        columns = [row[1] for row in cursor.fetchall()]

        if 'comment_count' not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN comment_count INTEGER DEFAULT 0")
        if 'repost_count' not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN repost_count INTEGER DEFAULT 0")
        if 'like_count' not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN like_count INTEGER DEFAULT 0")
        if 'total_engagement' not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN total_engagement INTEGER DEFAULT 0")

        conn.commit()
        conn.close()

    def save_user(self, user_data: dict):
        """保存用户信息"""
        conn = self.get_conn()
        cursor = conn.cursor()

        # 从 status_total_counter 获取转评赞数据
        counter = user_data.get('status_total_counter', {})

        cursor.execute('''
            INSERT OR REPLACE INTO users
            (uid, screen_name, avatar_url, description, followers_count, follow_count,
             statuses_count, verified, verified_reason, raw_json, crawled_at,
             comment_count, repost_count, like_count, total_engagement)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            str(user_data.get('id', '')),
            user_data.get('screen_name', ''),
            user_data.get('avatar_hd', user_data.get('profile_image_url', '')),
            user_data.get('description', ''),
            user_data.get('followers_count', 0),
            user_data.get('friends_count', user_data.get('follow_count', 0)),
            user_data.get('statuses_count', 0),
            1 if user_data.get('verified') else 0,
            user_data.get('verified_reason', ''),
            json.dumps(user_data, ensure_ascii=False),
            datetime.now().isoformat(),
            int(counter.get('comment_cnt', 0)),
            int(counter.get('repost_cnt', 0)),
            int(counter.get('like_cnt', 0)),
            int(str(counter.get('total_cnt', 0)).replace(',', ''))
        ))
        conn.commit()
        conn.close()

    def save_post(self, post_data: dict) -> bool:
        """保存微博，返回是否为新数据"""
        conn = self.get_conn()
        cursor = conn.cursor()

        # 检查是否已存在
        cursor.execute("SELECT id FROM posts WHERE id = ?", (str(post_data['id']),))
        if cursor.fetchone():
            conn.close()
            return False

        # 解析话题和@用户
        topics = json.dumps(post_data.get('topics', []), ensure_ascii=False)
        at_users = json.dumps(post_data.get('at_users', []), ensure_ascii=False)

        # 清理HTML标签获取纯文本
        text = post_data.get('text', '')
        text_plain = self._strip_html(text)

        cursor.execute('''
            INSERT INTO posts
            (id, user_uid, text, text_plain, created_at, source, reposts_count,
             comments_count, attitudes_count, topics, at_users, has_media,
             is_retweet, retweet_id, raw_json, crawled_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            str(post_data['id']),
            str(post_data.get('user', {}).get('id', '')),
            text,
            text_plain,
            post_data.get('created_at', ''),
            post_data.get('source', ''),
            post_data.get('reposts_count', 0),
            post_data.get('comments_count', 0),
            post_data.get('attitudes_count', 0),
            topics,
            at_users,
            1 if post_data.get('pics') or post_data.get('page_info') else 0,
            1 if post_data.get('retweeted_status') else 0,
            str(post_data.get('retweeted_status', {}).get('id', '')),
            json.dumps(post_data, ensure_ascii=False),
            datetime.now().isoformat()
        ))
        conn.commit()
        conn.close()
        return True

    def update_post_text(self, post_id: str, long_text: str):
        """更新超长博文的完整文本"""
        conn = self.get_conn()
        cursor = conn.cursor()
        # 将 \n 转为 <br /> 保持HTML格式，和微博原始 text 格式一致
        text_html = long_text.replace("\n", "<br />")
        cursor.execute('''
            UPDATE posts SET text = ?, text_plain = ? WHERE id = ?
        ''', (text_html, long_text, post_id))
        conn.commit()
        conn.close()

    def save_images(self, post_id: str, images: list):
        """保存图片记录"""
        conn = self.get_conn()
        cursor = conn.cursor()

        # 先删除旧记录
        cursor.execute("DELETE FROM images WHERE post_id = ?", (post_id,))

        for img in images:
            cursor.execute('''
                INSERT INTO images (post_id, url, local_path, width, height)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                post_id,
                img.get('url', ''),
                img.get('local_path', ''),
                img.get('width', 0),
                img.get('height', 0)
            ))

        conn.commit()
        conn.close()

    def save_video(self, post_id: str, video_data: dict):
        """保存视频记录"""
        conn = self.get_conn()
        cursor = conn.cursor()

        # 先删除旧记录
        cursor.execute("DELETE FROM videos WHERE post_id = ?", (post_id,))

        cursor.execute('''
            INSERT INTO videos (post_id, url, cover_url, local_path, duration)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            post_id,
            video_data.get('url', ''),
            video_data.get('cover_url', ''),
            video_data.get('local_path', ''),
            video_data.get('duration', 0)
        ))

        conn.commit()
        conn.close()

    def save_comment(self, comment_data: dict, post_id: str) -> bool:
        """保存评论，返回是否为新插入"""
        conn = self.get_conn()
        cursor = conn.cursor()

        comment_id = str(comment_data['id'])
        cursor.execute("SELECT id FROM comments WHERE id = ?", (comment_id,))
        if cursor.fetchone():
            conn.close()
            return False

        cursor.execute('''
            INSERT INTO comments
            (id, post_id, user_uid, user_name, user_avatar, text, created_at,
             like_count, floor_number, raw_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            comment_id,
            post_id,
            str(comment_data.get('user', {}).get('id', '')),
            comment_data.get('user', {}).get('screen_name', ''),
            comment_data.get('user', {}).get('profile_image_url', ''),
            comment_data.get('text', ''),
            comment_data.get('created_at', ''),
            comment_data.get('like_count', 0),
            comment_data.get('floor_number', 0),
            json.dumps(comment_data, ensure_ascii=False)
        ))

        conn.commit()
        conn.close()
        return True

    def save_reply(self, reply_data: dict, comment_id: str, post_id: str) -> bool:
        """保存回复，返回是否为新插入"""
        conn = self.get_conn()
        cursor = conn.cursor()

        reply_id = str(reply_data['id'])
        cursor.execute("SELECT id FROM replies WHERE id = ?", (reply_id,))
        if cursor.fetchone():
            conn.close()
            return False

        cursor.execute('''
            INSERT INTO replies
            (id, comment_id, post_id, user_uid, user_name, reply_to_uid,
             reply_to_name, text, created_at, raw_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            reply_id,
            comment_id,
            post_id,
            str(reply_data.get('user', {}).get('id', '')),
            reply_data.get('user', {}).get('screen_name', ''),
            str(reply_data.get('reply_comment', {}).get('user', {}).get('id', '')),
            reply_data.get('reply_comment', {}).get('user', {}).get('screen_name', ''),
            reply_data.get('text', ''),
            reply_data.get('created_at', ''),
            json.dumps(reply_data, ensure_ascii=False)
        ))

        conn.commit()
        conn.close()
        return True

    def save_likes(self, post_id: str, likes: list):
        """保存点赞记录"""
        conn = self.get_conn()
        cursor = conn.cursor()

        for like in likes:
            cursor.execute('''
                INSERT OR IGNORE INTO likes (post_id, user_uid, user_name, user_avatar, raw_json)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                post_id,
                str(like.get('user', {}).get('id', '')),
                like.get('user', {}).get('screen_name', ''),
                like.get('user', {}).get('profile_image_url', ''),
                json.dumps(like, ensure_ascii=False)
            ))

        conn.commit()
        conn.close()

    def get_progress(self, task_type: str) -> dict:
        """获取爬取进度"""
        conn = self.get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM crawl_progress WHERE task_type = ?", (task_type,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    def update_progress(self, task_type: str, last_id: str = None, last_page: int = 0):
        """更新爬取进度"""
        conn = self.get_conn()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO crawl_progress (task_type, last_id, last_page, updated_at)
            VALUES (?, ?, ?, ?)
        ''', (task_type, last_id, last_page, datetime.now().isoformat()))
        conn.commit()
        conn.close()

    def get_posts_without_comments(self, limit: int = 0) -> list:
        """获取未爬取评论的微博，limit=0 表示不限制数量"""
        conn = self.get_conn()
        cursor = conn.cursor()
        if limit > 0:
            cursor.execute('''
                SELECT id FROM posts
                -- WHERE comments_count > 0  -- 注释原因：部分老微博PC端API返回comments_count=0但移动端有评论，放开此限制以便全量重爬
                WHERE id NOT IN (SELECT DISTINCT post_id FROM comments)
                ORDER BY created_at DESC
                LIMIT ?
            ''', (limit,))
        else:
            cursor.execute('''
                SELECT id FROM posts
                -- WHERE comments_count > 0
                WHERE id NOT IN (SELECT DISTINCT post_id FROM comments)
                ORDER BY created_at DESC
            ''')
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_stats(self) -> dict:
        """获取统计信息"""
        conn = self.get_conn()
        cursor = conn.cursor()

        stats = {}
        cursor.execute("SELECT COUNT(*) FROM posts")
        stats['total_posts'] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM comments")
        stats['total_comments'] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM images")
        stats['total_images'] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM videos")
        stats['total_videos'] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM likes")
        stats['total_likes'] = cursor.fetchone()[0]

        conn.close()
        return stats

    def save_comment_mobile(self, comment_data: dict, post_id: str) -> bool:
        """保存移动端API的评论，返回是否为新插入"""
        conn = self.get_conn()
        cursor = conn.cursor()

        comment_id = str(comment_data['id'])

        # 检查是否已存在
        cursor.execute("SELECT id FROM comments WHERE id = ?", (comment_id,))
        if cursor.fetchone():
            conn.close()
            return False

        # 保存评论
        cursor.execute('''
            INSERT INTO comments
            (id, post_id, user_uid, user_name, user_avatar, text, created_at,
             like_count, floor_number, raw_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            comment_id,
            post_id,
            str(comment_data.get('user', {}).get('id', '')),
            comment_data.get('user', {}).get('screen_name', ''),
            comment_data.get('user', {}).get('profile_image_url', ''),
            comment_data.get('text', ''),
            comment_data.get('created_at', ''),
            comment_data.get('like_counts', 0),
            comment_data.get('floor_number', 0),
            json.dumps(comment_data, ensure_ascii=False)
        ))

        # 如果有 reply_comment，说明当前评论是对它的回复（楼中楼）
        reply_comment = comment_data.get('reply_comment')
        if reply_comment:
            reply_id = str(reply_comment['id'])
            cursor.execute("SELECT id FROM replies WHERE id = ?", (comment_id,))
            if not cursor.fetchone():
                cursor.execute('''
                    INSERT INTO replies
                    (id, comment_id, post_id, user_uid, user_name, reply_to_uid,
                     reply_to_name, text, created_at, raw_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    comment_id,
                    reply_id,
                    post_id,
                    str(comment_data.get('user', {}).get('id', '')),
                    comment_data.get('user', {}).get('screen_name', ''),
                    str(reply_comment.get('user', {}).get('id', '')),
                    reply_comment.get('user', {}).get('screen_name', ''),
                    comment_data.get('text', ''),
                    comment_data.get('created_at', ''),
                    json.dumps(comment_data, ensure_ascii=False)
                ))

        conn.commit()
        conn.close()
        return True

    @staticmethod
    def _strip_html(html: str) -> str:
        """去除HTML标签"""
        import re
        clean = re.compile('<.*?>')
        return re.sub(clean, '', html)
