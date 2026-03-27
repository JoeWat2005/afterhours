import sys
import asyncio
import uvicorn

# 1. Force the correct policy
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from app.main import app

if __name__ == "__main__":
    # 2. Build the loop manually and lock it in
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    # 3. Tell Uvicorn to NOT touch the loop (loop="none")
    config = uvicorn.Config(app=app, host="127.0.0.1", port=8000, loop="none")
    server = uvicorn.Server(config)
    
    # 4. Run the server using our handcrafted loop!
    loop.run_until_complete(server.serve())
    