import os
import uuid
import aiohttp
import ssl
import certifi
import traceback
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
            
            # 使用SSL证书验证的下载方法
            try:
                ssl_context = ssl.create_default_context(cafile=certifi.where())
                connector = aiohttp.TCPConnector(ssl=ssl_context)
                
                async with aiohttp.ClientSession(connector=connector) as session:
                    async with session.get(url, timeout=30) as response:
                        if response.status == 200:
                            with open(filepath, "wb") as f:
                                f.write(await response.read())
                            logger.debug(f"成功下载文件到: {filepath}")
                            return filepath
                        else:
                            logger.error(f"下载文件失败，状态码: {response.status}")
            except Exception as e:
                logger.error(f"下载文件出错(尝试备用方法): {e}")
                
                # 备用下载方法：关闭SSL验证
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(url, ssl=False, timeout=30) as response:
                            if response.status == 200:
                                with open(filepath, "wb") as f:
                                    f.write(await response.read())
                                logger.debug(f"通过备用方法成功下载文件: {filepath}")
                                return filepath
                            else:
                                logger.error(f"备用下载方法失败，状态码: {response.status}")
                except Exception as e2:
                    logger.error(f"备用下载方法也失败: {e2}")
            
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
        return await self.download_file(image_url, "jpg")
    
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
