# delorean_console.py

import customtkinter as ctk
import threading


class DeLoreanConsole(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Disney Late Close Calendar Extractor")
        self.geometry("1100x600")
        self.resizable(True, True)

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")

        self._lock = threading.Lock()
        self._confirm_event = threading.Event()
        self._confirm_result = None
        self._confirm_panel = None

        self._build_ui()

    def _build_ui(self):
        header_frame = ctk.CTkFrame(self, corner_radius=10)
        header_frame.pack(fill="x", padx=10, pady=10)

        title_label = ctk.CTkLabel(
            header_frame,
            text="DISNEY LATE CLOSE CALENDAR EXTRACTOR",
            font=("Consolas", 18, "bold"),
            text_color="#00E5FF",
        )
        title_label.pack(pady=4)

        subtitle_label = ctk.CTkLabel(
            header_frame,
            text="Flux Capacitor Online - Time Circuits Engaged - Live Log Stream",
            font=("Consolas", 11),
            text_color="#FFA726",
        )
        subtitle_label.pack(pady=2)

        self.main_frame = ctk.CTkFrame(
            self,
            corner_radius=15,
            fg_color="#050816",
        )
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.log_frame = ctk.CTkFrame(
            self.main_frame,
            corner_radius=10,
            fg_color="#050816",
        )
        self.log_frame.pack(side="left", fill="both", expand=True, padx=(10, 5), pady=10)

        self.textbox = ctk.CTkTextbox(
            self.log_frame,
            wrap="word",
            font=("Consolas", 12),
            fg_color="#050816",
            text_color="#E0F7FA",
            border_width=2,
            border_color="#00E5FF",
        )
        self.textbox.pack(fill="both", expand=True, padx=5, pady=5)

        self.textbox.insert("end", "[FLUX] Console initialized.\n")
        self.textbox.configure(state="disabled")

    def write(self, message: str):
        if not message.endswith("\n"):
            message += "\n"

        def _append():
            with self._lock:
                self.textbox.configure(state="normal")
                self.textbox.insert("end", message)
                self.textbox.see("end")
                self.textbox.configure(state="disabled")

        self.after(0, _append)

    def flush(self):
        pass

    def show_confirmation_panel(self, actions):
        self._confirm_event.clear()
        self._confirm_result = None

        def _build_panel():
            if self._confirm_panel is not None:
                self._confirm_panel.destroy()
                self._confirm_panel = None

            panel = ctk.CTkFrame(
                self.main_frame,
                corner_radius=15,
                fg_color="#050816",
                border_width=2,
                border_color="#00E5FF",
            )
            panel.pack(side="right", fill="y", padx=(5, 10), pady=10)
            panel.configure(width=450)
            panel.pack_propagate(False)
            panel.grid_propagate(False)
            self._confirm_panel = panel

            panel.grid_columnconfigure(0, weight=1)
            panel.grid_rowconfigure(2, weight=1)

            title_label = ctk.CTkLabel(
                panel,
                text="Select Events to Create",
                font=("Consolas", 14, "bold"),
                text_color="#E0F7FA",
            )
            title_label.grid(row=0, column=0, pady=(10, 5), padx=10, sticky="n")

            subtitle_label = ctk.CTkLabel(
                panel,
                text="Check the events you want to create.",
                font=("Consolas", 11),
                text_color="#FFA726",
            )
            subtitle_label.grid(row=1, column=0, pady=(0, 10), padx=10, sticky="n")

            list_border = ctk.CTkFrame(
                panel,
                corner_radius=10,
                fg_color="#050816",
                border_width=3,
                border_color="#00E5FF",
            )
            list_border.grid(row=2, column=0, padx=10, pady=(0, 5), sticky="nsew")
            list_border.grid_rowconfigure(0, weight=1)
            list_border.grid_columnconfigure(0, weight=1)

            list_frame = ctk.CTkScrollableFrame(
                list_border,
                width=430,
                height=380,
                fg_color="#050816",
            )
            list_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

            check_vars = []

            for action, ev in actions:
                status = "ADD" if action == "add" else "SKIP"
                color = "#4CAF50" if action == "add" else "#FF9800"

                text = "{} on {}   [{}]".format(
                    ev["summary"], ev["date"], status
                )

                var = ctk.BooleanVar(value=(action == "add"))

                chk = ctk.CTkCheckBox(
                    list_frame,
                    text=text,
                    text_color=color,
                    variable=var,
                    font=("Consolas", 11),
                )

                if action == "skip":
                    chk.configure(state="disabled")

                chk.pack(anchor="w", padx=10, pady=4)

                check_vars.append((var, action, ev))

            button_frame = ctk.CTkFrame(panel, fg_color="#050816")
            button_frame.grid(row=3, column=0, pady=(5, 10), padx=10, sticky="sew")
            button_frame.grid_columnconfigure(0, weight=1)
            button_frame.grid_columnconfigure(1, weight=1)

            def on_create():
                selected = [
                    ev
                    for (var, action, ev) in check_vars
                    if action == "add" and var.get()
                ]
                self._confirm_result = selected
                if self._confirm_panel is not None:
                    self._confirm_panel.destroy()
                    self._confirm_panel = None
                self._confirm_event.set()

            def on_cancel():
                self._confirm_result = None
                if self._confirm_panel is not None:
                    self._confirm_panel.destroy()
                    self._confirm_panel = None
                self._confirm_event.set()

            create_btn = ctk.CTkButton(
                button_frame,
                text="Create Selected Events",
                command=on_create,
            )
            create_btn.grid(row=0, column=0, padx=10, pady=5, sticky="ew")

            cancel_btn = ctk.CTkButton(
                button_frame,
                text="Cancel",
                fg_color="#444444",
                command=on_cancel,
            )
            cancel_btn.grid(row=0, column=1, padx=10, pady=5, sticky="ew")

        self.after(0, _build_panel)
        self._confirm_event.wait()
        return self._confirm_result