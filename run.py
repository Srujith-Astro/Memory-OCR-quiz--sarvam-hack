import uvicorn
import webbrowser
import threading
import time

def open_browser():
    time.sleep(1.2)
    webbrowser.open("http://127.0.0.1:8000")

if __name__ == "__main__":
    print("Starting MemoryRecall Gamified Active Recall App...")
    print("Web UI will be available at: http://127.0.0.1:8000")
    print("Powered by Sarvam AI (Doc AI OCR + sarvam-105b-conversations)")
    
    # Optional auto-open
    threading.Thread(target=open_browser, daemon=True).start()
    
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=False)
