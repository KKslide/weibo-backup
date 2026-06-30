"""
媒体文件下载模块
"""
import os
import requests
import hashlib
from pathlib import Path
from typing import Optional
from datetime import datetime


class MediaDownloader:
    def __init__(self, media_dir: str):
        self.media_dir = Path(media_dir)
        self.image_dir = self.media_dir / "images"
        self.video_dir = self.media_dir / "videos"

        # 创建目录
        self.image_dir.mkdir(parents=True, exist_ok=True)
        self.video_dir.mkdir(parents=True, exist_ok=True)

        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15",
            "Referer": "https://m.weibo.cn/",
        })

    def _get_filename_from_url(self, url: str, prefix: str = "") -> str:
        """从URL生成文件名"""
        # 提取URL中的文件名
        url_hash = hashlib.md5(url.encode()).hexdigest()[:12]

        # 尝试从URL提取扩展名
        ext = ".jpg"
        if ".png" in url:
            ext = ".png"
        elif ".gif" in url:
            ext = ".gif"
        elif ".mp4" in url:
            ext = ".mp4"

        # 生成文件名
        if prefix:
            return f"{prefix}_{url_hash}{ext}"
        return f"{url_hash}{ext}"

    def _get_date_folder(self, created_at: str = None) -> str:
        """根据日期生成子文件夹"""
        if created_at:
            try:
                # 解析微博日期格式
                dt = datetime.strptime(created_at, "%a %b %d %H:%M:%S %z %Y")
                return dt.strftime("%Y/%m")
            except:
                pass
        return datetime.now().strftime("%Y/%m")

    def download_image(self, url: str, post_id: str, created_at: str = None) -> Optional[str]:
        """下载图片，返回本地路径"""
        if not url:
            return None

        # 处理URL
        if url.startswith("//"):
            url = "https:" + url

        try:
            # 生成保存路径
            date_folder = self._get_date_folder(created_at)
            save_dir = self.image_dir / date_folder
            save_dir.mkdir(parents=True, exist_ok=True)

            filename = self._get_filename_from_url(url, post_id)
            save_path = save_dir / filename

            # 如果已下载，跳过
            if save_path.exists():
                return str(save_path.relative_to(self.media_dir))

            # 下载
            resp = self.session.get(url, timeout=60)
            resp.raise_for_status()

            # 保存
            with open(save_path, "wb") as f:
                f.write(resp.content)

            print(f"  下载图片: {filename}")
            return str(save_path.relative_to(self.media_dir))

        except Exception as e:
            print(f"  下载图片失败 {url}: {e}")
            return None

    def download_video(self, url: str, post_id: str, created_at: str = None) -> Optional[str]:
        """下载视频，返回本地路径"""
        if not url:
            return None

        try:
            # 生成保存路径
            date_folder = self._get_date_folder(created_at)
            save_dir = self.video_dir / date_folder
            save_dir.mkdir(parents=True, exist_ok=True)

            filename = self._get_filename_from_url(url, post_id)
            save_path = save_dir / filename

            # 如果已下载，跳过
            if save_path.exists():
                return str(save_path.relative_to(self.media_dir))

            # 下载（流式下载大文件）
            resp = self.session.get(url, timeout=300, stream=True)
            resp.raise_for_status()

            # 保存
            with open(save_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)

            print(f"  下载视频: {filename}")
            return str(save_path.relative_to(self.media_dir))

        except Exception as e:
            print(f"  下载视频失败 {url}: {e}")
            return None

    def download_images_batch(self, urls: list, post_id: str, created_at: str = None) -> list:
        """批量下载图片"""
        results = []
        for i, url in enumerate(urls):
            if url:
                local_path = self.download_image(url, f"{post_id}_{i}", created_at)
                results.append({
                    "url": url,
                    "local_path": local_path
                })
        return results
