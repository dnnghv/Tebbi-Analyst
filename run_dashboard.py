#!/usr/bin/env python3
"""
Launcher script for Thread Analytics Dashboard
"""

import subprocess
import sys
import os
import argparse
import time

def check_dependencies():
    """Kiểm tra dependencies có được cài đặt chưa"""
    try:
        import streamlit
        import plotly
        import pandas
        print("✅ All dependencies are installed")
        return True
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("Installing dependencies...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
            print("✅ Dependencies installed successfully")
            return True
        except Exception as install_error:
            print(f"❌ Failed to install dependencies: {install_error}")
            return False

def run_analytics(max_threads=500):
    """Chạy analytics để tạo dữ liệu"""
    print(f"\n🔄 CHẠY ANALYTICS (max_threads={max_threads})...")
    print("-" * 50)
    
    cmd = [
        "python3", "thread_analytics.py",
        "--max-threads", str(max_threads),
        "--export-csv",
        "--export-conversations-txt", "10",
        "--export-conversations-json", "5",
        "--json-report",
        "--output", "dashboard_data"
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Analytics completed successfully")
            return True
        else:
            print(f"❌ Analytics failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Error running analytics: {e}")
        return False

def launch_dashboard(port=8501):
    """Khởi chạy Streamlit dashboard"""
    print(f"\n🚀 LAUNCHING DASHBOARD ON PORT {port}...")
    print("-" * 50)
    print("🌐 Dashboard will open at: http://localhost:8501")
    print("⏹️  Press Ctrl+C to stop the dashboard")
    print("-" * 50)
    
    cmd = [
        "streamlit", "run", "streamlit_app.py",
        "--server.port", str(port),
        "--server.headless", "false",
        "--browser.gatherUsageStats", "false"
    ]
    
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\n👋 Dashboard stopped by user")
    except Exception as e:
        print(f"❌ Error launching dashboard: {e}")

def main():
    parser = argparse.ArgumentParser(description='Thread Analytics Dashboard Launcher')
    parser.add_argument('--skip-analytics', action='store_true', 
                       help='Skip running analytics, just launch dashboard')
    parser.add_argument('--max-threads', type=int, default=500,
                       help='Maximum threads to analyze (default: 500)')
    parser.add_argument('--port', type=int, default=8501,
                       help='Port for dashboard (default: 8501)')
    parser.add_argument('--analytics-only', action='store_true',
                       help='Only run analytics, do not launch dashboard')
    
    args = parser.parse_args()
    
    print("🎯 THREAD ANALYTICS DASHBOARD LAUNCHER")
    print("=" * 50)
    
    # Check dependencies
    if not check_dependencies():
        print("❌ Cannot proceed without dependencies")
        return
    
    # Run analytics if needed
    if not args.skip_analytics:
        if not run_analytics(args.max_threads):
            print("❌ Analytics failed, but you can still launch dashboard with existing data")
    
    if args.analytics_only:
        print("✅ Analytics completed. Use --skip-analytics to launch dashboard.")
        return
    
    # Check if we have any data files in new structure
    import glob
    data_files = []
    if os.path.exists("reports"):
        for date_dir in os.listdir("reports"):
            date_path = os.path.join("reports", date_dir)
            if os.path.isdir(date_path):
                reports_path = os.path.join(date_path, "reports")
                conv_path = os.path.join(date_path, "conversations")
                if os.path.exists(reports_path):
                    data_files.extend(glob.glob(os.path.join(reports_path, "*.json")))
                    data_files.extend(glob.glob(os.path.join(reports_path, "*.txt")))
                if os.path.exists(conv_path):
                    data_files.extend(glob.glob(os.path.join(conv_path, "*.*")))
    
    if not data_files:
        print("⚠️  No data files found. Running analytics first...")
        if not run_analytics(args.max_threads):
            print("❌ Cannot launch dashboard without data")
            return
    
    # Launch dashboard
    print(f"\n⏳ Waiting 2 seconds before launching dashboard...")
    time.sleep(2)
    launch_dashboard(args.port)

if __name__ == "__main__":
    main() 