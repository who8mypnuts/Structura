"""MainWindow: the composition root (docs/14 §2, §9). Creates the widgets, wires services, owns commands."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PySide6.QtCore import QSize, Qt, QTimer, Slot
from PySide6.QtGui import QCloseEvent, QGuiApplication, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QSplitter,
    QStackedWidget,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ..core.jit import set_cpu_threads
from ..core.lang.analysis import Analysis
from ..core.scene.camera import Camera
from ..render.api import script_settings
from ..services.build import BuildProgress
from ..services.jobs import JobRunner
from ..services.render import RenderService
from ..services.settings import SettingsService
from ..services.theme import ThemeService
from ..themes.model import Theme
from ..themes.qss import Fonts
from .animation_actions import AnimationActions
from .banners import Banners
from .build_actions import BuildActions
from .camera_actions import CameraActions, HistoryActions
from .command_palette import CommandPalette
from .commands.builtin import register_builtin
from .commands.keymap import Keymap
from .commands.registry import CommandRegistry
from .dialog_actions import DialogActions
from .dock_layout import LAYOUT_VERSION, DockLayout
from .document_actions import DocumentActions
from .documents import DocumentTabs, EditorTab
from .editor_actions import EditorActions
from .export_actions import ExportActions
from .file_drop import FileDropFilter
from .header import BRAND, HeaderBar
from .help_actions import HelpActions
from .i18n import tr
from .material_actions import LightActions, MaterialActions
from .menus import add_dynamic_menu, build_menus
from .panels.activity import ActivityPanel
from .panels.build_stats import BuildStatsPanel
from .panels.camera import CameraPanel
from .panels.console import ConsolePanel
from .panels.examples import ExamplesPanel
from .panels.files import FilesPanel
from .panels.history import HistoryPanel
from .panels.inspector import InspectorPanel
from .panels.lights import LightsPanel
from .panels.materials import MaterialsPanel
from .panels.outline import OutlinePanel
from .panels.parameters import ParametersPanel
from .panels.problems import ProblemsPanel
from .panels.render_queue import RenderQueuePanel
from .panels.render_settings import RenderSettingsPanel
from .panels.timeline.panel import TimelinePanel
from .panels.variations import VariationExplorer
from .parameter_sync import ParameterSync
from .processes import ProcessRunner
from .project_actions import ProjectActions
from .provenance import ProvenanceHover
from .quick_open import QuickOpen
from .render_actions import RenderActions
from .render_queue import RenderQueue
from .render_view.render_view import RenderView
from .scene_view import describe_pick, viewport_options
from .script_actions import ScriptActions
from .search_actions import SearchActions
from .session_actions import SessionActions
from .statusbar import StatusBar
from .theming import apply_theme
from .timeline_actions import TimelineActions
from .viewport.host import ViewportHost, preview_label
from .welcome import WelcomePage
from .widgets.banner import Banner
from .widgets.toast import ToastStack
from .workbench import PreviewReady, Workbench
from .workspaces import Workspaces

DEFAULT_SIZE = QSize(1440, 900)
EDITOR_SHARE = 0.45  # of the central area, beside the viewport
SCREEN_FRACTION = 0.92  # leave room for panels and window decorations
SIDE_WIDTH = 280  # the side panel beside the activity rail


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
        self._panels()
        self.status = StatusBar()
        self.toasts = ToastStack(self, lambda: not bool(self.settings.value("appearance/reduce_motion", False)))
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
        self.processes = ProcessRunner(self)
        self.render_actions = RenderActions(self)
        self.cameras, self.history_actions = CameraActions(self), HistoryActions(self)
        self.build_actions = BuildActions(self)
        self.workspaces = Workspaces(self)
        self.banners = Banners(self)
        self.material_actions, self.light_actions = MaterialActions(self), LightActions(self)
        self.registry = CommandRegistry(self)
        self.command_palette = CommandPalette(self.registry, self)
        self.quick_open = QuickOpen(self)
        register_builtin(self.registry, self)
        self.keymap = Keymap(self.registry, self.settings)
        self.keymap.apply()
        self.header = HeaderBar(self.registry)
        self._layout()
        self.search = SearchActions(self)
        self.default_layout = self.saveState(LAYOUT_VERSION)  # View ▸ Reset Layout
        self._connect()
        build_menus(self.menuBar(), self.registry)
        add_dynamic_menu(self.menuBar(), "File", "Open Recent", "file.open", self.docs.fill_recent_menu)
        self.console.attach()
        self.apply_settings()
        self.registry.refresh()

    # -- layout --------------------------------------------------------------------------------------------
    def _panels(self) -> None:
        self.viewport = ViewportHost(self.renders)
        self.render_view = RenderView(self.renders)
        self.console, self.problems, self.stats = ConsolePanel(), ProblemsPanel(), BuildStatsPanel()
        self.outline, self.parameters, self.examples = OutlinePanel(), ParametersPanel(), ExamplesPanel(self.runner)
        self.variations = VariationExplorer(self.runner)
        self.render_settings, self.timeline_panel = RenderSettingsPanel(), TimelinePanel()
        self.camera_panel, self.inspector, self.files = CameraPanel(), InspectorPanel(), FilesPanel()
        self.materials, self.lights = MaterialsPanel(), LightsPanel()
        self.render_queue = RenderQueue(self)
        self.queue_panel, self.activity = RenderQueuePanel(self.render_queue), ActivityPanel(self.runner)
        self.history = HistoryPanel()

    def _layout(self) -> None:
        self.views = QTabWidget()
        self.views.setAccessibleName(tr("Views"))
        self.tabs.setAccessibleName(tr("Open scripts"))
        self.views.setDocumentMode(True)
        self.views.addTab(self.viewport, "Viewport")
        self.views.addTab(self.render_view, "Render")
        self.welcome = WelcomePage(self.docs.recent.paths)
        self.editor_area = QStackedWidget()
        self.editor_area.addWidget(self.tabs)
        self.editor_area.addWidget(self.welcome)
        self._show_welcome()
        self.banner = Banner()
        view_column = QWidget()
        column = QVBoxLayout(view_column)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(0)
        column.addWidget(self.banner)
        column.addWidget(self.views, 1)
        split = self.split = QSplitter(Qt.Orientation.Horizontal)
        split.addWidget(self.editor_area)
        split.addWidget(view_column)
        split.setSizes([520, 760])
        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.header)
        layout.addWidget(split, 1)
        self.setCentralWidget(central)
        self.setStatusBar(self.status)
        self.panels = DockLayout(self)
        self.docks = self.panels.docks
        widgets = {"Examples": self.examples, "Files": self.files, "Outline": self.outline,  # the first one is shown
                   "Parameters": self.parameters, "Camera": self.camera_panel, "Inspector": self.inspector,
                   "Materials": self.materials, "Lights": self.lights,
                   "Variations": self.variations, "Render Settings": self.render_settings,
                   "Problems": self.problems, "Console": self.console, "Build Stats": self.stats,
                   "Timeline": self.timeline_panel, "Render Queue": self.queue_panel, "History": self.history,
                   "Activity": self.activity}  # fmt: skip
        for title, widget in widgets.items():
            self.panels.add(title, widget)
        self.rail = self.panels.attach_rail(self.registry)
        self.resize(initial_size(self))
        self._sized = False
        self._split_sized = False  # True once restored from the session or set to the default share

    def _show_welcome(self, *_: object) -> None:
        """The welcome page while no script is open."""
        empty = self.tabs.count() == 0
        if empty and self.editor_area.currentWidget() is not self.welcome:
            self.welcome.refresh()
        self.editor_area.setCurrentWidget(self.welcome if empty else self.tabs)

    def open_any(self, path: Path) -> None:
        """Files panel: scripts and projects open in a tab; renders reopen the script that made them."""
        if path.suffix.lower() in (".png", ".exr"):
            self.projects.open_render(path)
        else:
            self.docs.open_file(path)

    def choose_theme(self, theme_id: str) -> None:
        self.settings.set_value("appearance/theme", theme_id)
        self.themes.set_theme(theme_id)

    def start(self, files: list[Path]) -> None:
        """Open the recovered or previous session and ``files``, and restore the saved window layout."""
        self.welcome.probe_device(self.runner, self.renders.backends)
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
        area = Qt.DockWidgetArea.BottomDockWidgetArea
        bottom = [d for d in self.docks.values() if self.dockWidgetArea(d) == area and not d.isHidden()]
        self.resizeDocks(bottom, [170] * len(bottom), Qt.Orientation.Vertical)
        side = [d for d in self.docks.values() if d.isVisible() and d not in bottom]
        self.resizeDocks(side, [SIDE_WIDTH] * len(side), Qt.Orientation.Horizontal)

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
        wb.recolored.connect(self.on_recolored)
        wb.scene_ready.connect(self.banners.scene_ready)
        self.viewport.mode_changed.connect(self.banners.preview_mode)
        wb.message.connect(self.show_message)
        wb.builds.failed.connect(lambda *_: self.status.set_busy(False))
        self.header.seed_changed.connect(wb.set_seed)
        self.workspaces.changed.connect(self.header.set_workspace)
        self.workspaces.changed.connect(lambda _: self.registry.refresh())
        self.header.set_workspace(self.workspaces.current)
        self.tabs.current_tab_changed.connect(self.on_tab_changed)
        self.render_settings.overrides_changed.connect(self._store_render_overrides)
        self.status.track(self.tabs)
        self.problems.activated_offset.connect(self.docs.go_to)
        self.outline.activated_offset.connect(self.docs.go_to)
        self.examples.open_example.connect(self.docs.open_example)
        self.inspector.go_to_source.connect(self.docs.go_to)
        self.queue_panel.add_requested.connect(self.render_actions.queue_render)
        self.files.open_path.connect(self.open_any)
        self.tabs.tab_added.connect(self._show_welcome)
        self.tabs.current_tab_changed.connect(self._show_welcome)
        w = self.welcome
        w.new_script.connect(self.docs.new_script)
        w.open_file.connect(self.docs.open_dialog)
        w.open_recent.connect(self.docs.open_file)
        w.show_examples.connect(lambda: self.panels.show("Examples"))
        w.choose_theme.connect(self.choose_theme)
        self.inspector.select_rows.connect(self._select_rows)
        self.inspector.isolate_rows.connect(self.build_actions.isolate)
        self.variations.adopt.connect(self.build_actions.adopt_seed)
        self.variations.adopt_params.connect(self.build_actions.adopt_params)
        self.viewport.picked.connect(self.on_picked)
        self.viewport.mode_changed.connect(lambda mode: self.status.set("device", f"Preview: {preview_label(mode)}"))
        self.themes.theme_changed.connect(self.apply_theme)
        self.render_view.status.connect(self.show_message)
        self.render_view.request_source = self.render_actions.render_source

    # -- appearance ----------------------------------------------------------------------------------------
    @Slot(object)
    def apply_theme(self, theme: Theme) -> None:
        app = QApplication.instance()
        if isinstance(app, QApplication):
            apply_theme(app, theme, self.fonts())
        self.tabs.set_theme(theme)
        self.header.set_theme(theme)
        self.rail.set_theme(theme)
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
        self.build_actions.apply_overlays()
        set_cpu_threads(int(self.settings.value("render/cpu_threads", 0)))
        self.viewport.set_navigation(str(self.settings.value("viewport/controls", "structura")))
        self.viewport.animate_moves = lambda: not bool(self.settings.value("appearance/reduce_motion", False))
        self.apply_theme(self.themes.theme)

    # -- workbench events ----------------------------------------------------------------------------------
    @Slot(object)
    def on_tab_changed(self, tab: EditorTab | None) -> None:
        self.registry.refresh()
        if tab is None:
            return
        self.header.set_seed(tab.seed)
        self.render_settings.set_overrides(tab.render_overrides)
        self.files.follow(tab.path)

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
        self.viewport.overlay.set_stale(bool(errors) and tab.outcome is not None)
        self.docks["Problems"].setWindowTitle(f"Problems ({len(analysis.diagnostics)})" if errors else "Problems")

    @Slot(object)
    def on_build_started(self, tab: EditorTab) -> None:
        self.status.set_busy(True)

    @Slot(object, object)
    def on_build_progress(self, tab: EditorTab, progress: BuildProgress) -> None:
        self.status.set("objects", f"building… {progress.objects:,} objects")

    @Slot(object, object, object, bool)
    def on_scene_ready(self, tab: EditorTab, ready: PreviewReady, camera: Camera | None, frame: bool) -> None:
        outcome = ready.outcome
        self.status.set_busy(False)
        self.viewport.overlay.set_stale(False)
        self.status.set("objects", f"{len(outcome.scene):,} objects")
        self.status.set("build", f"build {outcome.stats.seconds * 1000:.0f} ms")
        if tab is not self.tabs.current():
            return
        self.stats.show_outcome(outcome)
        script = script_settings(outcome.scene)
        self.render_settings.show_settings(script)
        self.render_view.integrator.setCurrentText(script.integrator)
        self.viewport.set_scene(ready.shown, ready.preview, camera)
        self._refresh_viewport_options()
        if frame:
            self.viewport.frame_all()

    @Slot(object, object)
    def on_recolored(self, tab: EditorTab, ready: PreviewReady) -> None:
        if tab is self.tabs.current():
            self.viewport.set_scene(ready.shown, ready.preview, None)

    @Slot(object)
    def on_picked(self, row: int | None) -> None:
        self.viewport.select(row)
        tab = self.tabs.current()
        if row is None or tab is None or tab.outcome is None:
            self.status.showMessage("")
            self.inspector.show_pick(None, None, None)
            return
        self.inspector.show_pick(tab.outcome.scene, tab.analysis, row, tab.text())
        text, span = describe_pick(tab.outcome.scene, tab.analysis, row)
        self.status.showMessage(text)
        if span is not None:
            tab.editor.go_to(span.start)

    @Slot(object)
    def _select_rows(self, rows: object) -> None:
        tab = self.tabs.current()
        count = len(tab.outcome.scene) if tab is not None and tab.outcome is not None else 0
        self.viewport.highlight(rows if isinstance(rows, np.ndarray) else None, count)

    @Slot(str)
    def show_message(self, text: str) -> None:
        self.status.showMessage(text, 6000)
        self.console.info(text)

    def notify_file(self, text: str, path: Path) -> None:
        """A finished file operation: a toast with "Show in Folder", and the console log."""
        self.toasts.show_file(text, path)
        self.console.info(f"{text}: {path}")

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        self.workspaces.save_current()
        if not self.session.shutdown():
            event.ignore()
            return
        self.console.detach()
        self.runner.shutdown()
        event.accept()
