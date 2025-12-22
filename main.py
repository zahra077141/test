import asyncio
import shlex
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN = '8412698993:AAFPNA35Kyy-kBNyMHKnID_Oa9mtspqNepE'  # استبدل بتوكنك
AUTHORIZED_USERS = {7367423827}  # معرفك

class ShellSession:
    def __init__(self):
        self.cwd = None
        self.process = None

    async def start_shell(self):
        # شيل نظيف بدون تحميل ملفات تعريف، مع prompt بسيط
        self.process = await asyncio.create_subprocess_shell(
            '/bin/bash --noprofile --norc',
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        # نحدد prompt بسيط لمنع أي تعقيدات
        await self.send_command('PS1="$ "\n')
        self.cwd = await self.get_cwd()

    async def send_command(self, cmd):
        self.process.stdin.write(cmd.encode())
        await self.process.stdin.drain()

    async def get_cwd(self):
        await self.send_command('pwd\n')
        await asyncio.sleep(0.1)
        output = await self.read_output(timeout=0.2)
        if output:
            lines = output.strip().split('\n')
            return lines[-1]
        return None

    async def read_output(self, timeout=0.5):
        output = b''
        try:
            while True:
                line = await asyncio.wait_for(self.process.stdout.readline(), timeout=timeout)
                if not line:
                    break
                output += line
        except asyncio.TimeoutError:
            pass
        return output.decode(errors='ignore')

    async def run_command(self, command):
        if command.startswith('cd'):
            parts = shlex.split(command)
            if len(parts) == 1:
                command = 'cd ~'
            # نفذ cd بدون انتظار المخرجات الكثيرة
            await self.send_command(command + '\n')
            await asyncio.sleep(0.1)
            self.cwd = await self.get_cwd()
            return f'تم تغيير المسار إلى:\n`{self.cwd}`'

        await self.send_command(command + '\n')
        await asyncio.sleep(0.3)
        output = await self.read_output(timeout=1)

        if not output.strip():
            output = "(لا يوجد مخرجات)"

        return output

shell_session = ShellSession()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in AUTHORIZED_USERS:
        await update.message.reply_text("ما عندك صلاحية لاستخدام هذا البوت.")
        return
    await shell_session.start_shell()
    await update.message.reply_text("بوت جاهز، أرسل أي أمر.")

async def run_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in AUTHORIZED_USERS:
        await update.message.reply_text("ما عندك صلاحية لاستخدام هذا البوت.")
        return

    command = update.message.text.strip()
    if not command:
        await update.message.reply_text("يرجى ارسال أمر صالح.")
        return

    result = await shell_session.run_command(command)

    # رد مرتب: المسار بأعلى، ثم الناتج
    response = f"`{shell_session.cwd} $ {command}`\n\n"
    response += f"```\n{result.strip()}\n```"

    await update.message.reply_text(response, parse_mode='Markdown')

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), run_command))
    app.run_polling()

if __name__ == '__main__':
    main()
