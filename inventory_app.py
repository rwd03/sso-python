"""Inventory Management Portal, a second desktop app using Google sign-in."""

import tkinter as tk
from pathlib import Path
from tkinter import ttk

from main import CREDENTIALS, Portal


INVENTORY_CREDENTIALS = Path(__file__).with_name("inventory_credentials.json")
SAMPLE_ITEMS = (
    ("IT-101", "Laptop", 12),
    ("IT-102", "USB-C dock", 24),
    ("IT-103", "Monitor", 8),
    ("IT-104", "Keyboard", 36),
)


class InventoryPortal(Portal):
    title = "Inventory Management Portal"

    def __init__(self, root):
        credentials = INVENTORY_CREDENTIALS if INVENTORY_CREDENTIALS.exists() else CREDENTIALS
        super().__init__(root, credentials)
        root.geometry("620x440")
        root.minsize(520, 405)

    def dashboard(self, name, email, picture):
        self.clear()
        ttk.Label(self.card, text=self.title, style="Heading.TLabel").pack(anchor="w")
        ttk.Label(self.card, text=f"Welcome, {name}", wraplength=455).pack(anchor="w", pady=(8, 0))
        ttk.Label(self.card, text=email, wraplength=455).pack(anchor="w", pady=(0, 18))
        ttk.Label(self.card, text="Sample inventory").pack(anchor="w", pady=(0, 6))

        table = ttk.Treeview(self.card, columns=("sku", "item", "stock"),
                             show="headings", height=len(SAMPLE_ITEMS), selectmode="none")
        table.heading("sku", text="SKU")
        table.heading("item", text="Item")
        table.heading("stock", text="In stock")
        table.column("sku", width=90, stretch=False)
        table.column("item", width=230)
        table.column("stock", width=90, stretch=False, anchor="center")
        for item in SAMPLE_ITEMS:
            table.insert("", "end", values=item)
        table.pack(fill="x")

        ttk.Button(self.card, text="Log out", style="Portal.TButton",
                   command=self.login_screen).pack(anchor="e", pady=(18, 0))


if __name__ == "__main__":
    root = tk.Tk()
    InventoryPortal(root)
    root.mainloop()
