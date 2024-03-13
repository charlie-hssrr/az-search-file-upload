import asyncio
import os
import aiofiles
from werkzeug.utils import secure_filename
from quart import (current_app)

from concurrent.futures import ThreadPoolExecutor

ALLOWED_EXTENSIONS = set(['pdf', 'html', 'json', 'docx', 'pptx', 'xlsx', 'png', 'jpg', 'jpeg', 'tiff', 'bmp', 'heic', 'md', 'txt'])

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

executor = ThreadPoolExecutor(max_workers=4)
async def save_file(file):
    filename = secure_filename(file.filename)
    file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
    
    # Use ThreadPoolExecutor to run synchronous file.read() operation in a background thread
    loop = asyncio.get_running_loop()
    file_data = await loop.run_in_executor(executor, file.read)
    
    async with aiofiles.open(file_path, 'wb') as out_file:
        await out_file.write(file_data)
    
    return filename