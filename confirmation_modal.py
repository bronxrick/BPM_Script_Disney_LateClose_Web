# confirmation_modal.py

import customtkinter as ctk


class ConfirmationModal(ctk.CTkToplevel):
    def __init__(self, parent, actions):
        super().__init__(parent)

        self.title("Confirm Calendar Actions")
        self.geometry("650x450")
        self.resizable(False, False)
        self.grab_set()

        self.selected_events = []

        # CASE 1: No actions at all
        if not actions:
            self._build_empty_ui()
        else:
            self._build_actions_ui(actions)

    # ---------------------------------------------------------
    # UI for when NO events were found
    # ---------------------------------------------------------
    def _build_empty_ui(self):
        msg = ctk.CTkLabel(
            self,
            text="No late-close events were found in the next 5 days.",
            font=("Arial", 18, "bold"),
            justify="center"
        )
        msg.pack(pady=40)

        sub = ctk.CTkLabel(
            self,
            text="Nothing to create.",
            font=("Arial", 14),
            justify="center"
        )
        sub.pack(pady=10)

        close_btn = ctk.CTkButton(
            self,
            text="Close",
            command=self.cancel
        )
        close_btn.pack(pady=20)

    # ---------------------------------------------------------
    # UI for when events DO exist
    # ---------------------------------------------------------
    def _build_actions_ui(self, actions):
        title_label = ctk.CTkLabel(
            self,
            text="Select Events to Create",
            font=("Arial", 18, "bold")
        )
        title_label.pack(pady=10)

        frame = ctk.CTkScrollableFrame(self, width=620, height=260)
        frame.pack(pady=10)

        self.check_vars = []

        for action, ev in actions:
            status = "ADD" if action == "add" else "SKIP"
            color = "#4CAF50" if action == "add" else "#FF9800"

            text = "{} on {}   [{}]".format(
                ev["summary"], ev["date"], status
            )

            var = ctk.BooleanVar(value=(action == "add"))

            chk = ctk.CTkCheckBox(
                frame,
                text=text,
                text_color=color,
                variable=var
            )

            if action == "skip":
                chk.configure(state="disabled")

            chk.pack(anchor="w", padx=10, pady=4)

            self.check_vars.append((var, action, ev))

        btn_frame = ctk.CTkFrame(self)
        btn_frame.pack(pady=15)

        confirm_btn = ctk.CTkButton(
            btn_frame,
            text="Create Selected Events",
            command=self.confirm
        )
        confirm_btn.grid(row=0, column=0, padx=10)

        cancel_btn = ctk.CTkButton(
            btn_frame,
            text="Cancel",
            fg_color="#444444",
            command=self.cancel
        )
        cancel_btn.grid(row=0, column=1, padx=10)

    # ---------------------------------------------------------
    # Button handlers
    # ---------------------------------------------------------
    def confirm(self):
        if hasattr(self, "check_vars"):
            self.selected_events = [
                ev
                for (var, action, ev) in self.check_vars
                if action == "add" and var.get()
            ]
        self.destroy()

    def cancel(self):
        self.selected_events = None
        self.destroy()