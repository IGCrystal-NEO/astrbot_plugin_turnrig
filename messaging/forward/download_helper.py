import os
import uuid
import requests  # 添加requests库
import traceback
import asyncio
from astrbot.api import logger

class DownloadHelper:
    """媒体下载助手类"""
    
    def __init__(self, image_dir=None):
        # 如果未提供路径，使用标准插件数据目录
        if not image_dir:
            self.image_dir = os.path.join("data", "plugins_data", "astrbot_plugin_turnrig", "temp", "images")
        else:
            self.image_dir = image_dir
        
        os.makedirs(self.image_dir, exist_ok=True)
        logger.info(f"媒体临时目录: {self.image_dir}")
    
    async def download_file(self, url: str, file_type: str = "jpg") -> str:
        """下载文件到本地临时目录，支持各种媒体类型"""
        try:
            # 生成唯一文件名
            filename = f"{uuid.uuid4()}.{file_type}"
            filepath = os.path.join(self.image_dir, filename)
            
            # 检查是否为 QQ 图片服务器链接
            is_qq_multimedia = "multimedia.nt.qq.com.cn" in url or "gchat.qpic.cn" in url
            
            # 检查是否为GIF - 新增逻辑
            is_gif = file_type.lower() == "gif" or url.lower().endswith('.gif')
            if is_gif:
                logger.info(f"正在下载GIF图片: {url}")
            
            # 方法1: 使用requests直接下载
            try:
                response = await asyncio.to_thread(
                    requests.get, 
                    url, 
                    timeout=30,
                    headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36'},
                    verify=False
                )
                
                if response.status_code == 200:
                    with open(filepath, "wb") as f:
                        f.write(response.content)
                    
                    # 验证GIF文件有效性
                    if is_gif:
                        # 检查文件头
                        with open(filepath, "rb") as f:
                            header = f.read(6)
                        if header.startswith(b'GIF'):
                            logger.info(f"成功下载GIF动图: {filepath}")
                        else:
                            logger.warning(f"下载的GIF文件头无效，可能不是真正的GIF: {filepath}")
                    
                    return filepath
                else:
                    logger.warning(f"请求下载失败，状态码: {response.status_code}，尝试使用curl")
            except Exception as e:
                logger.warning(f"请求下载出错: {e}，尝试使用curl")
            
            # 方法2: 使用curl下载，对GIF更为友好
            try:
                import subprocess
                
                # 构建curl命令
                cmd = [
                    "curl", 
                    "-s",                   # 静默模式
                    "-L",                   # 跟随重定向
                    "-o", filepath,         # 输出文件
                    "-H", "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36",
                    url
                ]
                
                # 执行curl命令
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                stdout, stderr = await process.communicate()
                
                # 检查下载结果
                if process.returncode == 0 and os.path.exists(filepath) and os.path.getsize(filepath) > 0:
                    if is_gif:
                        logger.info(f"使用curl成功下载GIF: {filepath}")
                    return filepath
                else:
                    stderr_text = stderr.decode() if stderr else "未知错误"
                    logger.warning(f"curl下载失败: {stderr_text}")
            except Exception as e:
                logger.warning(f"curl下载异常: {e}")
            
            # 如果是GIF，更倾向于返回原始URL
            if is_gif and is_qq_multimedia:
                logger.info(f"GIF下载失败，直接使用原始URL: {url}")
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
