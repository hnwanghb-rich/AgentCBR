"""碳盘查审核系统 - 主入口"""
import tkinter as tk
from carbon_audit_gui import CarbonAuditGUI

def main():
    root = tk.Tk()
    app = CarbonAuditGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
