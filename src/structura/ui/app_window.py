"""MainWindow: the composition root (docs/14 §2, §9). Creates the widgets, wires services, owns commands."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from PySide6.QtCore import QSize, Qt, QTimer, Slot
from PySide6.QtGui import QCloseEvent, QGuiApplication, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QDockWidget,
    QMainWindow,
    QSplitter,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ..core.lang.analysis import Analysis
from ..core.scene.camera import Camera
from ..core.scene.ir import SceneIR
from ..preview.instances import PreviewScene
from ..render.api import script_settings
from ..render.settings import RenderSettings
from ..services.build import BuildOutcome, BuildProgress
from ..services.jobs import JobRunner
from ..services.render import RenderService
from ..services.settings import SettingsService
from ..services.theme import ThemeService
from ..themes.model import Theme
from ..themes.qss import Fonts
from .animation_actions import AnimationActions
from .command_palette import CommandPalette
from .commands.builtin import register_builtin
from .commands.keymap import Keymap
from .commands.registry import CommandRegistry
from .dialog_actions import DialogActions
from .document_actions import DocumentActions
from .documents import DocumentTabs, EditorTab
from .editor_actions import EditorActions
from .export_actions import ExportActions
from .file_drop import FileDropFilter
from .header import BRAND, HeaderBar
from .help_actions import HelpActions
from .i18n import tr
from .menus import add_dynamic_menu, build_menus
from .panels.build_stats import BuildStatsPanel
from .panels.console import ConsolePanel
from .panels.examples import ExamplesPanel
from .panels.outline import OutlinePanel
from .panels.parameters import ParametersPanel
from .panels.problems import ProblemsPanel
from .panels.render_settings import RenderSettingsPanel
from .panels.timeline.panel import TimelinePanel
from .panels.variations import VariationExplorer
from .parameter_sync import ParameterSync
from .project_actions import ProjectActions
from .provenance import ProvenanceHover
from .quick_open import QuickOpen
from .render_view.render_view import RenderView
from .scene_view import describe_pick, viewport_options
from .script_actions import ScriptActions
from .search_actions import SearchActions
from .session_actions import SessionActions
from .statusbar import StatusBar
from .theming import apply_theme
from .timeline_actions import TimelineActions
from .viewport.host import ViewportHost
from .workbench import Workbench

DEFAULT_SIZE = QSize(1440, 900)
EDITOR_SHARE = 0.45  # of the central area, beside the viewport
SCREEN_FRACTION = 0.92  # leave room for panels and window decorations


def initial_size(widget: QWidget) -> QSize:
    """The default window size, shrunk to fit the screen the window opens on."""
    screen = widget.screen() or QGuiApplication.primaryScreen()
    if screen is None:
        return DEFAULT_SIZE
    room = screen.availableGeometry().size() * SCREEN_FRACTION
    return DEFAULT_SIZE.boundedTo(room)


class MainWindow(QMainWindow):
    def __init__(self, settings: SettingsService | None = None, runner: JobRunner | None = None) -> None:
        super().__init__()
        self.setWindowTitle("Structura")
        self.setWindowIcon(QIcon(str(BRAND / "png" / "icon-256.png")))
        self.settings = settings or SettingsService()
        self.runner = runner or JobRunner()
        self.themes = ThemeService(self.settings)
        self.renders = RenderService(self.runner)
        self.tabs = DocumentTabs(self.themes.theme)
        self.workbench = Workbench(self.tabs, self.runner)
        self.viewport = ViewportHost(self.renders)
        self.render_view = RenderView(self.renders)
        self.console, self.problems, self.stats = ConsolePanel(), ProblemsPanel(), BuildStatsPanel()
        self.outline, self.parameters, self.examples = OutlinePanel(), ParametersPanel(), ExamplesPanel()
        self.variations = VariationExplorer(self.runner)
        self.render_settings, self.timeline_panel = RenderSettingsPanel(), TimelinePanel()
        self.status = StatusBar()
        self.docs = DocumentActions(self)
        self.editor_actions = EditorActions(self)
        self.session = SessionActions(self)
        self.projects = ProjectActions(self)
        self.help = HelpActions(self)
        self.dialogs = DialogActions(self)
        self.scripts = ScriptActions(self)
        self.provenance = ProvenanceHover(self)
        self.parameter_sync = ParameterSync(self)
        self.animations = AnimationActions(self)
        self.timeline = TimelineActions(self)
        FileDropFilter(self, self.docs.open_file)
        self.exports = ExportActions(self)
        self.registry = CommandRegistry(self)
        self.command_palette = CommandPalette(self.registry, self)
        self.quick_open = QuickOpen(self)
        register_builtin(self.registry, self)
        self.keymap = Keymap(self.registry, self.settings)
        self.keymap.apply()
        self.header = HeaderBar(self.registry)
        self._layout()
        self.search = SearchActions(self)
        self._connect()
        build_menus(self.menuBar(), self.registry)
        add_dynamic_menu(self.menuBar(), "File", "Open Recent", "file.open", self.docs.fill_recent_menu)
        self.console.attach()
        self.apply_settings()
        self.registry.refresh()

    # -- layout --------------------------------------------------------------------------------------------
    def _layout(self) -> None:
        self.views = QTabWidget()
        self.views.setAccessibleName(tr("Views"))
        self.tabs.setAccessibleName(tr("Open scripts"))
        self.views.setDocumentMode(True)
        self.views.addTab(self.viewport, "Viewport")
        self.views.addTab(self.render_view, "Render")
        split = self.split = QSplitter(Qt.Orientation.Horizontal)
        split.addWidget(self.tabs)
        split.addWidget(self.views)
        split.setSizes([520, 760])
        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.header)
        layout.addWidget(split, 1)
        self.setCentralWidget(central)
        self.setStatusBar(self.status)
        self.docks = {}
        for area, panels in (
            (Qt.DockWidgetArea.LeftDockWidgetArea, (("Examples", self.examples), ("Outline", self.outline),
                                                    ("Parameters", self.parameters),
                                                    ("Variations", self.variations),
                                                    ("Render Settings", self.render_settings))),
            (Qt.DockWidgetArea.BottomDockWidgetArea, (("Problems", self.problems), ("Console", self.console),
                                                      ("Build Stats", self.stats), ("Timeline", self.timeline_panel))),
        ):  # fmt: skip
            first = None
            for title, widget in panels:
                dock = QDockWidget(tr(title, "Panels"), self)
                dock.setObjectName(f"dock-{title.lower().replace(' ', '-')}")
                dock.setWidget(widget)
                widget.setAccessibleName(dock.windowTitle())
                self.addDockWidget(area, dock)
                if first is not None:
                    self.tabifyDockWidget(first, dock)
                first = first or dock
                self.docks[title] = dock
            if first is not None:
                first.raise_()
        self.resize(initial_size(self))
        self._sized = False
        self._split_sized = False  # True once restored from the session or set to the default share

    def start(self, files: list[Path]) -> None:
        """Open the recovered or previous session and ``files``, and restore the saved window layout."""
        self.session.startup(files)
        if self.session.restore_layout():
            self._sized = True  # the user's layout wins over the default dock sizes
            self._split_sized = self.session.split_restored

    def showEvent(self, event: object) -> None:  # noqa: N802
        super().showEvent(event)  # type: ignore[arg-type]
        if not self._sized:  # dock sizes only apply once the window has its real geometry
            self._sized = True
            QTimer.singleShot(0, self._initial_dock_sizes)
        if not self._split_sized:
            self._split_sized = True
            QTimer.singleShot(0, lambda: QTimer.singleShot(0, self._initial_split))  # after the dock sizes

    def _initial_dock_sizes(self) -> None:
        # The first layout pass can run before the header has collapsed its labels, which widens the window;
        # Qt never shrinks it back, so the intended size is applied again now that the minimum is final.
        self.resize(initial_size(self))
        bottom = [self.docks[t] for t in ("Problems", "Console", "Build Stats", "Timeline")]
        self.resizeDocks(bottom, [170] * len(bottom), Qt.Orientation.Vertical)
        left = [self.docks[t] for t in ("Examples", "Outline", "Parameters")]
        self.resizeDocks(left, [250] * len(left), Qt.Orientation.Horizontal)

    def _initial_split(self) -> None:
        """Editor and views share the central area 45 : 55 once its width is known."""
        width = max(1, self.split.width())
        self.split.setSizes([round(width * EDITOR_SHARE), width - round(width * EDITOR_SHARE)])

    def _connect(self) -> None:
        wb = self.workbench
        wb.analysis_shown.connect(self.on_analysis)
        wb.build_started.connect(self.on_build_started)
        wb.build_progress.connect(self.on_build_progress)
        wb.scene_ready.connect(self.on_scene_ready)
        wb.message.connect(self.show_message)
        wb.builds.failed.connect(lambda *_: self.status.set_busy(False))
        self.header.seed_changed.connect(wb.set_seed)
        self.tabs.current_tab_changed.connect(self.on_tab_changed)
        self.render_settings.overrides_changed.connect(self._store_render_overrides)
        self.status.track(self.tabs)
        self.problems.activated_offset.connect(self.docs.go_to)
        self.outline.activated_offset.connect(self.docs.go_to)
        self.examples.open_example.connect(self.docs.open_file)
        self.variations.adopt.connect(self.adopt_seed)
        self.viewport.picked.connect(self.on_picked)
        self.viewport.mode_changed.connect(lambda mode: self.status.set("device", f"Preview: {mode.upper()}"))
        self.themes.theme_changed.connect(self.apply_theme)
        self.render_view.status.connect(self.show_message)
        self.render_view.request_source = self.render_source

    # -- appearance ----------------------------------------------------------------------------------------
    @Slot(object)
    def apply_theme(self, theme: Theme) -> None:
        app = QApplication.instance()
        if isinstance(app, QApplication):
            apply_theme(app, theme, self.fonts())
        self.tabs.set_theme(theme)
        self.header.set_theme(theme)
        self.render_view.view.checker = (theme["render.checker.a"], theme["render.checker.b"])
        self._refresh_viewport_options()

    def fonts(self) -> Fonts:
        ui_size = int(self.settings.value("appearance/ui_size", 10))
        return Fonts(ui_size=ui_size, code_size=int(self.settings.value("editor/code_size", 11)))

    def _refresh_viewport_options(self) -> None:
        tab = self.tabs.current()
        scene = tab.outcome.scene if tab and tab.outcome else None
        self.viewport.set_options(viewport_options(self.viewport.options, self.themes.theme, scene))

    def apply_settings(self) -> None:
        """Push stored preferences into the live UI (called at start-up and after Preferences)."""
        self.themes.set_theme(str(self.settings.value("appearance/theme", self.themes.theme.meta.id)))
        self.workbench.live = bool(self.settings.value("editor/live_build", True))
        self.render_view.device.setCurrentText(str(self.settings.value("render/device", "auto")))
        self.editor_actions.apply()
        self.apply_theme(self.themes.theme)

    def toggle_live(self) -> None:
        self.workbench.live = not self.workbench.live
        self.show_message("Live build " + ("on" if self.workbench.live else "off"))

    def random_seed(self) -> None:
        self.header.set_seed(self.workbench.random_seed())

    def next_seed(self) -> None:
        self.header.set_seed(self.workbench.next_seed())

    def previous_seed(self) -> None:
        tab = self.tabs.current()
        seed = max(0, (tab.seed if tab else 0) - 1)
        self.header.set_seed(seed)
        self.workbench.set_seed(seed)

    def explore_variations(self) -> None:
        tab = self.tabs.current()
        if tab is None or tab.analysis is None or tab.analysis.program is None:
            self.show_message("The script must compile before exploring variations.")
            return
        self.docks["Variations"].raise_()
        self.variations.explore(tab.analysis.program)

    @Slot(int)
    def adopt_seed(self, seed: int) -> None:
        self.header.set_seed(seed)
        self.workbench.set_seed(seed)

    def set_look(self, look: str) -> None:
        self.viewport.set_options(replace(self.viewport.options, look=look))

    def start_render(self) -> None:
        self.views.setCurrentWidget(self.render_view)
        self.render_view.start()

    def render_source(self) -> tuple[SceneIR, Camera, RenderSettings, str] | None:
        tab = self.tabs.current()
        if tab is None or tab.outcome is None:
            return None
        w, h = self.viewport.width(), self.viewport.height()
        scale = min(1.0, 1280 / max(w, h))
        quick = self.render_view.settings(max(16, round(w * scale)), max(16, round(h * scale)))
        base = script_settings(tab.outcome.scene)  # the script's legacy keys and v2 blocks …
        settings = self.render_settings.apply(base)  # … the panel's values …
        settings = replace(  # … and the toolbar
            settings, frame=False, width=quick.width, height=quick.height, samples=quick.samples,
            samples_per_pass=quick.samples_per_pass, integrator=quick.integrator, aovs=quick.aovs,
            asset_dir=str(tab.path.parent) if tab.path else "",
        )  # fmt: skip
        return tab.outcome.scene, self.viewport.camera(), settings, tab.text()

    # -- workbench events ----------------------------------------------------------------------------------
    @Slot(object)
    def on_tab_changed(self, tab: EditorTab | None) -> None:
        self.registry.refresh()
        if tab is None:
            return
        self.header.set_seed(tab.seed)
        self.render_settings.set_overrides(tab.render_overrides)

    @Slot(dict)
    def _store_render_overrides(self, overrides: dict[str, object]) -> None:
        tab = self.tabs.current()
        if tab is not None:
            tab.render_overrides = overrides

    @Slot(object, object)
    def on_analysis(self, tab: EditorTab, analysis: Analysis) -> None:
        if tab is not self.tabs.current():
            return
        self.problems.show_diagnostics(tab.text(), list(analysis.diagnostics))
        self.status.set("dialect", tab.language_label)
        tab.editor.highlighter.set_analysis(analysis)
        self.outline.show_analysis(analysis)
        self.parameter_sync.show(tab, analysis)
        errors = sum(1 for d in analysis.diagnostics if d.severity.name == "ERROR")
        self.docks["Problems"].setWindowTitle(f"Problems ({len(analysis.diagnostics)})" if errors else "Problems")

    @Slot(object)
    def on_build_started(self, tab: EditorTab) -> None:
        self.status.set_busy(True)

    @Slot(object, object)
    def on_build_progress(self, tab: EditorTab, progress: BuildProgress) -> None:
        self.status.set("objects", f"building… {progress.objects:,} objects")

    @Slot(object, object, object, object, bool)
    def on_scene_ready(
        self, tab: EditorTab, outcome: BuildOutcome, preview: PreviewScene, camera: Camera | None, frame: bool
    ) -> None:
        self.status.set_busy(False)
        self.status.set("objects", f"{len(outcome.scene):,} objects")
        self.status.set("build", f"build {outcome.stats.seconds * 1000:.0f} ms")
        if tab is not self.tabs.current():
            return
        self.stats.show_outcome(outcome)
        script = script_settings(outcome.scene)
        self.render_settings.show_settings(script)
        self.render_view.integrator.setCurrentText(script.integrator)
        self.viewport.set_scene(outcome.scene, preview, camera)
        self._refresh_viewport_options()
        if frame:
            self.viewport.frame_all()

    @Slot(object)
    def on_picked(self, row: int | None) -> None:
        self.viewport.select(row)
        tab = self.tabs.current()
        if row is None or tab is None or tab.outcome is None:
            self.status.showMessage("")
            return
        text, span = describe_pick(tab.outcome.scene, tab.analysis, row)
        self.status.showMessage(text)
        if span is not None:
            tab.editor.go_to(span.start)

    @Slot(str)
    def show_message(self, text: str) -> None:
        self.status.showMessage(text, 6000)
        self.console.info(text)

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        if not self.session.shutdown():
            event.ignore()
            return
        self.console.detach()
        self.runner.shutdown()
        event.accept()
