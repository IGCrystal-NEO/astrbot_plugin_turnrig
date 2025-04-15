import os
import uuid
import requests  # 添加requests库
import traceback
import asyncio
from astrbot.api import logger

class DownloadHelper:
    """媒体下载助手类"""
    
    def __init__(self, image_dir):
        self.image_dir = image_dir
        os.makedirs(self.image_dir, exist_ok=True)
        logger.info(f"媒体临时目录: {self.image_dir}")
    
    async def download_file(self, url: str, file_type: str = "jpg") -> str:
        """下载文件到本地临时目录，支持各种媒体类型
        
        Args:
            url: 文件URL
            file_type: 文件扩展名，默认为jpg
            
        Returns:
            str: 成功时返回本地文件路径，失败时返回空字符串
        """
        try:
            # 生成唯一文件名
            filename = f"{uuid.uuid4()}.{file_type}"
            filepath = os.path.join(self.image_dir, filename)
            
            # 检查是否为 QQ 图片服务器链接
            is_qq_multimedia = "multimedia.nt.qq.com.cn" in url or "gchat.qpic.cn" in url
            
            try:
                # 使用requests直接下载，更加可靠
                response = await asyncio.to_thread(
                    requests.get, 
                    url, 
                    timeout=30,
                    headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36'},
                    verify=False  # 对于QQ多媒体链接，禁用SSL验证
                )
                
                if response.status_code == 200:
                    with open(filepath, "wb") as f:
                        f.write(response.content)
                    logger.debug(f"成功下载文件到: {filepath}")
                    return filepath
                else:
                    logger.error(f"下载文件失败，状态码: {response.status_code}")
            except Exception as e:
                logger.error(f"下载文件出错: {e}")
                logger.error(traceback.format_exc())
            
            # 如果下载失败但是QQ多媒体链接，返回原始URL
            if is_qq_multimedia:
                logger.info(f"无法下载QQ图片，尝试使用原始URL: {url}")
                return url
                
            return ""
        except Exception as e:
            logger.error(f"下载文件处理过程出错: {e}")
            logger.error(traceback.format_exc())
            return ""
    
    async def download_image(self, image_url: str) -> str:
        """下载图片到本地临时目录
        
        Args:
            image_url: 图片URL
            
        Returns:
            str: 成功时返回本地文件路径，失败时返回空字符串
        """
        # 为空URL直接返回
        if not image_url:
            logger.warning("下载图片失败: URL为空")
            return ""
            
        # 处理特殊URL格式
        if image_url.startswith("file:///"):
            # 已经是本地文件路径
            local_path = image_url[8:]
            logger.debug(f"图片已经是本地文件: {local_path}")
            if os.path.exists(local_path):
                return local_path
            else:
                logger.warning(f"本地图片不存在: {local_path}")
                return ""
        
        # 检查缓存以避免重复下载
        cache_key = f"img_cache_{hash(image_url)}"
        if hasattr(self, 'plugin') and self.plugin and hasattr(self.plugin, 'config'):
            cached_path = self.plugin.config.get(cache_key, "")
            if cached_path and os.path.exists(cached_path):
                logger.debug(f"使用缓存的图片: {cached_path}")
                return cached_path
        
        # 推断文件类型
        file_type = "jpg"
        if "." in image_url.split("/")[-1]:
            ext = image_url.split(".")[-1].lower()
            if ext in ["jpg", "jpeg", "png", "gif", "webp", "bmp"]:
                file_type = ext
        
        # 执行下载，最多重试3次
        for attempt in range(3):
            try:
                result = await self.download_file(image_url, file_type)
                if result:
                    # 缓存结果
                    if hasattr(self, 'plugin') and self.plugin and hasattr(self.plugin, 'config'):
                        self.plugin.config[cache_key] = result
                    return result
                
                logger.warning(f"下载图片失败，尝试 {attempt+1}/3")
                await asyncio.sleep(1)  # 重试前等待
            except Exception as e:
                logger.error(f"下载图片异常 (尝试 {attempt+1}/3): {e}")
                await asyncio.sleep(1)  # 重试前等待
        
        logger.error(f"多次尝试后下载图片失败: {image_url}")
        return ""
    
    async def download_audio(self, audio_url: str) -> str:
        """下载音频到本地临时目录
        
        Args:
            audio_url: 音频URL
            
        Returns:
            str: 成功时返回本地文件路径，失败时返回空字符串
        """
        return await self.download_file(audio_url, "mp3")
    
    async def download_video(self, video_url: str) -> str:
        """下载视频到本地临时目录
        
        Args:
            video_url: 视频URL
            
        Returns:
            str: 成功时返回本地文件路径，失败时返回空字符串
        """
        return await self.download_file(video_url, "mp4")
