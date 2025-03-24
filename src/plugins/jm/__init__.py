import asyncio
from nonebot import on_command, get_driver
from nonebot.adapters.onebot.v11 import Bot, MessageEvent
from nonebot.plugin import PluginMetadata
from nonebot.adapters.onebot.v11 import PrivateMessageEvent, GroupMessageEvent

from jmcomic import download_album
import os
import shutil
from PIL import Image
import time

# 插件的元数据
plugin_metadata = PluginMetadata(
    name="JMComic Download",
    description="A plugin to download comics in PDF format and send them.",
    usage="Use `\\jm <album_id>` to download and send a comic in PDF format."
)

# 创建命令处理器
jm_command = on_command("jm", priority=5)

def webp_to_pdf(folder_path: str, output_pdf: str):
    """
    将文件夹中的webp图片合并为PDF文件。
    :param folder_path: 图片所在的文件夹路径
    :param output_pdf: 输出PDF文件路径
    """
    images = []
    for file_name in sorted(os.listdir(folder_path)):
        file_path = os.path.join(folder_path, file_name)
        if file_name.lower().endswith('.webp'):
            with Image.open(file_path) as img:
                images.append(img.convert("RGB"))

    if images:
        images[0].save(output_pdf, save_all=True, append_images=images[1:])

def find_target_folders(directory: str) -> list:
    """
    在指定目录中找到所有目标文件夹，忽略指定的文件夹。
    :param directory: 要扫描的目录路径
    :return: 目标文件夹的路径列表
    """
    ignored_folders = {"__pycache__", ".venv", "JMComic", "Lagrange.OneBot", "src"}
    folders = [
        os.path.join(directory, f)
        for f in os.listdir(directory)
        if os.path.isdir(os.path.join(directory, f)) and f not in ignored_folders
    ]
    return folders

def safe_remove(file_path: str):
    """
    安全删除文件，确保文件未被占用。
    :param file_path: 要删除的文件路径
    """
    for _ in range(5):
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
            break
        except PermissionError:
            time.sleep(1)

async def send_pdf(bot: Bot, event: MessageEvent, output_pdf: str):
    """
    根据消息来源发送PDF文件。
    :param bot: Bot实例
    :param event: 消息事件
    :param output_pdf: PDF文件路径
    """
    try:
        if isinstance(event, PrivateMessageEvent):
            await bot.call_api(
                "upload_private_file",
                user_id=event.user_id,
                file=output_pdf,
                name=os.path.basename(output_pdf)
            )
        elif isinstance(event, GroupMessageEvent):
            await bot.call_api(
                "upload_group_file",
                group_id=event.group_id,
                file=output_pdf,
                name=os.path.basename(output_pdf)
            )
    except Exception as e:
        raise Exception(f"发送PDF文件失败：{str(e)}")

@jm_command.handle()
async def handle_jm_command(event: MessageEvent, bot: Bot):
    """
    实际处理命令的逻辑。
    """
    msg = event.get_plaintext().strip()
    album_id = ''.join(filter(str.isdigit, msg))

    if not album_id:
        await bot.send(event, "无效的漫画ID，请检查您的输入。")
        return

    try:
        await bot.send(event, f"正在下载漫画ID: {album_id}...")
        download_album(album_id)

        folder_paths = find_target_folders(os.getcwd())
        if not folder_paths:
            await bot.send(event, "未找到有效的文件夹，请检查下载是否成功。")
            return

        for folder_path in folder_paths:
            output_pdf = f"{folder_path}.pdf"
            try:
                webp_to_pdf(folder_path, output_pdf)

                if os.path.exists(output_pdf):
                    await send_pdf(bot, event, output_pdf)
                else:
                    await bot.send(event, f"文件夹 {os.path.basename(folder_path)} 的 PDF 生成失败，请稍后再试。")
            except Exception as e:
                await bot.send(event, f"处理文件夹 {os.path.basename(folder_path)} 时发生错误：{str(e)}")
                raise
            finally:
                safe_remove(output_pdf)
                if os.path.exists(folder_path):
                    shutil.rmtree(folder_path)

    except Exception as e:
        await bot.send(event, f"发生错误：{str(e)}")