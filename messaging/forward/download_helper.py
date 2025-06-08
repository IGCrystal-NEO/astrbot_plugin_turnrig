import asyncio
import os
import traceback
import uuid

import requests  # 添加requests库喵～ 📚
from astrbot.api import logger


class DownloadHelper:
    """
    媒体下载助手喵～ 📥
    专门帮忙下载各种媒体文件的小可爱！ ฅ(^•ω•^ฅ
    
    这个小助手会帮你：
    - 🖼️ 下载图片文件
    - 🎵 下载音频文件  
    - 🎬 下载视频文件
    - 💾 管理本地缓存
    - 🔄 智能重试下载
    
    Note:
        支持多种下载方式，确保媒体文件能正确下载喵！ ✨
    """

    def __init__(self, image_dir=None):
        """
        初始化下载助手喵！(ฅ^•ω•^ฅ)
        
        Args:
            image_dir: 图片存储目录，如果不提供会使用默认路径喵～
        """
        # 如果未提供路径，使用标准插件数据目录喵～ 📁
        if not image_dir:
            self.image_dir = os.path.join(
                "data", "plugins_data", "astrbot_plugin_turnrig", "temp", "images"
            )
        else:
            self.image_dir = image_dir

        # 确保目录存在喵～ 🏗️
        os.makedirs(self.image_dir, exist_ok=True)
        logger.info(f"媒体临时目录喵: {self.image_dir} 📂")

    async def download_file(self, url: str, file_type: str = "jpg") -> str:
        """
        下载文件到本地临时目录喵～ 📥
        支持各种媒体类型的通用下载方法！
        
        Args:
            url: 文件URL喵
            file_type: 文件类型扩展名喵
            
        Returns:
            成功时返回本地文件路径，失败时返回空字符串喵
            
        Note:
            会尝试多种下载方式，确保文件能正确下载喵！ 🔄
        """
        try:
            # 生成唯一文件名喵～ 🆔
            filename = f"{uuid.uuid4()}.{file_type}"
            filepath = os.path.join(self.image_dir, filename)

            # 检查是否为 QQ 图片服务器链接喵～ 🔍
            is_qq_multimedia = (
                "multimedia.nt.qq.com.cn" in url or "gchat.qpic.cn" in url
            )

            # 检查是否为GIF - 新增逻辑喵～ 🎞️
            is_gif = file_type.lower() == "gif" or url.lower().endswith(".gif")
            if is_gif:
                logger.info(f"正在下载GIF图片喵: {url} 🎞️")

            # 方法1: 使用requests直接下载喵～ 📡
            try:
                response = await asyncio.to_thread(
                    requests.get,
                    url,
                    timeout=30,
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36"
                    },
                    verify=False,
                )

                if response.status_code == 200:
                    # 写入文件喵～ 💾
                    with open(filepath, "wb") as f:
                        f.write(response.content)

                    # 验证GIF文件有效性喵～ ✅
                    if is_gif:
                        # 检查文件头喵～ 🔍
                        with open(filepath, "rb") as f:
                            header = f.read(6)
                        if header.startswith(b"GIF"):
                            logger.info(f"成功下载GIF动图喵: {filepath} ✅")
                        else:
                            logger.warning(
                                f"下载的GIF文件头无效，可能不是真正的GIF喵: {filepath} ⚠️"
                            )

                    return filepath
                else:
                    logger.warning(
                        f"请求下载失败喵，状态码: {response.status_code}，尝试使用curl 🔄"
                    )
            except Exception as e:
                logger.warning(f"请求下载出错喵: {e}，尝试使用curl 🔄")

            # 方法2: 使用curl下载，对GIF更为友好喵～ 🌐
            try:
                # 构建curl命令喵～ 🛠️
                cmd = [
                    "curl",
                    "-s",  # 静默模式
                    "-L",  # 跟随重定向
                    "-o",
                    filepath,  # 输出文件
                    "-H",
                    "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36",
                    url,
                ]

                # 执行curl命令喵～ ⚡
                process = await asyncio.create_subprocess_exec(
                    *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
                )

                stdout, stderr = await process.communicate()

                # 检查下载结果喵～ 🔍
                if (
                    process.returncode == 0
                    and os.path.exists(filepath)
                    and os.path.getsize(filepath) > 0
                ):
                    if is_gif:
                        logger.info(f"使用curl成功下载GIF喵: {filepath} ✅")
                    return filepath
                else:
                    stderr_text = stderr.decode() if stderr else "未知错误"
                    logger.warning(f"curl下载失败喵: {stderr_text} 😿")
            except Exception as e:
                logger.warning(f"curl下载异常喵: {e} 😿")

            # 如果是GIF，更倾向于返回原始URL喵～ 🔗
            if is_gif and is_qq_multimedia:
                logger.info(f"GIF下载失败，直接使用原始URL喵: {url} 📎")
                return url

            return ""
        except Exception as e:
            # 下载过程中出错了喵！ 😿
            logger.error(f"下载文件处理过程出错喵: {e}")
            logger.error(traceback.format_exc())
            return ""

    async def download_image(self, image_url: str) -> str:
        """
        下载图片到本地临时目录喵～ 🖼️
        专门处理图片文件的下载！
        
        Args:
            image_url: 图片URL喵

        Returns:
            成功时返回本地文件路径，失败时返回空字符串喵
            
        Note:
            支持缓存机制，避免重复下载相同图片喵！ 💾
        """
        # 为空URL直接返回喵～ 🚫
        if not image_url:
            logger.warning("下载图片失败喵: URL为空 📭")
            return ""

        # 处理特殊URL格式喵～ 🔍
        if image_url.startswith("file:///"):
            # 已经是本地文件路径喵～ 💾
            local_path = image_url[8:]
            logger.debug(f"图片已经是本地文件喵: {local_path} 📁")
            if os.path.exists(local_path):
                return local_path
            else:
                logger.warning(f"本地图片不存在喵: {local_path} 😿")
                return ""

        # 检查缓存以避免重复下载喵～ 🔍
        cache_key = f"img_cache_{hash(image_url)}"
        if hasattr(self, "plugin") and self.plugin and hasattr(self.plugin, "config"):
            cached_path = self.plugin.config.get(cache_key, "")
            if cached_path and os.path.exists(cached_path):
                logger.debug(f"使用缓存的图片喵: {cached_path} 💾")
                return cached_path

        # 推断文件类型喵～ 🔍
        file_type = "jpg"
        if "." in image_url.split("/")[-1]:
            ext = image_url.split(".")[-1].lower()
            if ext in ["jpg", "jpeg", "png", "gif", "webp", "bmp"]:
                file_type = ext

        # 执行下载，最多重试3次喵～ 🔄
        for attempt in range(3):
            try:
                result = await self.download_file(image_url, file_type)
                if result:
                    # 缓存结果喵～ 💾
                    if (
                        hasattr(self, "plugin")
                        and self.plugin
                        and hasattr(self.plugin, "config")
                    ):
                        self.plugin.config[cache_key] = result
                    return result

                logger.warning(f"下载图片失败，尝试 {attempt + 1}/3 喵～ 🔄")
                await asyncio.sleep(1)  # 重试前等待喵～ 😴
            except Exception as e:
                logger.error(f"下载图片异常 (尝试 {attempt + 1}/3) 喵: {e} 😿")
                await asyncio.sleep(1)  # 重试前等待喵～ 😴

        logger.error(f"多次尝试后下载图片失败喵: {image_url} 😿")
        return ""

    async def download_audio(self, audio_url: str) -> str:
        """
        下载音频到本地临时目录喵～ 🎵
        专门处理音频文件的下载！
        
        Args:
            audio_url: 音频URL喵

        Returns:
            成功时返回本地文件路径，失败时返回空字符串喵
            
        Note:
            默认保存为mp3格式，兼容性最好喵！ 🎶
        """
        return await self.download_file(audio_url, "mp3")

    async def download_video(self, video_url: str) -> str:
        """
        下载视频到本地临时目录喵～ 🎬
        专门处理视频文件的下载！
        
        Args:
            video_url: 视频URL喵

        Returns:
            成功时返回本地文件路径，失败时返回空字符串喵
            
        Note:
            默认保存为mp4格式，兼容性最好喵！ 📹
        """
        return await self.download_file(video_url, "mp4")
