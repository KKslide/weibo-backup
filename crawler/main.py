"""
微博爬虫主程序 - 使用PC端API
"""
import os
import sys
import json
import time
import re
import requests
from pathlib import Path
from dotenv import load_dotenv

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from crawler.database import Database
from crawler.downloader import MediaDownloader


class WeiboAPC:
    """PC端微博API"""
    BASE_URL = "https://weibo.com/ajax"

    def __init__(self, cookie: str, delay: float = 2.0):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": "https://weibo.com/",
        })

        # 设置Cookie
        self.session.headers["Cookie"] = cookie

        # 提取XSRF-TOKEN
        xsrf_match = re.search(r'XSRF-TOKEN=([^;]+)', cookie)
        if xsrf_match:
            self.session.headers["X-XSRF-TOKEN"] = xsrf_match.group(1)

        self.delay = delay
        self._last_request_time = 0

    def _wait(self):
        """请求间隔"""
        elapsed = time.time() - self._last_request_time
        if elapsed < self.delay:
            import random
            sleep_time = self.delay - elapsed + random.uniform(0.3, 1.0)
            try:
                time.sleep(sleep_time)
            except KeyboardInterrupt:
                raise
        self._last_request_time = time.time()

    def _wait_light(self):
        """子回复请求的轻量间隔（0.3~1.0s 随机）"""
        import random
        sleep_time = random.uniform(0.3, 1.0)
        try:
            time.sleep(sleep_time)
        except KeyboardInterrupt:
            raise

    def _request(self, url: str, params: dict = None, max_retries: int = 2, light: bool = False) -> dict:
        """发送请求，支持重试"""
        for attempt in range(max_retries):
            if light:
                self._wait_light()
            else:
                self._wait()
            try:
                resp = self.session.get(url, params=params, timeout=15)
                resp.raise_for_status()
                data = resp.json()

                if data.get("ok") == -100:
                    print("Cookie已过期，请重新获取")
                    return None

                return data
            except requests.exceptions.HTTPError as e:
                # 400/403/404 等客户端错误不重试
                if e.response is not None and 400 <= e.response.status_code < 500:
                    return None
                print(f"HTTP错误: {e} (第 {attempt + 1}/{max_retries} 次)")
            except requests.exceptions.Timeout:
                print(f"请求超时 (第 {attempt + 1}/{max_retries} 次)")
            except requests.exceptions.ConnectionError:
                print(f"连接错误 (第 {attempt + 1}/{max_retries} 次)")
            except Exception as e:
                print(f"请求失败: {e} (第 {attempt + 1}/{max_retries} 次)")

            if attempt < max_retries - 1:
                time.sleep(2)

        return None

    def get_user_info(self, uid: str) -> dict:
        """获取用户信息"""
        data = self._request(f"{self.BASE_URL}/profile/info", {"uid": uid})
        if data and data.get("ok") == 1:
            return data.get("data", {}).get("user", {})
        return None

    def get_user_posts(self, uid: str, page: int = 1) -> list:
        """获取用户微博列表"""
        params = {
            "uid": uid,
            "page": page,
            "feature": 0
        }
        data = self._request(f"{self.BASE_URL}/statuses/mymblog", params)
        if data and data.get("ok") == 1:
            return data.get("data", {}).get("list", [])
        return []

    def get_comments(self, mid: str, page: int = 1):
        """获取评论，失败返回 None，无评论返回 []"""
        params = {
            "id": mid,
            "page": page,
            "is_reload": 1,
            "is_show_bulletin": 2,
            "count": 20
        }
        data = self._request(f"{self.BASE_URL}/statuses/buildComments", params)
        if data is None:
            return None  # 请求失败
        if data.get("ok") == 1:
            return data.get("data", [])
        return []  # 成功但无数据

    def get_comment_replies(self, mid: str, cid: str, max_id: int = 0, light: bool = False) -> list:
        """获取评论回复，light=True 使用轻量延迟"""
        params = {
            "id": cid,              # 用评论ID，不是帖子ID
            "is_reload": "1",
            "is_show_bulletin": "2",
            "is_mix": "1",
            "fetch_level": "1",
            "max_id": max_id,
            "count": 20,
        }
        data = self._request(f"{self.BASE_URL}/statuses/buildComments", params, light=light)
        if data and data.get("ok") == 1:
            return data.get("data", [])
        return []

    def get_long_text(self, mblogid: str) -> str:
        """获取超长博文的完整内容（mblogid 是 raw_json 里的短字符串，如 'O6GMNnOah'）"""
        data = self._request(f"{self.BASE_URL}/statuses/longtext", {"id": mblogid})
        if data and data.get("ok") == 1:
            return data.get("data", {}).get("longTextContent", "")
        return ""

    def get_likes(self, mid: str, page: int = 1) -> list:
        """获取点赞用户"""
        params = {
            "id": mid,
            "page": page
        }
        data = self._request(f"{self.BASE_URL}/like/list", params)
        if data and data.get("ok") == 1:
            return data.get("data", {}).get("users", [])
        return []


class WeiboAPMobile:
    """移动端微博API — 用于获取PC端API无法获取的历史评论"""
    BASE_URL = "https://api.weibo.cn"
    # 固定的客户端参数
    QUERY_PARAMS = {
        "c": "iphone",
        "s": "ab90923c",
        "from": "10G5093010",
    }
    HEADERS = {
        "Host": "api.weibo.cn",
        "Content-Type": "application/x-www-form-urlencoded; charset=utf-8",
        "User-Agent": "Weibo/99339 (iPhone; iOS 26.5; Scale/3.00)",
        "Accept": "*/*",
    }

    def __init__(self, gsid: str, delay: float = 2.0):
        self.gsid = gsid
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)
        self.delay = delay
        self._last_request_time = 0

    def _wait(self):
        elapsed = time.time() - self._last_request_time
        if elapsed < self.delay:
            import random
            sleep_time = self.delay - elapsed + random.uniform(0.3, 1.0)
            try:
                time.sleep(sleep_time)
            except KeyboardInterrupt:
                raise
        self._last_request_time = time.time()

    def _request(self, path: str, body: dict, max_retries: int = 2) -> dict:
        """POST 请求，支持重试"""
        params = dict(self.QUERY_PARAMS)
        params["gsid"] = self.gsid

        for attempt in range(max_retries):
            self._wait()
            try:
                resp = self.session.post(
                    f"{self.BASE_URL}{path}",
                    params=params,
                    data=body,
                    timeout=15,
                )
                resp.raise_for_status()
                data = resp.json()
                errno = data.get("errno", 0)
                if errno:
                    print(f"  移动端API错误: errno={errno}, msg={data.get('errmsg', '')}")
                    return None
                return data
            except requests.exceptions.Timeout:
                print(f"  移动端请求超时 (第 {attempt + 1}/{max_retries} 次)")
            except requests.exceptions.ConnectionError:
                print(f"  移动端连接错误 (第 {attempt + 1}/{max_retries} 次)")
            except Exception as e:
                print(f"  移动端请求失败: {e} (第 {attempt + 1}/{max_retries} 次)")

            if attempt < max_retries - 1:
                time.sleep(2)

        return None

    def get_comments(self, post_id: str, page: int = 1, count: int = 20) -> tuple:
        """获取评论，返回 (comments_list, total_number) 或 (None, 0)"""
        body = {
            "flowId": "comment",
            "id": str(post_id),
            "is_mix": "1",
            "is_reload": "1",
            "is_show_bulletin": "0",
            "trim_level": "1",
            "fetch_level": "0",
            "count": str(count),
            "commonPage": str(page),
        }
        data = self._request("/2/statuses/container_detail_comment", body)
        if data is None:
            return None, 0

        items = data.get("items", [])
        total = data.get("loadedInfo", {}).get("total_number", 0)

        # 提取评论数据
        comments = []
        for item in items:
            if item.get("type") == "comment" and item.get("data"):
                comments.append(item["data"])

        return comments, total

    def get_likes(self, post_id: str, page: int = 1, count: int = 50) -> tuple:
        """获取点赞用户，返回 (likes_list, total_number) 或 (None, 0)"""
        body = {
            "flowId": "like",
            "id": str(post_id),
            "count": str(count),
            "commonPage": str(page),
        }
        data = self._request("/2/statuses/container_detail_like", body)
        if data is None:
            return None, 0

        items = data.get("items", [])
        total = data.get("loadedInfo", {}).get("total_number", 0)

        likes = []
        for item in items:
            if item.get("type") == "like" and item.get("data"):
                likes.append(item["data"])

        return likes, total


class WeiboCrawlerPC:
    def __init__(self):
        load_dotenv()

        self.cookie = os.getenv("WEIBO_COOKIE", "")
        self.uid = os.getenv("WEIBO_UID", "")
        self.delay = float(os.getenv("REQUEST_DELAY", "2"))
        self.db_path = os.getenv("DB_PATH", "./data/weibo_backup.db")
        self.media_dir = os.getenv("MEDIA_DIR", "./data/media")

        if not self.cookie:
            print("错误: 请在 .env 文件中配置 WEIBO_COOKIE")
            sys.exit(1)

        if not self.uid:
            print("错误: 请在 .env 文件中配置 WEIBO_UID")
            sys.exit(1)

        self.gsid = os.getenv("WEIBO_GSID", "")

        self.api = WeiboAPC(self.cookie, self.delay)
        self.api_mobile = WeiboAPMobile(self.gsid, self.delay) if self.gsid else None
        self.db = Database(self.db_path)
        self.downloader = MediaDownloader(self.media_dir)

        print(f"初始化完成:")
        print(f"  用户UID: {self.uid}")
        print(f"  数据库: {self.db_path}")
        print(f"  媒体目录: {self.media_dir}")
        if self.api_mobile:
            print(f"  移动端API: 已启用")
        else:
            print(f"  移动端API: 未配置 (无法获取历史评论)")

    def crawl_user_info(self):
        """爬取用户信息"""
        print("\n=== 爬取用户信息 ===")
        user_info = self.api.get_user_info(self.uid)

        if user_info:
            self.db.save_user(user_info)
            print(f"用户: {user_info.get('screen_name', '未知')}")
            print(f"粉丝数: {user_info.get('followers_count', 0)}")
            print(f"关注数: {user_info.get('friends_count', 0)}")
            print(f"微博数: {user_info.get('statuses_count', 0)}")
            return user_info
        else:
            print("获取用户信息失败")
            return None

    def crawl_posts(self, max_pages: int = 0):
        """爬取所有微博"""
        print("\n=== 爬取微博列表 ===")

        progress = self.db.get_progress("posts")
        start_page = progress.get("last_page", 1) if progress else 1

        page = start_page
        total_new = 0
        empty_count = 0

        while True:
            if max_pages > 0 and page > max_pages:
                print(f"达到最大页数限制: {max_pages}")
                break

            print(f"\n爬取第 {page} 页...")
            posts = self.api.get_user_posts(self.uid, page)

            if not posts:
                empty_count += 1
                if empty_count >= 3:
                    print("连续3页无数据，停止爬取")
                    break
                page += 1
                continue

            empty_count = 0
            page_new = 0

            for post in posts:
                post_id = str(post.get("id", ""))
                if not post_id:
                    continue

                # 处理图片
                pic_urls = []
                pics = post.get("pic_ids", [])
                pic_infos = post.get("pic_infos", {})
                for pic_id in pics:
                    pic_info = pic_infos.get(pic_id, {})
                    large = pic_info.get("large", {})
                    url = large.get("url", "")
                    if url:
                        pic_urls.append(url)

                post["pic_urls"] = pic_urls

                # 处理视频
                page_info = post.get("page_info", {})
                if page_info and page_info.get("object_type") == "video":
                    media_info = page_info.get("media_info", {})
                    video_url = (
                        media_info.get("stream_url_hd") or
                        media_info.get("stream_url") or
                        media_info.get("mp4_720p_mp4") or
                        media_info.get("mp4_hd_url") or
                        media_info.get("mp4_sd_url")
                    )
                    if video_url:
                        # page_pic 可能是 dict、str 或 None
                        page_pic = page_info.get("page_pic")
                        if isinstance(page_pic, dict):
                            cover_url = page_pic.get("url", "")
                        elif isinstance(page_pic, str):
                            cover_url = page_pic
                        else:
                            cover_url = ""

                        post["video_info"] = {
                            "url": video_url,
                            "cover_url": cover_url,
                            "duration": media_info.get("duration", 0)
                        }

                # 提取话题和@用户
                text = post.get("text", "")
                topics = re.findall(r'#([^#]+)#', text)
                at_users = re.findall(r'@(\S+?)[\s<]', text)
                post["topics"] = topics
                post["at_users"] = at_users

                # 保存微博
                is_new = self.db.save_post(post)
                if is_new:
                    page_new += 1
                    total_new += 1

                    # 补全超长文本（包含"展开全文"或isLongText标记的博文）
                    if "展开" in text or post.get("isLongText"):
                        mblogid = post.get("mblogid", "")
                        if mblogid:
                            long_text = self.api.get_long_text(mblogid)
                            if long_text:
                                self.db.update_post_text(post_id, long_text)
                                print(f"  补全超长文本: {len(long_text)} 字")

                    # 下载图片
                    if pic_urls:
                        print(f"  下载图片: {len(pic_urls)} 张")
                        images_data = []
                        for i, url in enumerate(pic_urls):
                            local_path = self.downloader.download_image(url, f"{post_id}_{i}", post.get("created_at"))
                            images_data.append({
                                "url": url,
                                "local_path": local_path,
                                "width": 0,
                                "height": 0
                            })
                        self.db.save_images(post_id, images_data)

                    # 下载视频
                    if post.get("video_info"):
                        print(f"  发现视频，开始下载...")
                        video_info = post["video_info"]
                        local_path = self.downloader.download_video(
                            video_info["url"], post_id, post.get("created_at")
                        )
                        video_info["local_path"] = local_path
                        self.db.save_video(post_id, video_info)

            print(f"第 {page} 页: 新增 {page_new} 条微博")

            self.db.update_progress("posts", last_page=page)

            page += 1
            time.sleep(0.5)

        print(f"\n微博爬取完成，共新增 {total_new} 条")
        return total_new

    def _fetch_deeper_replies(self, post_id: str, root_comment_id: str, parent_id: str, depth: int = 0):
        """递归爬取更深层的楼中楼回复，depth 限制递归深度防止无限循环"""
        if depth >= 4:
            return 0

        total = 0
        max_id = 0
        api_calls = 0

        while True:
            api_calls += 1
            replies = self.api.get_comment_replies(post_id, parent_id, max_id, light=True)
            if not replies:
                break

            for reply in replies:
                reply_id = str(reply.get("id", ""))
                if not reply_id:
                    continue
                if self.db.save_reply(reply, root_comment_id, post_id):
                    total += 1
                time.sleep(0.2)
                # 递归爬取更深层
                total += self._fetch_deeper_replies(post_id, root_comment_id, reply_id, depth + 1)

            if len(replies) < 20:
                break
            max_id = int(replies[-1].get("id", 0))

        if total > 0:
            print(f"  深挖回复: {total} 条 ({api_calls} 次API)" )

        return total

    def crawl_comments(self, limit: int = 0):
        """爬取评论（PC端失败时自动切换移动端API）"""
        print("\n=== 爬取评论 ===")

        try:
            self._do_crawl_comments(limit)
        except KeyboardInterrupt:
            print("\n\n用户中断，爬取已停止")

    def _do_crawl_comments(self, limit: int):
        posts = self.db.get_posts_without_comments(limit)
        print(f"待爬取评论的微博: {len(posts)} 条")

        total_posts = len(posts)
        total_comments = 0
        total_mobile = 0
        total_skipped = 0

        for idx, post_info in enumerate(posts, 1):
            post_id = post_info["id"]
            print(f"\n[{idx}/{total_posts}] 爬取微博 {post_id} 的评论...")

            page = 1
            max_pages = 20
            use_mobile = False
            mobile_failed = False
            post_count = 0  # 本条微博爬到的评论数
            post_start = time.time()

            while page <= max_pages:
                if not use_mobile:
                    # === PC 端 API ===
                    comments = self.api.get_comments(post_id, page)

                    if comments is None:
                        # 第一页就失败且配置了移动端API → 降级
                        if page == 1 and self.api_mobile:
                            print(f"  PC端API请求失败，切换到移动端API...")
                            use_mobile = True
                            page = 1
                            continue
                        # 后续页失败或第一页无移动端降级 → 直接停止
                        break

                    if not comments:
                        # PC端返回空，可能是老旧微博 → 尝试移动端
                        if self.api_mobile and page == 1:
                            print(f"  PC端无评论数据，尝试移动端API...")
                            use_mobile = True
                            page = 1
                            continue
                        break

                    # PC端正常保存
                    page_new = 0  # 本页新插入数
                    for comment in comments:
                        comment_id = str(comment.get("id", ""))
                        if not comment_id:
                            continue
                        if self.db.save_comment(comment, post_id):
                            total_comments += 1
                            post_count += 1
                            page_new += 1

                        sub_comments = comment.get("comments", [])
                        for reply in sub_comments:
                            reply_id = str(reply.get("id", ""))
                            if reply_id:
                                if self.db.save_reply(reply, comment_id, post_id):
                                    post_count += 1
                                    page_new += 1
                                # 递归爬取更深层的楼中楼回复
                                deeper = self._fetch_deeper_replies(post_id, comment_id, reply_id)
                                post_count += deeper
                                page_new += deeper

                        # 挖取顶层评论的回复（comment.comments[] 之外的可能还有）
                        deeper = self._fetch_deeper_replies(post_id, comment_id, comment_id)
                        post_count += deeper
                        page_new += deeper

                    # 整页全是重复数据 → 停止翻页
                    if page_new == 0 and page > 1:
                        break

                    page += 1
                    time.sleep(0.3)

                else:
                    # === 移动端 API ===
                    mobile_comments, total = self.api_mobile.get_comments(post_id, page)

                    if mobile_comments is None:
                        mobile_failed = True
                        break

                    if not mobile_comments:
                        break

                    for mc in mobile_comments:
                        if str(mc.get("id", "")):
                            if self.db.save_comment_mobile(mc, post_id):
                                total_mobile += 1
                                post_count += 1

                    # 移动端分页：是否还有更多页
                    fetched = page * 20
                    if fetched >= total:
                        break
                    page += 1
                    time.sleep(0.5)

            # 打印本条微博的爬取结果
            if mobile_failed:
                print(f"  结果: 移动端API请求失败，已跳过 (耗时 {time.time() - post_start:.1f}s)")
                total_skipped += 1
            elif use_mobile and post_count == 0:
                print(f"  结果: 移动端也无评论数据 (耗时 {time.time() - post_start:.1f}s)")
            else:
                api_label = "移动端" if use_mobile else "PC端"
                print(f"  结果: {api_label}获取 {post_count} 条评论 (耗时 {time.time() - post_start:.1f}s)")

        total = total_comments + total_mobile
        print(f"\n评论爬取完成，共 {total} 条 (PC端: {total_comments}, 移动端: {total_mobile}, 跳过: {total_skipped})")
        return total

    def crawl_texts(self):
        """补全所有超长博文的文本"""
        print("\n=== 补全超长博文文本 ===")

        conn = self.db.get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT id, json_extract(raw_json, '$.mblogid') as mblogid FROM posts WHERE json_extract(raw_json, '$.isLongText') = 1")
        rows = cursor.fetchall()
        conn.close()

        print(f"待补全的博文: {len(rows)} 条")

        total_fixed = 0
        for idx, row in enumerate(rows, 1):
            post_id, mblogid = row["id"], row["mblogid"]
            if not mblogid:
                continue

            long_text = self.api.get_long_text(mblogid)
            if long_text:
                self.db.update_post_text(post_id, long_text)
                total_fixed += 1
                text_preview = long_text[:60].replace("\n", " ")
                print(f"  [{idx}/{len(rows)}] 微博 {post_id}: {len(long_text)} 字 — {text_preview}...")
            else:
                print(f"  [{idx}/{len(rows)}] 微博 {post_id}: API无返回")

            time.sleep(0.5)

        print(f"\n补全完成，共 {total_fixed} 条")
        return total_fixed

    def crawl_likes(self):
        """爬取所有微博的点赞用户（通过移动端API）"""
        if not self.api_mobile:
            print("\n错误: 未配置 WEIBO_GSID，无法使用移动端API爬取点赞")
            return 0

        print("\n=== 爬取点赞用户 ===")

        posts = []
        conn = self.db.get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM posts WHERE attitudes_count > 0 ORDER BY created_at DESC")
        posts = [row[0] for row in cursor.fetchall()]
        conn.close()

        print(f"待爬取点赞的微博: {len(posts)} 条")

        total_likes = 0

        for idx, post_id in enumerate(posts, 1):
            page = 1
            post_likes = 0
            post_start = time.time()

            while True:
                likes, total = self.api_mobile.get_likes(post_id, page)
                if likes is None:
                    break
                if not likes:
                    break

                self.db.save_likes(post_id, likes)
                post_likes += len(likes)

                fetched = page * 50
                if fetched >= total:
                    break
                page += 1
                time.sleep(0.5)

            if post_likes:
                total_likes += post_likes

            if idx == 1 or post_likes > 0:
                print(f"  [{idx}/{len(posts)}] 微博 {post_id}: {post_likes} 赞 (耗时 {time.time() - post_start:.1f}s)")

        print(f"\n点赞爬取完成，共 {total_likes} 条点赞")
        return total_likes

    def run(self):
        """运行完整爬取流程"""
        print("=" * 50)
        print("微博数据爬虫")
        print("=" * 50)

        start_time = time.time()

        # 1. 爬取用户信息
        self.crawl_user_info()

        # 2. 爬取所有微博
        self.crawl_posts()

        # 3. 爬取评论
        self.crawl_comments()

        # 4. 爬取点赞用户
        if self.api_mobile:
            self.crawl_likes()

        # 统计
        elapsed = time.time() - start_time
        stats = self.db.get_stats()

        print("\n" + "=" * 50)
        print("爬取完成!")
        print(f"耗时: {elapsed:.1f} 秒")
        print(f"微博数: {stats['total_posts']}")
        print(f"评论数: {stats['total_comments']}")
        print(f"图片数: {stats['total_images']}")
        print(f"视频数: {stats['total_videos']}")
        print(f"点赞数: {stats['total_likes']}")
        print("=" * 50)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="微博数据爬虫")
    parser.add_argument("--comments-only", action="store_true", help="只爬取评论")
    parser.add_argument("--likes-only", action="store_true", help="只爬取点赞用户（需配置WEIBO_GSID）")
    parser.add_argument("--texts-only", action="store_true", help="补全超长博文文本")
    parser.add_argument("--pages", type=int, default=0, help="最大爬取页数（0表示全部）")
    args = parser.parse_args()

    crawler = WeiboCrawlerPC()

    if args.comments_only:
        crawler.crawl_comments()
    elif args.likes_only:
        crawler.crawl_likes()
    elif args.texts_only:
        crawler.crawl_texts()
    else:
        crawler.run()


if __name__ == "__main__":
    main()
