#!/usr/bin/env python3
"""
Test script để launch dashboard với cấu trúc mới
"""

import subprocess
import sys
import os

def main():
    print("🚀 Launching Thread Analytics Dashboard...")
    print("=" * 50)
    
    # Kiểm tra xem có dữ liệu không
    if not os.path.exists("reports"):
        print("❌ Không tìm thấy thư mục reports")
        print("💡 Chạy thread_analytics.py trước để tạo dữ liệu")
        return
    
    # Tìm thư mục ngày
    date_dirs = [d for d in os.listdir("reports") if os.path.isdir(os.path.join("reports", d))]
    if not date_dirs:
        print("❌ Không tìm thấy dữ liệu ngày nào")
        print("💡 Chạy thread_analytics.py trước để tạo dữ liệu")
        return
    
    print(f"✅ Tìm thấy {len(date_dirs)} ngày dữ liệu: {', '.join(sorted(date_dirs))}")
    
    # Launch dashboard
    print("\n🌐 Launching Streamlit Dashboard...")
    print("📍 URL: http://localhost:8501")
    print("🔧 Features:")
    print("  📅 Date filtering trong sidebar")
    print("  👥 User/Thread Browser với structure mới")
    print("  📊 Analytics từ nhiều ngày")
    print("  💬 Individual thread conversations")
    
    print("\n⏳ Dashboard đang khởi động...")
    print("🛑 Nhấn Ctrl+C để dừng")
    
    try:
        subprocess.run([sys.executable, "-m", "streamlit", "run", "streamlit_app.py"])
    except KeyboardInterrupt:
        print("\n✋ Dashboard đã được dừng")
    except FileNotFoundError:
        print("\n❌ Streamlit chưa được cài đặt")
        print("💡 Chạy: pip install streamlit")

if __name__ == "__main__":
    main() 