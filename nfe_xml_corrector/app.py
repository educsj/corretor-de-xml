from __future__ import annotations

from pathlib import Path
import os
import subprocess
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import webbrowser

from nfe_xml_corrector.core import (
    CorrectionOptions,
    correct_xml_file,
    default_output_path,
)
from nfe_xml_corrector.manual import APP_VERSION, MANUAL_SECTIONS


PRESET_CUSTOM = "Personalizado"
CPROD_NONE = "none"
CPROD_SEQUENTIAL = "sequential"
CPROD_RANDOM = "random"
PRESETS = {
    "EAN vincula produto errado": {
        "fix_cean": True,
        "fix_ceantrib": False,
        "cprod_mode": CPROD_NONE,
    },
    "SequelizeUniqueConstraintError / cProd": {
        "fix_cean": False,
        "fix_ceantrib": False,
        "cprod_mode": CPROD_SEQUENTIAL,
    },
    "cProd ja existe no cadastro": {
        "fix_cean": False,
        "fix_ceantrib": False,
        "cprod_mode": CPROD_RANDOM,
    },
    "Corrigir EAN e cProd": {
        "fix_cean": True,
        "fix_ceantrib": False,
        "cprod_mode": CPROD_SEQUENTIAL,
    },
    PRESET_CUSTOM: None,
}


def folder_open_command(platform: str, folder: Path) -> list[str] | None:
    if platform == "win32":
        return None
    if platform == "darwin":
        return ["open", str(folder)]
    return ["xdg-open", str(folder)]


class Tooltip:
    def __init__(self, widget: tk.Widget, text: str) -> None:
        self.widget = widget
        self.text = text
        self.window: tk.Toplevel | None = None
        self.after_id: str | None = None
        widget.bind("<Enter>", self._schedule, add="+")
        widget.bind("<Leave>", self._hide, add="+")
        widget.bind("<ButtonPress>", self._hide, add="+")

    def _schedule(self, _event: tk.Event) -> None:
        self._cancel()
        self.after_id = self.widget.after(450, self._show)

    def _show(self) -> None:
        if self.window or not self.widget.winfo_exists():
            return
        x = self.widget.winfo_rootx() + self.widget.winfo_width() - 8
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 6
        self.window = tk.Toplevel(self.widget)
        self.window.wm_overrideredirect(True)
        self.window.wm_geometry(f"+{x}+{y}")
        tk.Label(
            self.window,
            text=self.text,
            bg="#111827",
            fg="#ffffff",
            padx=8,
            pady=5,
            font=("Segoe UI", 9),
        ).pack()

    def _cancel(self) -> None:
        if self.after_id:
            self.widget.after_cancel(self.after_id)
            self.after_id = None

    def _hide(self, _event: tk.Event | None = None) -> None:
        self._cancel()
        if self.window:
            self.window.destroy()
            self.window = None


class NFeXmlCorrectorApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Corretor de XML NF-e")
        self.root.geometry("780x680")
        self.root.minsize(720, 650)

        self.input_path = tk.StringVar()
        self.output_path = tk.StringVar()
        self.preset = tk.StringVar(value="EAN vincula produto errado")
        self.fix_cean = tk.BooleanVar(value=True)
        self.fix_ceantrib = tk.BooleanVar(value=False)
        self.cprod_mode = tk.StringVar(value=CPROD_NONE)
        self.cprod_digits = tk.IntVar(value=4)
        self.last_output_path: Path | None = None
        self.help_window: tk.Toplevel | None = None

        self._configure_style()
        self._build_layout()
        self._apply_preset()

    def _configure_style(self) -> None:
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TFrame", background="#f6f7f9")
        style.configure("TLabel", background="#f6f7f9", font=("Segoe UI", 10))
        style.configure("Title.TLabel", font=("Segoe UI Semibold", 16))
        style.configure("Hint.TLabel", foreground="#4b5563")
        style.configure("TButton", font=("Segoe UI", 10), padding=(10, 6))
        style.configure("Primary.TButton", font=("Segoe UI Semibold", 10), padding=(12, 8))
        style.configure("TLabelframe", background="#f6f7f9", padding=(12, 8))
        style.configure("TLabelframe.Label", background="#f6f7f9", font=("Segoe UI Semibold", 10))
        style.configure("TCheckbutton", background="#f6f7f9", font=("Segoe UI", 10))

    def _build_layout(self) -> None:
        main = ttk.Frame(self.root, padding=18)
        main.grid(row=0, column=0, sticky="nsew")
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main.columnconfigure(0, weight=1)

        header = ttk.Frame(main)
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)
        ttk.Label(header, text="Corretor de XML NF-e", style="Title.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        help_button = ttk.Button(
            header,
            text="?",
            width=3,
            command=self._open_help,
            takefocus=True,
        )
        help_button.grid(row=0, column=1, sticky="e")
        self.help_tooltip = Tooltip(help_button, "Abrir manual de uso")
        ttk.Label(
            main,
            text="Importe a nota, escolha a correcao e gere uma copia corrigida.",
            style="Hint.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(2, 14))

        file_frame = ttk.LabelFrame(main, text="Arquivo")
        file_frame.grid(row=2, column=0, sticky="ew")
        file_frame.columnconfigure(1, weight=1)

        ttk.Label(file_frame, text="XML de entrada").grid(row=0, column=0, sticky="w", pady=4)
        ttk.Entry(file_frame, textvariable=self.input_path).grid(
            row=0, column=1, sticky="ew", padx=8, pady=4
        )
        ttk.Button(file_frame, text="Selecionar", command=self._choose_input).grid(
            row=0, column=2, pady=4
        )

        ttk.Label(file_frame, text="Salvar como").grid(row=1, column=0, sticky="w", pady=4)
        ttk.Entry(file_frame, textvariable=self.output_path).grid(
            row=1, column=1, sticky="ew", padx=8, pady=4
        )
        ttk.Button(file_frame, text="Alterar", command=self._choose_output).grid(
            row=1, column=2, pady=4
        )

        options_frame = ttk.LabelFrame(main, text="Correcao")
        options_frame.grid(row=3, column=0, sticky="ew", pady=(14, 0))
        options_frame.columnconfigure(1, weight=1)

        ttk.Label(options_frame, text="Erro do ERP").grid(row=0, column=0, sticky="w", pady=4)
        preset_box = ttk.Combobox(
            options_frame,
            textvariable=self.preset,
            values=list(PRESETS.keys()),
            state="readonly",
        )
        preset_box.grid(row=0, column=1, sticky="ew", padx=8, pady=4)
        preset_box.bind("<<ComboboxSelected>>", lambda _event: self._apply_preset())

        checks = ttk.Frame(options_frame)
        checks.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(8, 2))
        checks.columnconfigure(0, weight=1)

        ttk.Checkbutton(
            checks,
            text="Trocar <cEAN> para SEM GTIN",
            variable=self.fix_cean,
            command=self._mark_custom,
        ).grid(row=0, column=0, sticky="w", pady=3)
        ttk.Checkbutton(
            checks,
            text="Trocar tambem <cEANTrib> para SEM GTIN",
            variable=self.fix_ceantrib,
            command=self._mark_custom,
        ).grid(row=1, column=0, sticky="w", pady=3)
        ttk.Checkbutton(
            checks,
            text="Renumerar <cProd> em sequencia 0001, 0002...",
            variable=self.cprod_mode,
            onvalue=CPROD_SEQUENTIAL,
            offvalue=CPROD_NONE,
            command=self._select_cprod_mode,
        ).grid(row=2, column=0, sticky="w", pady=3)
        ttk.Checkbutton(
            checks,
            text="Gerar numeros aleatorios unicos para <cProd>",
            variable=self.cprod_mode,
            onvalue=CPROD_RANDOM,
            offvalue=CPROD_NONE,
            command=self._select_cprod_mode,
        ).grid(row=3, column=0, sticky="w", pady=3)

        self.digits_frame = ttk.Frame(options_frame)
        self.digits_label = ttk.Label(self.digits_frame, text="Digitos do cProd")
        self.digits_label.grid(row=0, column=0, sticky="w")
        self.digits_spinbox = ttk.Spinbox(
            self.digits_frame,
            from_=1,
            to=20,
            textvariable=self.cprod_digits,
            width=6,
            command=self._mark_custom,
        )
        self.digits_spinbox.grid(row=0, column=1, sticky="w", padx=(8, 0))

        actions = ttk.Frame(main)
        actions.grid(row=4, column=0, sticky="ew", pady=(16, 0))
        actions.columnconfigure(2, weight=1)

        ttk.Button(
            actions,
            text="Gerar XML corrigido",
            style="Primary.TButton",
            command=self._process,
        ).grid(row=0, column=0, sticky="w")
        ttk.Button(actions, text="Abrir pasta", command=self._open_output_folder).grid(
            row=0, column=1, sticky="w", padx=(8, 0)
        )

        log_frame = ttk.LabelFrame(main, text="Resultado")
        log_frame.grid(row=5, column=0, sticky="nsew", pady=(14, 0))
        main.rowconfigure(5, weight=1)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)

        self.log = tk.Text(
            log_frame,
            height=8,
            wrap="word",
            relief="flat",
            bg="#ffffff",
            fg="#111827",
            font=("Consolas", 10),
        )
        self.log.grid(row=0, column=0, sticky="nsew")
        self.log.configure(state="disabled")

        footer = ttk.Frame(main)
        footer.grid(row=6, column=0, sticky="ew", pady=(10, 0))
        footer.columnconfigure(0, weight=1)
        github_link = tk.Label(
            footer,
            text="github.com/educsj",
            fg="#2563eb",
            bg="#f6f7f9",
            cursor="hand2",
            font=("Segoe UI", 10, "underline"),
        )
        github_link.grid(row=0, column=0, sticky="w")
        github_link.bind("<Button-1>", lambda _event: webbrowser.open_new_tab("https://github.com/educsj"))

        self._sync_cprod_digits_visibility()
        self._write_log("Pronto para corrigir um XML de NF-e.")

    def _apply_preset(self) -> None:
        preset = PRESETS.get(self.preset.get())
        if preset is None:
            return
        self.fix_cean.set(preset["fix_cean"])
        self.fix_ceantrib.set(preset["fix_ceantrib"])
        self.cprod_mode.set(preset["cprod_mode"])
        self._sync_cprod_digits_visibility()

    def _mark_custom(self) -> None:
        if self.preset.get() != PRESET_CUSTOM:
            self.preset.set(PRESET_CUSTOM)

    def _select_cprod_mode(self) -> None:
        self._mark_custom()
        self._sync_cprod_digits_visibility()

    def _sync_cprod_digits_visibility(self) -> None:
        mode = self.cprod_mode.get()
        if mode != CPROD_NONE:
            minimum = 4 if mode == CPROD_RANDOM else 1
            self.digits_spinbox.configure(from_=minimum)
            if self.cprod_digits.get() < minimum:
                self.cprod_digits.set(minimum)
            label = (
                "Digitos do cProd (minimo 4)"
                if mode == CPROD_RANDOM
                else "Digitos do cProd"
            )
            self.digits_label.configure(text=label)
            self.digits_frame.grid(row=2, column=0, columnspan=2, sticky="w", pady=(8, 2))
        else:
            self.digits_frame.grid_remove()

    def _choose_input(self) -> None:
        filename = filedialog.askopenfilename(
            title="Selecionar XML da nota",
            filetypes=(("Arquivos XML", "*.xml"), ("Todos os arquivos", "*.*")),
        )
        if not filename:
            return
        self.input_path.set(filename)
        self.output_path.set(str(default_output_path(filename)))
        self._write_log(f"XML selecionado:\n{filename}")

    def _choose_output(self) -> None:
        initial = self.output_path.get()
        if not initial and self.input_path.get():
            initial = str(default_output_path(self.input_path.get()))

        initial_path = Path(initial) if initial else Path.cwd() / "nota_corrigida.xml"
        filename = filedialog.asksaveasfilename(
            title="Salvar XML corrigido como",
            initialdir=str(initial_path.parent),
            initialfile=initial_path.name,
            defaultextension=".xml",
            filetypes=(("Arquivos XML", "*.xml"), ("Todos os arquivos", "*.*")),
        )
        if filename:
            self.output_path.set(filename)

    def _open_help(self) -> None:
        if self.help_window and self.help_window.winfo_exists():
            self.help_window.deiconify()
            self.help_window.lift()
            self.help_window.focus_set()
            return

        window = tk.Toplevel(self.root)
        self.help_window = window
        window.title("Manual de uso")
        window.geometry("760x650")
        window.minsize(620, 500)
        window.transient(self.root)
        window.columnconfigure(0, weight=1)
        window.rowconfigure(0, weight=1)
        window.protocol("WM_DELETE_WINDOW", self._close_help)

        container = ttk.Frame(window, padding=18)
        container.grid(row=0, column=0, sticky="nsew")
        container.columnconfigure(0, weight=1)
        container.rowconfigure(2, weight=1)

        ttk.Label(container, text="Como usar o Corretor de XML", style="Title.TLabel").grid(
            row=0, column=0, columnspan=2, sticky="w"
        )
        ttk.Label(
            container,
            text=f"Manual integrado - versao {APP_VERSION}",
            style="Hint.TLabel",
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(2, 12))

        manual = tk.Text(
            container,
            wrap="word",
            relief="flat",
            bg="#ffffff",
            fg="#111827",
            padx=16,
            pady=14,
            font=("Segoe UI", 10),
            spacing1=2,
            spacing3=2,
        )
        manual.grid(row=2, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=manual.yview)
        scrollbar.grid(row=2, column=1, sticky="ns")
        manual.configure(yscrollcommand=scrollbar.set)
        manual.tag_configure(
            "section",
            font=("Segoe UI Semibold", 12),
            foreground="#1d4f7a",
            spacing1=10,
            spacing3=5,
        )
        manual.tag_configure("body", lmargin1=2, lmargin2=2, spacing3=4)

        for heading, body in MANUAL_SECTIONS:
            manual.insert(tk.END, heading + "\n", "section")
            manual.insert(tk.END, body + "\n\n", "body")
        manual.configure(state="disabled")

        ttk.Button(container, text="Fechar", command=self._close_help).grid(
            row=3, column=0, columnspan=2, sticky="e", pady=(12, 0)
        )
        window.focus_set()

    def _close_help(self) -> None:
        if self.help_window and self.help_window.winfo_exists():
            self.help_window.destroy()
        self.help_window = None

    def _process(self) -> None:
        try:
            input_file = Path(self.input_path.get())
            output_file = Path(self.output_path.get())

            if not self.input_path.get():
                raise ValueError("Selecione o XML de entrada.")
            if not self.output_path.get():
                self.output_path.set(str(default_output_path(input_file)))
                output_file = Path(self.output_path.get())
            if input_file.resolve() == output_file.resolve():
                raise ValueError("Escolha um arquivo de saida diferente do XML original.")

            options = CorrectionOptions(
                fix_cean=self.fix_cean.get(),
                fix_ceantrib=self.fix_ceantrib.get(),
                renumber_cprod=self.cprod_mode.get() == CPROD_SEQUENTIAL,
                randomize_cprod=self.cprod_mode.get() == CPROD_RANDOM,
                cprod_digits=int(self.cprod_digits.get()),
            )

            result = correct_xml_file(input_file, output_file, options)
            self.last_output_path = result.output_path
            summary = self._format_result(result.changed_counts, result.found_counts)
            opened_folder = self._try_open_folder(result.output_path.parent)
            folder_message = (
                "A pasta de destino foi aberta."
                if opened_folder
                else "O arquivo foi gerado, mas nao consegui abrir a pasta automaticamente."
            )
            self._write_log(
                "XML corrigido com sucesso.\n"
                f"Saida: {result.output_path}\n\n"
                f"{summary}\n\n"
                "O arquivo original nao foi alterado.\n"
                f"{folder_message}"
            )
            messagebox.showinfo("XML corrigido", "Arquivo corrigido gerado com sucesso.")
        except Exception as exc:  # noqa: BLE001 - GUI should show recoverable errors.
            self._write_log(f"Erro:\n{exc}")
            messagebox.showerror("Nao foi possivel corrigir", str(exc))

    def _format_result(self, changed_counts: dict[str, int], found_counts: dict[str, int]) -> str:
        lines = []
        for key in ("cEAN", "cEANTrib", "cProd"):
            found = found_counts.get(key, 0)
            changed = changed_counts.get(key, 0)
            if found:
                lines.append(f"{key}: {changed} alterado(s) de {found} encontrado(s)")
        return "\n".join(lines) if lines else "Nenhuma tag encontrada para as opcoes marcadas."

    def _open_output_folder(self) -> None:
        folder: Path | None = None
        if self.last_output_path:
            folder = self.last_output_path.parent
        elif self.output_path.get():
            folder = Path(self.output_path.get()).parent

        if not folder or not folder.exists():
            messagebox.showwarning("Pasta nao encontrada", "Nenhum arquivo corrigido foi gerado ainda.")
            return
        self._try_open_folder(folder)

    def _try_open_folder(self, folder: Path) -> bool:
        try:
            command = folder_open_command(sys.platform, folder)
            if command is None:
                os.startfile(str(folder))  # type: ignore[attr-defined]
            else:
                subprocess.Popen(
                    command,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
        except OSError:
            return False
        return True

    def _write_log(self, text: str) -> None:
        self.log.configure(state="normal")
        self.log.delete("1.0", tk.END)
        self.log.insert("1.0", text)
        self.log.configure(state="disabled")


def main() -> None:
    root = tk.Tk()
    app = NFeXmlCorrectorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
