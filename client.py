import httpx
import asyncio
import json
import uuid
import logging
from datetime import datetime
from typing import Optional
from playwright.async_api import async_playwright
import random
import os
import platform

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class LiveClient:
    def __init__(self, server_url: str):
        self.server_url = server_url.rstrip('/')
        self.config_file = 'config.json'
        self.client_id = self._get_or_create_client_id()
        self.current_task: Optional[dict] = None
        self.client = httpx.AsyncClient(timeout=30.0)
        self.is_running = True
        self.tasks = []
        self.browser = None
        self.context = None
        self.page = None

    def _get_or_create_client_id(self) -> str:
        """获取或创建客户端ID"""
        try:
            # 如果配置文件不存在，创建默认配置
            if not os.path.exists(self.config_file):
                default_config = {
                    "client_id": None,
                    "chrome_path": {
                        "windows": "",
                        "darwin": "",
                        "linux": "/usr/bin/google-chrome"
                    }
                }
                with open(self.config_file, 'w') as f:
                    json.dump(default_config, f, indent=2)

            # 读取配置文件
            with open(self.config_file, 'r') as f:
                config = json.load(f)

            # 如果没有client_id，生成新的并保存
            if not config.get("client_id"):
                config["client_id"] = str(uuid.uuid4())
                with open(self.config_file, 'w') as f:
                    json.dump(config, f, indent=2)

            return config["client_id"]
        except Exception as e:
            logger.error(f"获取客户端ID失败: {e}")
            return str(uuid.uuid4())  # 如果出错，返回临时ID

    def _get_chrome_path(self) -> str:
        """从配置文件获取Chrome路径"""
        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)
            
            system = platform.system().lower()
            if system == 'linux':
                # 检查不同的可能路径
                possible_paths = [
                    '/usr/bin/google-chrome',
                    '/usr/bin/google-chrome-stable',
                    '/usr/bin/chromium-browser',
                    '/usr/bin/chromium'
                ]
                
                # 首先使用配置文件中的路径
                chrome_path = config["chrome_path"].get(system, "")
                if chrome_path and os.path.exists(chrome_path):
                    return chrome_path
                    
                # 如果配置文件中的路径无效，尝试其他可能的路径
                for path in possible_paths:
                    if os.path.exists(path):
                        # 更新配置文件
                        config["chrome_path"]["linux"] = path
                        with open(self.config_file, 'w') as f:
                            json.dump(config, f, indent=2)
                        return path
                        
                return ""  # 如果都找不到，返回空字符串
            else:
                return config["chrome_path"].get(system, "")
        except Exception as e:
            logger.error(f"获取Chrome路径失败: {e}")
            return ""

    async def init_browser(self):
        """初始化浏览器"""
        try:
            playwright = await async_playwright().start()
            
            launch_options = {
                'headless': True,  # 无头模式
                'args': [
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu',
                    '--disable-web-security',
                    '--autoplay-policy=no-user-gesture-required',  # 允许自动播放
                    '--disable-features=IsolateOrigins,site-per-process',
                    '--disable-site-isolation-trials',
                    '--mute-audio'  # 静音播放
                ]
            }
            
            # 获取 Chrome 路径
            chrome_path = self._get_chrome_path()
            if chrome_path and os.path.exists(chrome_path):
                launch_options['executable_path'] = chrome_path
                logger.info(f"使用 Chrome 路径: {chrome_path}")
            
            self.browser = await playwright.chromium.launch(**launch_options)
            logger.info("浏览器启动成功")
            
            # 创建上下文
            self.context = await self.browser.new_context(
                viewport={'width': 1280, 'height': 720},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
                ignore_https_errors=True,
                bypass_csp=True
            )

            # 配置请求拦截
            await self.context.route("**/*", lambda route: route.continue_())
            
            logger.info("浏览器初始化完成")
            return True
        except Exception as e:
            logger.error(f"初始化浏览器失败: {e}")
            return False

    async def set_cookies(self, cookie_data: dict):
        """设置cookie"""
        try:
            cookies = [
                {"name": key, "value": value, "domain": ".bilibili.com", "path": "/"}
                for key, value in cookie_data.items()
            ]
            await self.context.add_cookies(cookies)
            return True
        except Exception as e:
            logger.error(f"设置cookie失败: {e}")
            return False

    async def watch_live_room(self, room_id: str) -> bool:
        """打开并观看直播间"""
        try:
            if not self.browser:
                if not await self.init_browser():
                    return False

            # 构建直播间URL
            live_url = f"https://live.bilibili.com/{room_id}"
            
            # 创建新页面
            self.page = await self.context.new_page()
            
            # 设置更长的超时时间
            self.page.set_default_timeout(120000)  # 2分钟
            
            # 访问直播间
            await self.page.goto(
                live_url,
                wait_until='domcontentloaded',
                timeout=120000
            )
            
            # 等待页面加载完成
            try:
                await self.page.wait_for_selector('#live-player', timeout=180000)
                
                # 等待视频播放
                await self.page.wait_for_function("""
                    () => {
                        const video = document.querySelector('video');
                        return video && video.readyState >= 3;
                    }
                """, timeout=60000)
                
                logger.info(f"成功进入直播间 {room_id}")
                return True
                
            except Exception as e:
                logger.error(f"等待播放器加载失败: {e}")
                return False

        except Exception as e:
            logger.error(f"打开直播间失败: {e}")
            return False

    async def simulate_user_activity(self):
        """模拟用户活动"""
        try:
            if not self.page:
                return False
            
            # 随机选择一个操作
            actions = [
                self.refresh_page,
                self.scroll_page,
                self.like_stream,
                self.send_danmaku
            ]
            action = random.choice(actions)
            await action()
            return True
        except Exception as e:
            logger.error(f"模拟用户活动失败: {e}")
            return False

    async def refresh_page(self):
        """刷新页面"""
        await self.page.reload(wait_until='domcontentloaded')
        await self.page.wait_for_selector('#live-player', timeout=30000)

    async def scroll_page(self):
        """滚动页面"""
        await self.page.evaluate("""
            () => {
                window.scrollTo({
                    top: Math.random() * document.body.scrollHeight,
                    behavior: 'smooth'
                });
            }
        """)

    async def like_stream(self):
        """点赞直播间"""
        try:
            like_btn = await self.page.query_selector('.like-btn')
            if like_btn:
                await like_btn.click()
        except:
            pass

    async def send_danmaku(self):
        """发送弹幕"""
        try:
            await self.page.type('.chat-input', '666')
            await self.page.click('.chat-send-btn')
        except:
            pass

    async def handle_stream_error(self, task_id: int, error_msg: str):
        """处理直播异常"""
        try:
            # 保存错误截图
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            screenshot_path = f"error_screenshots/{task_id}_{timestamp}.png"
            os.makedirs("error_screenshots", exist_ok=True)
            await self.page.screenshot(path=screenshot_path)
            
            # 更新任务状态
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.server_url}/api/tasks/error",
                    json={
                        "task_id": task_id,
                        "error_message": error_msg,
                        "screenshot_path": screenshot_path
                    }
                )
                if response.status_code != 200:
                    logger.error("更新任务状态失败")
        except Exception as e:
            logger.error(f"处理直播异常失败: {e}")

    async def close_live(self):
        """关闭直播间"""
        try:
            if self.page:
                await self.page.close()
                self.page = None
            if self.context:
                await self.context.close()
                self.context = None
            if self.browser:
                await self.browser.close()
                self.browser = None
        except Exception as e:
            logger.error(f"关闭直播间失败: {e}")

    async def heartbeat_loop(self):
        """独立的心跳循环"""
        while self.is_running:
            try:
                response = await self.client.post(
                    f"{self.server_url}/api/heartbeat",
                    json={"client_id": self.client_id}
                )
                data = response.json()
                if data.get("code") == 0:
                    logger.debug("心跳发送成功")
                else:
                    logger.warning("心跳发送失败")
            except Exception as e:
                logger.error(f"心跳请求出错: {e}")
            
            # 每5分钟发送一次心跳
            await asyncio.sleep(50)

    async def task_check_loop(self):
        """独立的任务检查循环"""
        while self.is_running:
            try:
                if not self.current_task:
                    response = await self.client.get(
                        f"{self.server_url}/api/tasks/client/{self.client_id}"
                    )
                    data = response.json()
                    if data.get("code") == 0 and data.get("data"):
                        self.current_task = data.get("data")
                        # 启动新的观看任务
                        task = asyncio.create_task(self.execute_watch_task(self.current_task))
                        self.tasks.append(task)
                        logger.info(f"获取到新任务: {json.dumps(self.current_task, ensure_ascii=False)}")
            except Exception as e:
                logger.error(f"检查任务出错: {e}")
            
            # 如果没有任务，每10秒检查一次
            await asyncio.sleep(60)

    async def update_progress(self, task_id: int, watched_time: int, progress: float) -> bool:
        """更新任务进度"""
        try:
            response = await self.client.post(
                f"{self.server_url}/api/tasks/progress",
                json={
                    "task_id": task_id,
                    "watched_time": watched_time,
                    "progress": progress
                }
            )
            data = response.json()
            return data.get("code") == 0
        except Exception as e:
            logger.error(f"更新进度失败: {e}")
            return False

    async def execute_watch_task(self, task: dict):
        """执行观看任务"""
        try:
            # 先初始化浏览器
            if not self.browser:
                if not await self.init_browser():
                    logger.error("初始化浏览器失败")
                    return

            # 设置cookie
            if "cookie" in task:
                await self.set_cookies(task["cookie"])

            room_id = task['room_id']
            total_time = task['total_watch_time']
            watched_time = task['watched_time']
            remaining_time = total_time - watched_time

            logger.info(f"开始观看直播间 {room_id}, 剩余时间: {remaining_time}分钟")

            # 打开直播间
            if not await self.watch_live_room(room_id):
                logger.error("打开直播间失败，任务终止")
                self.current_task = None
                return

            # 观看直播
            for minute in range(watched_time, total_time):
                if not self.is_running:
                    break

                # 每分钟检查一次页面状态
                try:
                    if self.page:
                        # 检查直播是否正常播放
                        await self.page.wait_for_selector('.live-player-mounter', timeout=5000)
                        
                        # 模拟用户活动
                        await self.simulate_user_activity()
                        
                except Exception as e:
                    logger.error(f"直播间异常: {e}")
                    # 处理异常
                    await self.handle_stream_error(task['id'], str(e))
                    # 关闭直播间
                    await self.close_live()
                    self.current_task = None
                    return

                await asyncio.sleep(60)  # 等待1分钟
                
                # 更新进度
                progress = ((minute + 1) / total_time) * 100
                success = await self.update_progress(task['id'], minute + 1, progress)
                
                if success:
                    logger.info(f"直播间 {room_id} 已观看 {minute + 1}/{total_time} 分钟")
                else:
                    logger.error("进度更新失败")

            # 关闭直播间
            await self.close_live()
            
            if self.is_running:
                logger.info(f"直播间 {room_id} 观看任务完成")
                self.current_task = None

        except Exception as e:
            logger.error(f"观看任务执行出错: {e}")
            await self.handle_stream_error(task['id'], str(e))
            await self.close_live()
            self.current_task = None

    async def run(self):
        """运行客户端"""
        try:
            # 启动心跳循环
            heartbeat_task = asyncio.create_task(self.heartbeat_loop())
            self.tasks.append(heartbeat_task)

            # 启动任务检查循环
            task_check = asyncio.create_task(self.task_check_loop())
            self.tasks.append(task_check)

            # 等待所有任务完成
            await asyncio.gather(*self.tasks, return_exceptions=True)

        except KeyboardInterrupt:
            logger.info("接收到停止信号，正在关闭...")
            self.is_running = False
            # 取消所有任务
            for task in self.tasks:
                task.cancel()
            await self.client.aclose()

async def main():
    try:
        # 从环境变量或配置文件获取服务器URL
        server_url = "http://172.16.1.205:8000"  # 替换为实际的服务器地址
        client = LiveClient(server_url)
        await client.run()
    except KeyboardInterrupt:
        logger.info("程序已停止")

if __name__ == "__main__":
    asyncio.run(main()) 